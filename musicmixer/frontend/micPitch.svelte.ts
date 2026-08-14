// micPitch.svelte.ts
//
// Live pitch from the microphone.
//
// Module-scoped for the same reason the engine is: Gradio 6
// rebuilds the component on every event round trip, and a
// microphone that stopped listening because an unrelated
// button was clicked would be useless. One tracker, alive
// for as long as the page is.
//
// The split of work, decided before this was written:
// the AudioWorklet does capture only - a dependency-free
// buffer that turns 128-sample quanta into 2048-sample
// windows and posts them out. pYIN itself (Essentia.js,
// PitchYinProbabilistic - the same algorithm family as the
// Python side's pYIN) runs on those windows out here, where
// the WASM module loads through the normal bundle. Loading
// 2.5MB of WASM *inside* a worklet's separate scope was the
// single riskiest part of the original plan; buffering
// needs none of it. At ~23 windows a second the analysis is
// cheap enough for the main thread, and moving it into the
// worklet later is an upgrade, not a redesign.

import { engine } from "./mixerEngine.svelte";
// The es build embeds the WASM inline as base64 - one
// self-contained module, no separate .wasm file for the
// bundler to lose. This is why these exact paths, not the
// package's index.js (which is the UMD build).
import Essentia from "essentia.js/dist/essentia.js-core.es.js";
import { EssentiaWASM } from "essentia.js/dist/essentia-wasm.es.js";

export interface PitchFrame {
	// Song time, seconds - already mapped through the
	// engine's own clock and the fixed latency offset, so
	// a frame lands where the note it answered sits.
	time: number;
	// Hz. Never zero here; unvoiced frames are simply not
	// stored, which is what draws as a gap.
	freq: number;
}

// Suppresses two specific, evidence-confirmed glitch shapes
// from PitchYin's per-window output, without delaying
// genuine pitch changes. Built after two failed attempts,
// both worth remembering:
//
// 1. A ratio-check that tested "is there also periodicity at
//    half this frequency" fired on almost any clean tone -
//    any periodic signal is trivially periodic at double its
//    period too, so the test couldn't tell a real octave
//    error from ordinary correct detection. Wrongly halved a
//    clean, unambiguous 220Hz sine in testing.
// 2. A documented technique (a bilateral filter blending a
//    trailing window of readings, per a real singing-pitch-
//    tracker patent) was tried next and tested against real
//    recordings before shipping - and it also failed, two
//    ways: a confirmed 3-frame glitch run outlasted a 5-frame
//    median window and got wrongly accepted as real, and
//    genuine non-octave transitions were smeared/delayed by
//    2-3 frames because the whole averaging window had to
//    repopulate before the output moved.
//
// This design instead compares every new candidate only
// against the currently HELD value (not a blended window),
// so an ordinary transition - even a large one - passes
// through with zero added delay. Only two specific shapes
// are held back for confirmation, each matched to a real,
// measured failure:
//
// - Octave jump: within 1.5 semitones of exactly +/-12 from
//   the held value. Confirmed instances: a 3-frame run and a
//   1-frame run, both reading almost exactly half the true
//   note (e.g. 63Hz amid a steady 120-140Hz note).
// - Floor grab: lands under ~75Hz (the detector's own search
//   floor is 60Hz) while the held value is clearly not near
//   the floor. Confirmed instances: readings near 60-71Hz
//   appearing right at breaths/consonants between words,
//   unrelated by any clean ratio to the surrounding note.
//
// A flagged candidate is held back until CONFIRM_N
// consecutive candidates agree with EACH OTHER (not with the
// old held value) - 4 was chosen because the worst confirmed
// glitch run was 3 frames; a genuine octave leap or a
// genuine dip into the 60-75Hz range still registers, just
// after ~170ms of confirmation instead of instantly.
//
// Known, disclosed gap: this targets the two glitch shapes
// actually found in real recordings, not every conceivable
// bad reading. A handful of other single-frame outliers
// (not octave-related, not near the floor) were observed
// passing through unfiltered in the same verification run -
// smaller and less visually alarming than the two shapes
// above, and mostly landing at genuine phrase gaps, but real
// and worth knowing about rather than claiming this is
// exhaustive.
class GatedPitchFilter {
	private heldMidi: number | null = null;
	private pendingMidi: number | null = null;
	private pendingCount = 0;

	constructor(
		private confirmN: number = 4,
		private floorCeilingHz: number = 75
	) {}

	// Returns the frequency to use this frame, or null if the
	// candidate is being held back pending confirmation (draw
	// this as a gap, the same way an unvoiced frame is).
	push(freqHz: number): number | null {
		const midi = 69 + 12 * Math.log2(freqHz / 440);

		if (this.heldMidi === null) {
			this.heldMidi = midi;
			return freqHz;
		}

		const diff = Math.abs(midi - this.heldMidi);
		const floorMidi = 69 + 12 * Math.log2(this.floorCeilingHz / 440);
		const isOctaveJump = Math.abs(diff - 12) < 1.5;
		const isFloorGrab =
			freqHz < this.floorCeilingHz && this.heldMidi - floorMidi > 8;

		if (!isOctaveJump && !isFloorGrab) {
			this.heldMidi = midi;
			this.pendingMidi = null;
			this.pendingCount = 0;
			return freqHz;
		}

		if (this.pendingMidi !== null && Math.abs(midi - this.pendingMidi) < 1) {
			this.pendingCount++;
		} else {
			this.pendingMidi = midi;
			this.pendingCount = 1;
		}

		if (this.pendingCount >= this.confirmN) {
			this.heldMidi = midi;
			this.pendingMidi = null;
			this.pendingCount = 0;
			return freqHz;
		}

		return null;
	}
}

// pYIN's window. 2048 samples at 48kHz is ~43ms - long
// enough to reach E2, the app's stated floor.
const WINDOW = 2048;

// Keep roughly twenty minutes of frames at ~23/s before
// dropping the oldest - a cap against a mic left running,
// not a limit anyone should meet in practice.
const MAX_FRAMES = 30000;

// The worklet, inlined and loaded as a Blob URL so it needs
// no separate asset in the build. It knows nothing about
// pitch: fill a window, post it with the context time of
// the window's start, repeat. postMessage clones the buffer
// synchronously, so reusing it is safe.
// TEMPORARY DEBUG SCAFFOLDING - remove once the octave-
// clamping investigation is done. Logs every raw PitchYin
// result (pitch + confidence), before the confidence gate
// discards anything, so a rejected or octave-wrong
// candidate is visible rather than silently dropped.
// Throttled to ~2/s; at 23 windows/s an unthrottled log
// would flood the console and make it unreadable.
let lastDebugLog = 0;
const DEBUG_LOG_INTERVAL_MS = 500;

const WORKLET_SOURCE = `
class MicCaptureProcessor extends AudioWorkletProcessor {
	constructor() {
		super();
		this.window = new Float32Array(${WINDOW});
		this.filled = 0;
	}
	process(inputs) {
		const channel = inputs[0] && inputs[0][0];
		if (!channel) return true;
		let i = 0;
		while (i < channel.length) {
			const take = Math.min(channel.length - i, ${WINDOW} - this.filled);
			this.window.set(channel.subarray(i, i + take), this.filled);
			this.filled += take;
			i += take;
			if (this.filled === ${WINDOW}) {
				this.port.postMessage({
					time: currentTime + (i / sampleRate) - (${WINDOW} / sampleRate),
					samples: this.window
				});
				this.filled = 0;
			}
		}
		return true;
	}
}
registerProcessor("mic-capture", MicCaptureProcessor);
`;

type MicState = "off" | "starting" | "on" | "denied" | "error";

class MicPitch {
	// Denied is a normal state, not an error: the panel says
	// so and everything else keeps working without a mic.
	state = $state<MicState>("off");

	// The most recent voiced pitch, Hz, or null while
	// unvoiced - what the free-running dot draws while
	// nothing is playing.
	livePitch = $state<number | null>(null);

	// The trace of the current take, cleared the moment a
	// new playback starts. Kept after Stop so what was sung
	// stays lookable-at until the next take begins.
	trace: PitchFrame[] = $state([]);

	private stream: MediaStream | null = null;
	private sourceNode: MediaStreamAudioSourceNode | null = null;
	private workletNode: AudioWorkletNode | null = null;
	private sinkGain: GainNode | null = null;
	private essentia: any = null;

	// Suppresses the two evidence-confirmed glitch shapes
	// from raw per-window detection - see GatedPitchFilter's
	// own comment for the trail of what was tried before this
	// and why it was reverted.
	private glitchFilter = new GatedPitchFilter();

	// Worklet modules register per-context; remember which
	// context already has ours so a stop/start cycle does
	// not re-add it.
	private workletLoadedFor: AudioContext | null = null;

	// Edge detection for "a new take started": the first
	// frame that arrives with the engine playing, after any
	// stretch of it not playing, clears the old trace. Done
	// here rather than by hooking engine.play() so the
	// engine never has to know this module exists - no
	// circular import, one call site.
	private wasPlaying = false;

	// TEMPORARY DEBUG SCAFFOLDING - remove once the live-
	// vs-file investigation is done. Captures the exact raw
	// samples the worklet delivers (the same signal the
	// detector analyses, post getUserMedia constraints) so
	// a live take can be downloaded and run through the same
	// offline analysis a file recorded outside the browser
	// already went through - the real test of whether the
	// browser's own mic pipeline delivers a different signal
	// than, e.g., Voice Memos does, rather than guessing at
	// which browser-side setting might be responsible.
	debugRecording = $state(false);
	private debugRecordBuffer: Float32Array[] | null = null;
	private debugRecordSampleRate = 48000;

	async enable(): Promise<void> {
		if (this.state === "on" || this.state === "starting") return;
		this.state = "starting";

		try {
			// All three off. noiseSuppression and
			// autoGainControl reshape a sustained sung note,
			// which is the entire signal here - already
			// correctly off. echoCancellation was left on
			// under the assumption that headphones make it
			// moot; that reasoning was backwards. With
			// headphones there is no acoustic echo path at
			// all - the mic never hears the speakers - so AEC
			// has nothing legitimate to cancel and can only
			// distort the voice, the same category of harm as
			// the other two. Verified before flipping this:
			// an offline recording run through both librosa's
			// own pyin and the exact browser detector, window
			// by window, agreed to within a semitone at
			// confidence 0.93-1.00 for a full held note - the
			// detection algorithm itself is not the source of
			// the octave flicker seen live, which makes the
			// capture path (this constraint) the remaining
			// suspect.
			this.stream = await navigator.mediaDevices.getUserMedia({
				audio: {
					echoCancellation: false,
					noiseSuppression: false,
					autoGainControl: false
				}
			});
		} catch (err) {
			this.state = "denied";
			return;
		}

		try {
			const context = engine.ensureContext();
			if (context.state === "suspended") await context.resume();

			if (this.workletLoadedFor !== context) {
				const url = URL.createObjectURL(
					new Blob([WORKLET_SOURCE], { type: "application/javascript" })
				);
				await context.audioWorklet.addModule(url);
				URL.revokeObjectURL(url);
				this.workletLoadedFor = context;
			}

			if (!this.essentia) {
				this.essentia = new Essentia(EssentiaWASM);
			}

			this.sourceNode = context.createMediaStreamSource(this.stream);
			this.workletNode = new AudioWorkletNode(context, "mic-capture", {
				numberOfInputs: 1,
				numberOfOutputs: 1,
				channelCount: 1
			});

			// A worklet only runs while it is part of a graph
			// that reaches the destination; a zero gain keeps
			// it pulled without the mic ever being audible.
			this.sinkGain = context.createGain();
			this.sinkGain.gain.value = 0;

			this.sourceNode.connect(this.workletNode);
			this.workletNode.connect(this.sinkGain);
			this.sinkGain.connect(context.destination);

			this.workletNode.port.onmessage = (event) => {
				this.handleWindow(
					event.data.time as number,
					event.data.samples as Float32Array,
					context
				);
			};

			this.state = "on";
		} catch (err) {
			this.teardownNodes();
			this.state = "error";
		}
	}

	disable(): void {
		this.teardownNodes();
		this.livePitch = null;
		this.wasPlaying = false;
		this.state = "off";
		// The trace deliberately stays: turning the mic off
		// should not throw away what was just sung.
	}

	clearTrace(): void {
		this.trace = [];
	}

	// TEMPORARY DEBUG - see note above. Starts a fixed-
	// duration capture of the raw samples arriving from the
	// worklet; downloads a WAV automatically when it ends.
	debugStartRecording(seconds: number = 5): void {
		if (this.debugRecording) return;
		this.debugRecordBuffer = [];
		this.debugRecording = true;
		console.log(`[mic] debug recording started, ${seconds}s`);
		setTimeout(() => this.debugStopAndDownload(), seconds * 1000);
	}

	// TEMPORARY DEBUG - see note above.
	private debugStopAndDownload(): void {
		this.debugRecording = false;
		if (!this.debugRecordBuffer) return;

		const chunks = this.debugRecordBuffer;
		this.debugRecordBuffer = null;

		let total = 0;
		for (const c of chunks) total += c.length;
		const combined = new Float32Array(total);
		let offset = 0;
		for (const c of chunks) {
			combined.set(c, offset);
			offset += c.length;
		}

		const blob = this.debugEncodeWav(combined, this.debugRecordSampleRate);
		const url = URL.createObjectURL(blob);
		const a = document.createElement("a");
		a.href = url;
		a.download = `mic-debug-${Date.now()}.wav`;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);

		console.log(
			`[mic] debug recording saved, ${combined.length} samples ` +
			`(${(combined.length / this.debugRecordSampleRate).toFixed(2)}s ` +
			`at ${this.debugRecordSampleRate}Hz)`
		);
	}

	// TEMPORARY DEBUG - see note above. Minimal 16-bit PCM
	// mono WAV encoder - no library needed, and the format
	// is plain enough that any tool (ffmpeg, librosa) reads
	// it directly, the same path already used on the
	// Voice-Memos file this is being compared against.
	private debugEncodeWav(samples: Float32Array, sampleRate: number): Blob {
		const buffer = new ArrayBuffer(44 + samples.length * 2);
		const view = new DataView(buffer);

		const writeString = (offset: number, str: string) => {
			for (let i = 0; i < str.length; i++) {
				view.setUint8(offset + i, str.charCodeAt(i));
			}
		};

		writeString(0, "RIFF");
		view.setUint32(4, 36 + samples.length * 2, true);
		writeString(8, "WAVE");
		writeString(12, "fmt ");
		view.setUint32(16, 16, true);
		view.setUint16(20, 1, true); // PCM
		view.setUint16(22, 1, true); // mono
		view.setUint32(24, sampleRate, true);
		view.setUint32(28, sampleRate * 2, true); // byte rate
		view.setUint16(32, 2, true); // block align
		view.setUint16(34, 16, true); // bits per sample
		writeString(36, "data");
		view.setUint32(40, samples.length * 2, true);

		let offset = 44;
		for (let i = 0; i < samples.length; i++) {
			const s = Math.max(-1, Math.min(1, samples[i]));
			view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
			offset += 2;
		}

		return new Blob([buffer], { type: "audio/wav" });
	}

	private teardownNodes(): void {
		if (this.workletNode) {
			this.workletNode.port.onmessage = null;
			this.workletNode.disconnect();
			this.workletNode = null;
		}
		if (this.sourceNode) {
			this.sourceNode.disconnect();
			this.sourceNode = null;
		}
		if (this.sinkGain) {
			this.sinkGain.disconnect();
			this.sinkGain = null;
		}
		if (this.stream) {
			for (const track of this.stream.getTracks()) track.stop();
			this.stream = null;
		}
	}

	private handleWindow(
		time: number,
		samples: Float32Array,
		context: AudioContext
	): void {
		// TEMPORARY DEBUG - see note above. Captured here,
		// before essentia touches anything, so the saved WAV
		// is exactly what the detector received - the live
		// mic pipeline's actual output, for comparison against
		// a file recorded outside the browser.
		if (this.debugRecordBuffer) {
			this.debugRecordBuffer.push(samples.slice());
			this.debugRecordSampleRate = context.sampleRate;
		}

		// TEMPORARY DEBUG - direct clipping check, not a
		// guess: a held-note recording measured peak 0.14
		// (nowhere near 1.0), so if clipping is real it is
		// specific to note-switch transients that file never
		// contained. Logged every occurrence, not throttled,
		// since genuine clipping should be rare - if this
		// line ever prints, it is real evidence, not noise.
		let peak = 0;
		for (let i = 0; i < samples.length; i++) {
			const a = Math.abs(samples[i]);
			if (a > peak) peak = a;
		}
		if (peak > 0.95) {
			console.warn(
				`[mic-clip] window peak=${peak.toFixed(3)} at t=` +
				`${time.toFixed(2)}s - signal is clipping`
			);
		}

		if (!this.essentia) return;

		// PitchYin, the single-frame estimator - NOT
		// PitchYinProbabilistic, deliberately, measured
		// before deciding: PYP's internal frame cutter
		// centres and zero-pads its frames, so fed one
		// 2048-sample window it analyses half silence and
		// reported a 220Hz sine as 70Hz; even on a long
		// signal it sat 52 cents flat (213.5Hz). PitchYin on
		// the same window read 219.79Hz, E2 as 82.33Hz, and
		// silence as confidence 0. pYIN's probabilistic part
		// is HMM smoothing over a whole track - exactly what
		// a live stream does not have per window - so the
		// per-frame YIN core is the honest equivalent here,
		// and the Python side's pYIN still judges the full
		// take on stop.
		//
		// The usable range is pitch_detector.py's own
		// PITCH_FLOOR/PITCH_CEILING (E2-C6), not a new
		// convention - but min/maxFrequency here are SEARCH
		// bounds, and a note sitting exactly on a search
		// bound gets excluded (an E2 sine with min=82.4 at
		// 48kHz came back unvoiced; with min=60 it read
		// 82.33). So the bounds sit a few semitones outside
		// the range they exist to cover, verified edge-
		// inclusive at both 44.1k and 48k. The 0.5
		// confidence gate sits in a measured gap: white
		// noise scored 0.10, a quiet real tone 1.00,
		// tone-over-noise 0.98.
		const vector = this.essentia.arrayToVector(samples);
		let freq = 0;
		try {
			const result = this.essentia.PitchYin(
				vector,
				WINDOW,
				true, // parabolic interpolation, the default
				1200, // above C6 (1046.5) - see bound note
				60, // below E2 (82.4) - see bound note
				context.sampleRate,
				0.15 // YIN tolerance, essentia's own default
			);
			if (result.pitch > 0 && result.pitchConfidence > 0.5) {
				freq = result.pitch;
			}

			// TEMPORARY DEBUG - see note above.
			const now = performance.now();
			if (now - lastDebugLog > DEBUG_LOG_INTERVAL_MS) {
				lastDebugLog = now;
				const midi = result.pitch > 0
					? (69 + 12 * Math.log2(result.pitch / 440)).toFixed(2)
					: "-";
				console.log(
					`[mic] raw=${result.pitch.toFixed(1)}Hz ` +
					`conf=${result.pitchConfidence.toFixed(2)} ` +
					`midi=${midi} ` +
					`accepted=${result.pitch > 0 && result.pitchConfidence > 0.5}`
				);
			}
		} finally {
			// The input vector lives on the WASM heap and does
			// not garbage collect; at ~23 windows a second an
			// undeleted vector per window is a real leak.
			// PitchYin's outputs are plain numbers - nothing
			// else to free.
			vector.delete();
		}

		// The gate: freq is 0 for unvoiced/low-confidence
		// frames already; a voiced-but-suspicious frame (an
		// octave jump or a floor grab, per GatedPitchFilter)
		// is turned back into 0 here too, unless it's just
		// been confirmed as real. Both cases draw identically
		// as a gap - the person watching never needs to know
		// which kind of "no reading" this was.
		if (freq > 0) {
			const gated = this.glitchFilter.push(freq);
			freq = gated ?? 0;
		}

		this.livePitch = freq > 0 ? freq : null;

		if (engine.playing) {
			if (!this.wasPlaying) {
				// A new take: the old trace is the previous
				// attempt, and drawing both would be judging
				// by clutter.
				this.trace = [];
				this.wasPlaying = true;
			}
			if (freq > 0) {
				// The singer heard the backing outputLatency
				// late, so the note answered at mic-time T
				// sits at song position T minus that. Fixed
				// offset, no calibration screen, per the plan;
				// automatic bleed measurement is the upgrade
				// path if this feels visibly off on speakers.
				const latency = (context as any).outputLatency || 0;
				const songTime = engine.positionAt(time - latency);
				this.trace.push({ time: songTime, freq });
				if (this.trace.length > MAX_FRAMES) {
					this.trace.splice(0, this.trace.length - MAX_FRAMES);
				}
			}
		} else {
			this.wasPlaying = false;
		}
	}
}

// One tracker, shared by every mount of the component for
// as long as the page lives - the engine's own pattern.
export const mic = new MicPitch();