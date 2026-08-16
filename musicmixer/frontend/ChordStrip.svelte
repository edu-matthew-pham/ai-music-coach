<script lang="ts">
	import { engine } from "./mixerEngine.svelte";
	import type { MixerBar } from "./types";

	interface Props {
		timeline: MixerBar[];
		playhead: number;
		follow: boolean;
		onSelectBar: (bar: MixerBar, event: MouseEvent | KeyboardEvent) => void;
	}

	let { timeline, playhead, follow, onSelectBar }: Props = $props();

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

	let barElements: Record<number, HTMLElement> = {};

	$effect(() => {
		if (follow && currentBar && barElements[currentBar.bar]) {
			barElements[currentBar.bar].scrollIntoView({
				behavior: "smooth",
				inline: "center",
				block: "nearest"
			});
		}
	});

	// One tick per beat, from that bar's own beat count - not
	// a fixed number, since bars are not guaranteed equal
	// length. Math.round guards against float drift (a real
	// bar length arrives as a whole number, but read from
	// seconds-derived data rather than typed directly).
	function ticksFor(bar: MixerBar): number[] {
		return Array.from({ length: Math.round(bar.beats) }, (_, i) => i);
	}

	// Left offset for a chord mark, as a percentage across
	// the bar's own width - proportional to its true position
	// (beat_in_bar may be a half, from a syncopated split),
	// not snapped to the nearest tick.
	function positionOf(chord: { beat_in_bar: number }, bar: MixerBar): number {
		return (chord.beat_in_bar / bar.beats) * 100;
	}
</script>

{#if timeline.length}
	<div class="strip">
		{#each timeline as bar (bar.bar)}
			<button
				type="button"
				class="bar"
				data-bar={bar.bar}
				class:playing={currentBar === bar}
				class:looped={engine.loopFrom !== null &&
					engine.loopTo !== null &&
					bar.start >= engine.loopFrom - 0.001 &&
					bar.end <= engine.loopTo + 0.001}
				bind:this={barElements[bar.bar]}
				onclick={(event) => onSelectBar(bar, event)}
				onkeydown={(event) => {
					if (event.key === "Enter" || event.key === " ") {
						event.preventDefault();
						onSelectBar(bar, event);
					}
				}}
			>
				<div class="number">{bar.bar}</div>
				<div class="beats">
					{#each ticksFor(bar) as tick}
						<div class="tick" style="left: {(tick / bar.beats) * 100}%"></div>
					{/each}
					{#each bar.chords as chord}
						<div
							class="chord-mark"
							class:carried={chord.carried}
							style="left: {positionOf(chord, bar)}%"
						>
							{chord.name}
						</div>
					{/each}
				</div>
				<div class="words">{bar.words}</div>
			</button>
		{/each}
	</div>
	<p class="note">{loopLabel}</p>
{/if}

<style>
	.strip {
		display: flex;
		gap: 4px;
		overflow-x: auto;
		padding: 8px 2px;
	}
	.bar {
		min-width: 96px;
		border: 1px solid var(--border-color-primary);
		border-radius: 4px;
		padding: 6px 8px 8px;
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
	/* The beat/chord row is a relative-positioned strip so
	   ticks and chord marks can be placed at an exact
	   percentage across the bar's own width - a chord on
	   beat 3.5 of 4 sits at 87.5%, not centred or snapped to
	   a fixed slot. Height and exact tick styling are a
	   first pass, not verified against a real render yet. */
	.bar .beats {
		position: relative;
		height: calc(28px * var(--read-scale, 1));
		margin-top: 4px;
		border-bottom: 1px solid var(--border-color-primary);
	}
	.bar .tick {
		position: absolute;
		bottom: 0;
		width: 1px;
		height: 6px;
		background: var(--border-color-primary);
	}
	.bar .chord-mark {
		position: absolute;
		top: 0;
		transform: translateX(-2px);
		font-weight: 700;
		font-size: calc(13px * var(--read-scale, 1));
		white-space: nowrap;
	}
	/* A chord already sounding when the bar opens, rather
	   than new here - the chart's own "." made visual.
	   Dimmed rather than hidden: the bar is not empty, the
	   chord just is not new. */
	.bar .chord-mark.carried {
		font-weight: 400;
		opacity: 0.5;
	}
	.bar .words {
		font-size: calc(11px * var(--read-scale, 1));
		color: var(--body-text-color-subdued);
		margin-top: 2px;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		max-width: 160px;
	}
	.note {
		font-size: 13px;
		color: var(--body-text-color-subdued);
	}
</style>