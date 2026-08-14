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

	async enable(): Promise<void> {
		if (this.state === "on" || this.state === "starting") return;
		this.state = "starting";

		try {
			// Echo cancellation on: the backing track coming
			// out of the speakers is exactly the echo it
			// exists to remove. Gain control and noise
			// suppression off - both reshape a sustained sung
			// note, which is the entire signal here.
			// Headphones sidestep all of this anyway.
			this.stream = await navigator.mediaDevices.getUserMedia({
				audio: {
					echoCancellation: true,
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
		} finally {
			// The input vector lives on the WASM heap and does
			// not garbage collect; at ~23 windows a second an
			// undeleted vector per window is a real leak.
			// PitchYin's outputs are plain numbers - nothing
			// else to free.
			vector.delete();
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
