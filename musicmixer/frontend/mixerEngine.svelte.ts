// mixerEngine.svelte.ts
//
// Audio state that outlives the component.
//
// Gradio 6 tears this component down and rebuilds it on
// every event round trip - confirmed directly, not assumed:
// a counter kept on window climbed cleanly across dozens of
// mount/destroy pairs while a counter kept as component
// state would have reset each time. So anything that must
// survive a click - the sound playing, where the playhead
// is, the fader levels - cannot live inside Index.svelte.
// It lives here instead: state declared at module level, in
// a .svelte.ts file, which Svelte keeps alive for as long as
// the page does, independent of any one component instance.
//
// A remount then costs nothing. The fresh instance re-reads
// this engine and shows the true position; it does not reset
// to zero and it does not orphan the sound.

export interface MixerLayerData {
	name: string;
	level: number;
	colour: string;
	wav: string;
}

export interface MixerBarData {
	bar: number;
	name: string;
	start: number;
	end: number;
	words: string;
}

// What select() actually needs from whatever gets clicked -
// a bar or a phrase both qualify, structurally, without
// either needing to know about the other. One selection
// method, one anchor, shared by both panels: clicking a bar
// then shift-clicking a phrase to extend the range (or the
// other way round) is one continuous gesture across two
// different granularities, not two unrelated selections
// fighting over the same loopFrom/loopTo.
export interface TimeSpan {
	start: number;
	end: number;
}

class MixerEngine {
	private context: AudioContext | null = null;
	private master: GainNode | null = null;
	private buffers: Record<string, AudioBuffer> = {};
	private gains: Record<string, GainNode> = {};
	private sources: AudioBufferSourceNode[] = [];
	private startedAt = 0;

	// A fingerprint of the loaded music, so buffers are
	// decoded once per song rather than once per remount -
	// remounts are frequent here and decoding is not free.
	private fingerprint = "";

	// A second fingerprint, checked separately from the one
	// above. That one only matters when play() actually runs;
	// this one is checked the moment new layers arrive from
	// Python, in noteLayers() below, so a loop selected against
	// one song's timeline never survives into a different
	// song's - it would otherwise sit there in seconds that
	// mean nothing until Play was pressed and forced a decode.
	private selectionFingerprint = "";

	playing = $state(false);
	offset = $state(0);
	loopFrom: number | null = $state(null);
	loopTo: number | null = $state(null);
	levels: Record<string, number> = $state({});

	// The first bar clicked, kept separately from loopFrom/
	// loopTo. A shift-click computes the range against this
	// fixed point - min of both starts, max of both ends -
	// so selecting backwards (click bar 4, shift-click bar 1)
	// works the same as selecting forwards. Without it, the
	// range math assumed the second click was always later,
	// and a backward selection collapsed to a few
	// hundredths of a second rather than spanning the bars.
	private anchor: TimeSpan | null = null;

	// Whether a selected stretch repeats or plays once and
	// stops. Defaults on: shift-clicking a second bar is
	// usually done to work a hard passage on repeat.
	repeat = $state(true);

	position(): number {
		if (!this.context) return this.offset;
		return this.positionAt(this.context.currentTime);
	}

	// The same mapping as position(), for any moment on the
	// context's clock - what lets a mic frame captured at
	// time T ask where in the song T was, including through
	// a loop's wrap-around. Exists so the pitch tracker
	// shares the engine's one idea of where the playhead
	// is rather than keeping a second clock of its own.
	positionAt(contextTime: number): number {
		if (!this.context || !this.playing) return this.offset;
		let at = this.offset + (contextTime - this.startedAt);
		if (this.loopFrom !== null && this.loopTo !== null && at > this.loopTo) {
			const span = this.loopTo - this.loopFrom;
			at = this.loopFrom + ((at - this.loopFrom) % span);
		}
		return at;
	}

	// The one AudioContext, created on first need - shared
	// with the mic tracker so playback and capture live on
	// one clock in one graph (which is also what makes
	// automatic bleed measurement possible later, if the
	// fixed latency offset ever proves not enough).
	ensureContext(): AudioContext {
		if (!this.context) {
			this.context = new (window.AudioContext ||
				(window as any).webkitAudioContext)();

			const master = this.context.createGain();
			master.gain.value = 0.7;

			// Several layers summed can clip; a limiter turns
			// that into a smooth reduction instead of a crackle.
			const limiter = this.context.createDynamicsCompressor();
			limiter.threshold.value = -6;
			limiter.knee.value = 0;
			limiter.ratio.value = 20;
			limiter.attack.value = 0.003;
			limiter.release.value = 0.15;

			master.connect(limiter);
			limiter.connect(this.context.destination);
			this.master = master;
		}
		return this.context;
	}

	private bytesFrom(base64: string): ArrayBuffer {
		const binary = atob(base64);
		const out = new Uint8Array(binary.length);
		for (let i = 0; i < binary.length; i++) out[i] = binary.charCodeAt(i);
		return out.buffer;
	}

	// Length alone can collide: two different phrases of the
	// same duration fingerprint identically, and the old
	// buffers would keep playing under the new song's timeline.
	// A few characters from each end of the base64 catches a
	// real content difference at near-enough-zero cost - cheap
	// enough to run on every remount, unlike walking the whole
	// string, which this component (Gradio 6 rebuilds it on
	// every click) would otherwise do constantly.
	private computeFingerprint(layers: MixerLayerData[]): string {
		const EDGE = 24;

		return layers
			.map((layer) => {
				const wav = layer.wav;
				return (
					layer.name + ":" + wav.length + ":" +
					wav.slice(0, EDGE) + ":" + wav.slice(-EDGE)
				);
			})
			.join("|");
	}

	// Called whenever the component sees a new set of layers,
	// before anything has necessarily been decoded - so a
	// stale loop is cleared the moment new music arrives, not
	// only once Play is next pressed. A loop is seconds into a
	// specific song; carried into a different one it is just a
	// stretch of arbitrary time, possibly past the new song's
	// end.
	noteLayers(layers: MixerLayerData[]): void {
		const fingerprint = this.computeFingerprint(layers);

		if (fingerprint !== this.selectionFingerprint) {
			this.clearLoop();
			this.selectionFingerprint = fingerprint;
		}
	}

	private async ensureAudio(layers: MixerLayerData[]): Promise<void> {
		const context = this.ensureContext();

		const fingerprint = this.computeFingerprint(layers);

		if (this.fingerprint === fingerprint) return;

		for (const name of Object.keys(this.gains)) {
			this.gains[name].disconnect();
		}
		this.buffers = {};
		this.gains = {};

		for (const layer of layers) {
			const gain = context.createGain();
			gain.gain.value = this.levels[layer.name] ?? layer.level;
			gain.connect(this.master!);
			this.gains[layer.name] = gain;
			this.buffers[layer.name] = await context.decodeAudioData(
				this.bytesFrom(layer.wav)
			);
		}

		this.fingerprint = fingerprint;
	}

	private stopSources(): void {
		for (const source of this.sources) {
			// Detached first: calling stop() on a source also
			// fires its onended event, per the Web Audio spec -
			// so a deliberate stop looks identical to reaching
			// the end. Left attached, the old source's handler
			// fires after the fact and wrongly clears `playing`
			// even though a newer playback has since started.
			source.onended = null;

			try {
				source.stop();
			} catch (err) {
				/* already stopped */
			}
			source.disconnect();
		}
		this.sources = [];
	}

	async play(layers: MixerLayerData[], from?: number): Promise<void> {
		// offset is kept correct by every select() branch -
		// the start of a newly completed range, or wherever a
		// preview click last moved to - so trusting it here
		// is what makes a preview click during playback
		// actually resume from where it was clicked, rather
		// than snapping back to the range's start regardless.
		const resumeFrom = from ?? this.offset;

		this.stopSources();
		this.playing = false;

		await this.ensureAudio(layers);
		if (!this.context) return;
		if (this.context.state === "suspended") await this.context.resume();

		this.offset = resumeFrom;
		this.startedAt = this.context.currentTime;
		this.playing = true;

		for (const layer of layers) {
			const source = this.context.createBufferSource();
			source.buffer = this.buffers[layer.name];

			if (this.loopFrom !== null && this.loopTo !== null && this.repeat) {
				source.loop = true;
				source.loopStart = this.loopFrom;
				source.loopEnd = this.loopTo;
			}

			source.connect(this.gains[layer.name]);
			source.start(this.startedAt, this.offset);

			// A one-shot selection stops exactly at its end.
			// Scheduled after start(), never before: the spec
			// forbids stop() on a source that has not started,
			// and calling it early threw per layer and left
			// playback half-initialised.
			if (this.loopFrom !== null && this.loopTo !== null && !this.repeat) {
				source.stop(this.startedAt + (this.loopTo - this.offset));
			}

			this.sources.push(source);
		}

		// Reaching the end on its own - whether the whole
		// song, or a one-shot selection's scheduled stop -
		// should still leave the transport usable without a
		// second press.
		if (this.sources.length) {
			this.sources[0].onended = () => {
				this.playing = false;
			};
		}
	}

	stop(): void {
		this.offset = this.position();
		this.stopSources();
		this.playing = false;
	}

	// Selection only - moves the start point and the
	// playhead. Playing straight from a click made the
	// visual update depend on the async audio path; a
	// selection is a plain assignment and cannot go stale.
	// A loop is only discarded when a click clearly means to
	// leave it. Clicking somewhere inside the selected range
	// is scrubbing - it moves where playback starts without
	// touching the range, the way markers work in a video
	// editor. Clicking outside the range means you have moved
	// on from it, so it is replaced with a fresh anchor here.
	// A shift-click after a range is already complete always
	// starts over too, inside or outside, since shift is an
	// unambiguous "define a new range" gesture either way.
	//
	// span only needs start/end - a bar and a phrase both
	// qualify without either type knowing about the other,
	// which is what lets a bar click and a phrase shift-click
	// complete one shared range together.
	select(span: TimeSpan, shiftKey: boolean): boolean {
		const hadRange = this.loopFrom !== null && this.loopTo !== null;
		const previousFrom = this.loopFrom;
		const previousTo = this.loopTo;

		const insideRange =
			hadRange &&
			span.start >= this.loopFrom! - 0.001 &&
			span.end <= this.loopTo! + 0.001;

		if (shiftKey && this.anchor !== null && !hadRange) {
			// Completing a range from the existing anchor - the
			// min/max works the same whether the span just
			// clicked is later or earlier than the first one.
			const start = Math.min(this.anchor.start, span.start);
			const end = Math.max(this.anchor.end, span.end);
			this.loopFrom = start;
			this.loopTo = Math.max(end, start + 0.05);
			this.offset = this.loopFrom;
		} else if (!shiftKey && insideRange) {
			// A scrub: move the playhead, leave the range and
			// its anchor exactly as they were.
			this.offset = span.start;
		} else {
			// Nothing selected yet, a click outside the current
			// range, or a shift-click after a range was already
			// complete: start over here.
			this.anchor = span;
			this.loopFrom = span.start;
			this.loopTo = null;
			this.offset = span.start;
		}

		this.stopSources();
		this.playing = false;

		return this.loopFrom !== previousFrom || this.loopTo !== previousTo;
	}

	clearLoop(): void {
		this.anchor = null;
		this.loopFrom = null;
		this.loopTo = null;
		this.offset = 0;
		this.stopSources();
		this.playing = false;
	}

	setLevel(name: string, value: number): void {
		this.levels[name] = value;
		if (this.gains[name] && this.context) {
			this.gains[name].gain.setTargetAtTime(
				value,
				this.context.currentTime,
				0.01
			);
		}
	}
}

// One engine, shared by every mount of the component for
// as long as the page lives.
export const engine = new MixerEngine();