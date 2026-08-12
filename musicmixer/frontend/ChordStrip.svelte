<script lang="ts">
	import { engine } from "./mixerEngine.svelte";
	import type { MixerBarData } from "./mixerEngine.svelte";

	interface Props {
		timeline: MixerBarData[];
		playhead: number;
		follow: boolean;
		onSelectBar: (bar: MixerBarData, event: MouseEvent | KeyboardEvent) => void;
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
				<div class="chord">{bar.name}</div>
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
</style>