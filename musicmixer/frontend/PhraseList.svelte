<script lang="ts">
	import { engine } from "./mixerEngine.svelte";
	import type { MixerPhrase } from "./types";

	// Phrases behave like the chart strip now: click selects,
	// seeks, and plays; shift-click extends a range from the
	// last clicked phrase or bar to cover several for
	// repeating (Repeat toggles whether that range loops or
	// plays once). engine.select() is the same method
	// ChordStrip's bars use - phrase and bar clicks share one
	// anchor, so either can extend a range the other started.
	//
	// Kept on its own exact start and end rather than
	// translated into "click this bar" first: a phrase can
	// start on a pickup note a fraction of a second before
	// its bar's downbeat, and selecting "that bar" to reach
	// it would drag in whatever the previous bar was still
	// finishing.
	interface Props {
		phrases: MixerPhrase[];
		playhead: number;
		onSelectPhrase: (phrase: MixerPhrase, event: MouseEvent | KeyboardEvent) => void;
		narrow?: boolean;
	}

	let { phrases, playhead, onSelectPhrase, narrow = false }: Props = $props();

	const currentPhrase = $derived(
		phrases.find((phrase) => playhead >= phrase.start && playhead < phrase.end)
	);

	// One scrolling row rather than a wrapped block: the
	// list is navigation, and two or three wrapped lines of
	// it pushed everything below down the page for the sake
	// of phrases that are not playing. Same follow-scroll
	// ChordStrip already does for bars, keyed by index since
	// phrases carry no id of their own.
	let phraseElements: Record<number, HTMLElement> = {};

	$effect(() => {
		const index = currentPhrase ? phrases.indexOf(currentPhrase) : -1;
		if (index >= 0 && phraseElements[index]) {
			phraseElements[index].scrollIntoView({
				behavior: "smooth",
				inline: "center",
				block: "nearest"
			});
		}
	});

	// A row of buttons wraps onto several lines on a phone,
	// which reads as clutter rather than a list. The native
	// picker below the width breakpoint gives the same choice
	// through the platform's own dropdown UI instead - one
	// line, one tap, no layout work of our own to get right.
	// Shift-click has no natural equivalent in a native
	// select, so the dropdown only ever does a plain choice.
	function handleChange(event: Event): void {
		const index = Number((event.currentTarget as HTMLSelectElement).value);

		if (!Number.isNaN(index) && phrases[index]) {
			onSelectPhrase(phrases[index], event as unknown as MouseEvent);
		}
	}
</script>

{#if phrases.length}
	{#if narrow}
		<select class="phrase-select" onchange={handleChange}>
			<option value="" disabled selected>Jump to phrase…</option>
			{#each phrases as phrase, index}
				<option value={index}>{phrase.label}</option>
			{/each}
		</select>
	{:else}
		<div class="phrase-list">
			{#each phrases as phrase, index}
				<button
					type="button"
					class="phrase"
					bind:this={phraseElements[index]}
					class:playing={currentPhrase === phrase}
					class:looped={engine.loopFrom !== null &&
						engine.loopTo !== null &&
						phrase.start >= engine.loopFrom - 0.001 &&
						phrase.end <= engine.loopTo + 0.001}
					onclick={(event) => onSelectPhrase(phrase, event)}
					onkeydown={(event) => {
						if (event.key === "Enter" || event.key === " ") {
							event.preventDefault();
							onSelectPhrase(phrase, event);
						}
					}}
				>
					{phrase.label}
				</button>
			{/each}
		</div>
	{/if}
{/if}

<style>
	.phrase-list {
		display: flex;
		flex-wrap: nowrap;
		overflow-x: auto;
		gap: 4px;
		margin: 4px 0 8px;
		padding-bottom: 2px;
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
	.phrase.playing {
		border-color: #2e7d32 !important;
		background: #e8f5e9 !important;
	}
	.phrase.looped {
		background: #fff3e0;
	}
	.phrase-select {
		font: inherit;
		font-size: 13px;
		width: 100%;
		padding: 8px 10px;
		margin: 4px 0 8px;
		border: 1px solid var(--border-color-primary);
		border-radius: 6px;
		background: var(--background-fill-primary);
	}
</style>