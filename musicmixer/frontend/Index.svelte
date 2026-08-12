<script lang="ts">
	import type { MusicMixerProps, MusicMixerEvents } from "./types";
	import type { MixerBarData } from "./mixerEngine.svelte";
	import { Gradio } from "@gradio/utils";
	import { Block } from "@gradio/atoms";
	import { onDestroy } from "svelte";
	import { engine } from "./mixerEngine.svelte";

	const props = $props();
	const gradio = new Gradio<MusicMixerEvents, MusicMixerProps>(props);

	const layers = $derived(gradio.props.value?.layers ?? []);
	const timeline = $derived(gradio.props.value?.timeline ?? []);

	// Fader positions default from the engine (survives a
	// remount) and fall back to each layer's opening level
	// only the first time that layer is ever seen.
	$effect(() => {
		for (const layer of layers) {
			if (!(layer.name in engine.levels)) {
				engine.levels[layer.name] = layer.level;
			}
		}
	});

	// Loop selection round-trips through Gradio's normal
	// value/change contract, since that already worked from
	// the first test - only the audio needed the engine.
	// Seeded from whatever Python last sent, so a remount
	// mid-selection does not lose it.
	if (
		gradio.props.value?.loop_start != null &&
		engine.loopFrom === null
	) {
		engine.loopFrom = gradio.props.value.loop_start;
		engine.loopTo = gradio.props.value.loop_end ?? null;
	}

	// This instance's own display loop. Destroyed with the
	// instance; the engine and its sound are not.
	let playhead = $state(engine.position());
	let frame: number | null = null;

	function tick(): void {
		playhead = engine.position();
		frame = requestAnimationFrame(tick);
	}
	tick();

	onDestroy(() => {
		if (frame !== null) cancelAnimationFrame(frame);
	});

	function reportValue(): void {
		if (gradio.props.value) {
			gradio.props.value.loop_start = engine.loopFrom;
			gradio.props.value.loop_end = engine.loopTo;
		}
		gradio.dispatch("change");
	}

	function selectBar(bar: MixerBarData, event: MouseEvent | KeyboardEvent): void {
		const wasPlaying = engine.playing;

		// Only tell Python when the range itself changed - a
		// preview click leaves loop_start/loop_end untouched,
		// so there is nothing worth a round trip for, and one
		// fewer round trip is one fewer remount to flicker
		// through.
		const rangeChanged = engine.select(bar, event.shiftKey);
		playhead = engine.position();

		if (rangeChanged) {
			reportValue();
		}

		if (wasPlaying) {
			engine.play(layers);
		}
	}

	function toggleRepeat(): void {
		// Repeat is read once, when play() builds the audio
		// source - it can't take effect on a source that
		// already exists. So a change while playing has to
		// restart from here, with the new setting baked into
		// the new source, rather than trying to mutate one
		// already running.
		if (engine.playing) {
			engine.play(layers, engine.position());
		}
	}

	function clearLoop(): void {
		engine.clearLoop();
		playhead = 0;
		reportValue();
	}

	function levelChanged(name: string): void {
		engine.setLevel(name, engine.levels[name]);
		gradio.dispatch("input");
	}

	function toggleMute(name: string, opening: number): void {
		engine.levels[name] = engine.levels[name] > 0 ? 0 : opening;
		levelChanged(name);
	}

	const currentBar = $derived(
		timeline.find((bar) => playhead >= bar.start && playhead < bar.end)
	);

	const loopLabel = $derived.by(() => {
		if (engine.loopFrom === null) {
			return timeline.length
				? "Click a bar to select where Play starts. Shift-click a later bar to loop a stretch."
				: "";
		}
		if (engine.loopTo === null) {
			return `Play starts at ${engine.loopFrom.toFixed(1)}s. Shift-click a later bar to select a stretch, or press Play.`;
		}
		return engine.repeat
			? `Repeating ${engine.loopFrom.toFixed(1)}s to ${engine.loopTo.toFixed(1)}s. Untick Repeat to play it once, or Clear selection to release it.`
			: `Selected ${engine.loopFrom.toFixed(1)}s to ${engine.loopTo.toFixed(1)}s, playing once. Tick Repeat to loop it.`;
	});
</script>

<Block
	visible={gradio.shared.visible}
	elem_id={gradio.shared.elem_id}
	elem_classes={gradio.shared.elem_classes}
	scale={gradio.shared.scale}
	min_width={gradio.shared.min_width}
	allow_overflow={true}
	padding={true}
>
	<div class="mixer">
		<div class="transport">
			<button onclick={() => engine.play(layers)}>Play</button>
			<button onclick={() => engine.stop()}>Stop</button>
			<button onclick={clearLoop}>Clear selection</button>
			{#if engine.loopFrom !== null && engine.loopTo !== null}
				<label class="repeat">
					<input
						type="checkbox"
						bind:checked={engine.repeat}
						onchange={toggleRepeat}
					/>
					Repeat
				</label>
			{/if}
			<span class="time">{playhead.toFixed(1)}s</span>
		</div>

		{#if timeline.length}
			<div class="strip">
				{#each timeline as bar (bar.bar)}
					<button
						type="button"
						class="bar"
						class:playing={currentBar === bar}
						class:looped={engine.loopFrom !== null &&
							engine.loopTo !== null &&
							bar.start >= engine.loopFrom - 0.001 &&
							bar.end <= engine.loopTo + 0.001}
						onclick={(event) => selectBar(bar, event)}
						onkeydown={(event) => {
							if (event.key === "Enter" || event.key === " ") {
								event.preventDefault();
								selectBar(bar, event);
							}
						}}
					>
						<div class="number">{bar.bar}</div>
						<div class="chord">{bar.name}</div>
						<div class="words">{bar.words}</div>
					</button>
				{/each}
			</div>
			<p class="note">{loopLabel}</p>
		{/if}

		<div class="faders">
			{#each layers as layer (layer.name)}
				<div class="fader-row">
					<span class="name" style="color:{layer.colour}">
						{layer.name}
					</span>
					<button
						class="mute"
						onclick={() => toggleMute(layer.name, layer.level)}
					>
						M
					</button>
					<input
						type="range"
						min="0"
						max="1"
						step="0.05"
						bind:value={engine.levels[layer.name]}
						oninput={() => levelChanged(layer.name)}
					/>
					<span class="value">
						{Math.round((engine.levels[layer.name] ?? 0) * 100)}%
					</span>
				</div>
			{/each}
		</div>
	</div>
</Block>

<style>
	.mixer {
		font-family: sans-serif;
	}
	.transport {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-bottom: 6px;
	}
	.transport button {
		padding: 6px 14px;
		font-size: 13px;
		font-weight: 600;
		cursor: pointer;
	}
	.time {
		font-size: 12px;
		color: var(--body-text-color-subdued);
		margin-left: auto;
	}
	.repeat {
		font-size: 13px;
		display: flex;
		align-items: center;
		gap: 4px;
		cursor: pointer;
	}
	.repeat input[type="checkbox"] {
		/* Gradio's theme resets input appearance broadly
		   enough that a checked box drew no checkmark at all
		   - it wasn't disappearing, there was simply nothing
		   left to render once checked. Forced back on and
		   given an explicit colour rather than an inherited
		   one that might match its own background. */
		appearance: auto;
		accent-color: #2e7d32;
		width: 15px;
		height: 15px;
	}

	.strip {
		display: flex;
		gap: 4px;
		overflow-x: auto;
		padding: 8px 2px;
	}
	.bar {
		min-width: 84px;
		border: 1px solid var(--border-color-primary);
		border-radius: 4px;
		padding: 6px 8px;
		cursor: pointer;
		background: var(--background-fill-primary);
		flex: 0 0 auto;
		font: inherit;
		text-align: left;
	}
	.bar.playing {
		border-color: #2e7d32 !important;
		background: #e8f5e9 !important;
	}
	.bar.looped {
		background: #fff3e0 !important;
	}
	.bar .number {
		font-size: 10px;
		color: var(--body-text-color-subdued);
	}
	.bar .chord {
		font-weight: 700;
		font-size: 14px;
	}
	.bar .words {
		font-size: 11px;
		color: var(--body-text-color-subdued);
		margin-top: 2px;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		max-width: 140px;
	}

	.note {
		font-size: 13px;
		color: var(--body-text-color-subdued);
	}

	.fader-row {
		display: flex;
		align-items: center;
		gap: 12px;
		margin: 6px 0;
	}
	.name {
		width: 120px;
		font-size: 13px;
		font-weight: 600;
	}
	.mute {
		width: 30px;
		padding: 4px 0;
		font-size: 13px;
		cursor: pointer;
	}
	input[type="range"] {
		flex: 1;
		max-width: 320px;
	}
	.value {
		width: 38px;
		font-size: 12px;
		color: var(--body-text-color-subdued);
		text-align: right;
	}
</style>