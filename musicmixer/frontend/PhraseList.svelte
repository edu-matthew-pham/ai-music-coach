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
	}

	let { phrases, onSelectPhrase }: Props = $props();
</script>

{#if phrases.length}
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