<script lang="ts">
	import type { MixerPhrase, MixerBar } from "./types";

	// Bar clicking already jumps the notes panel to that
	// bar's phrase - this just removes the need to know
	// which bar a phrase starts on. Clicking a phrase here
	// finds and clicks its first bar, so it goes through the
	// exact same selection path a real bar click does; no
	// second way of choosing where playback starts, just a
	// second way of asking for the same thing.
	interface Props {
		phrases: MixerPhrase[];
		timeline: MixerBar[];
		onSelectBar: (bar: MixerBar, event: MouseEvent | KeyboardEvent) => void;
	}

	let { phrases, timeline, onSelectBar }: Props = $props();

	function firstBarOf(phrase: MixerPhrase): MixerBar | undefined {
		return timeline.find(
			(bar) => bar.start < phrase.end && bar.end > phrase.start
		);
	}

	function select(phrase: MixerPhrase, event: MouseEvent | KeyboardEvent): void {
		const bar = firstBarOf(phrase);
		if (bar) onSelectBar(bar, event);
	}
</script>

{#if phrases.length}
	<div class="phrase-list">
		{#each phrases as phrase}
			<button
				type="button"
				class="phrase"
				onclick={(event) => select(phrase, event)}
				onkeydown={(event) => {
					if (event.key === "Enter" || event.key === " ") {
						event.preventDefault();
						select(phrase, event);
					}
				}}
			>
				{phrase.label}
			</button>
		{/each}
	</div>
{/if}

<style>
	.phrase-list {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
		margin: 4px 0 8px;
	}
	.phrase {
		font: inherit;
		font-size: 11px;
		padding: 4px 8px;
		border: 1px solid var(--border-color-primary);
		border-radius: 12px;
		background: var(--background-fill-primary);
		cursor: pointer;
		white-space: nowrap;
	}
	.phrase:hover {
		background: var(--background-fill-secondary, #f5f5f5);
	}
</style>
