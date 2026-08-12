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

	playing = $state(false);
	offset = $state(0);
	loopFrom: number | null = $state(null);
	loopTo: number | null = $state(null);
	levels: Record<string, number> = $state({});

	// Whether a selected stretch repeats or plays once and
	// stops. Defaults on: shift-clicking a second bar is
	// usually done to work a hard passage on repeat.
	repeat = $state(true);

	position(): number {
		if (!this.context || !this.playing) return this.offset;
		let at = this.offset + (this.context.currentTime - this.startedAt);
		if (this.loopFrom !== null && this.loopTo !== null && at > this.loopTo) {
			const span = this.loopTo - this.loopFrom;
			at = this.loopFrom + ((at - this.loopFrom) % span);
		}
		return at;
	}

	private bytesFrom(base64: string): ArrayBuffer {
		const binary = atob(base64);
		const out = new Uint8Array(binary.length);
		for (let i = 0; i < binary.length; i++) out[i] = binary.charCodeAt(i);
		return out.buffer;
	}

	private async ensureAudio(layers: MixerLayerData[]): Promise<void> {
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

		const fingerprint = layers
			.map((layer) => layer.name + ":" + layer.wav.length)
			.join("|");

		if (this.fingerprint === fingerprint) return;

		for (const name of Object.keys(this.gains)) {
			this.gains[name].disconnect();
		}
		this.buffers = {};
		this.gains = {};

		for (const layer of layers) {
			const gain = this.context.createGain();
			gain.gain.value = this.levels[layer.name] ?? layer.level;
			gain.connect(this.master!);
			this.gains[layer.name] = gain;
			this.buffers[layer.name] = await this.context.decodeAudioData(
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
		const resumeFrom = from ?? this.loopFrom ?? this.position();

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
	select(bar: MixerBarData, shiftKey: boolean): void {
		if (shiftKey && this.loopFrom !== null) {
			this.loopTo = Math.max(bar.end, this.loopFrom + 0.05);
		} else {
			this.loopFrom = bar.start;
			this.loopTo = null;
		}

		this.stopSources();
		this.playing = false;
		this.offset = this.loopFrom ?? bar.start;
	}

	clearLoop(): void {
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