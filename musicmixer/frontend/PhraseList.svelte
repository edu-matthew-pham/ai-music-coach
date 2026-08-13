<script lang="ts">
	import type { MixerPhrase } from "./types";

	// Selecting a phrase now goes straight to its own exact
	// start and end - engine.selectRange - rather than being
	// translated into "click this bar" first. That translation
	// used to mean losing a pickup note: a phrase starting a
	// fraction of a second before its bar's downbeat would
	// snap to the whole bar, dragging in whatever the previous
	// bar was still finishing. This keeps phrase timing exact.
	interface Props {
		phrases: MixerPhrase[];
		onSelectPhrase: (phrase: MixerPhrase) => void;
		narrow?: boolean;
	}

	let { phrases, onSelectPhrase, narrow = false }: Props = $props();

	// A row of buttons wraps onto several lines on a phone,
	// which reads as clutter rather than a list. The native
	// picker below the width breakpoint gives the same choice
	// through the platform's own dropdown UI instead - one
	// line, one tap, no layout work of our own to get right.
	function handleChange(event: Event): void {
		const index = Number((event.currentTarget as HTMLSelectElement).value);

		if (!Number.isNaN(index) && phrases[index]) {
			onSelectPhrase(phrases[index]);
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
			{#each phrases as phrase}
				<button
					type="button"
					class="phrase"
					onclick={() => onSelectPhrase(phrase)}
					onkeydown={(event) => {
						if (event.key === "Enter" || event.key === " ") {
							event.preventDefault();
							onSelectPhrase(phrase);
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