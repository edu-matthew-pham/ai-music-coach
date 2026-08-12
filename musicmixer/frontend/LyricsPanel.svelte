<script lang="ts">
	import { lyricsSentenceStyle } from "./mixerPanels.svelte";
	import type { MixerNote, MixerPhrase } from "./types";

	// One representation of the words, not two shown at once -
	// pills that light up individually, or a flowing sentence
	// whose words change colour as they pass. Showing both was
	// the same information twice on screen.
	interface Props {
		notes: MixerNote[];
		phrases: MixerPhrase[];
		playhead: number;
	}

	let { notes, phrases, playhead }: Props = $props();

	const words = $derived(
		notes.filter((note) => note.layer === "Melody" && note.word)
	);

	const effectivePhrases = $derived.by((): MixerPhrase[] => {
		if (phrases.length) return phrases;
		if (!words.length) return [];
		const end = words.reduce(
			(max, note) => Math.max(max, note.start + note.length), 0
		);
		return [{ start: 0, end, label: "Whole part" }];
	});

	const currentIndex = $derived.by(() => {
		if (!effectivePhrases.length) return -1;
		const found = effectivePhrases.findIndex((phrase) => playhead < phrase.end);
		return found === -1 ? effectivePhrases.length - 1 : found;
	});

	const currentPhrase = $derived(
		currentIndex >= 0 ? effectivePhrases[currentIndex] : null
	);

	const nextPhrase = $derived(
		currentIndex >= 0 && currentIndex + 1 < effectivePhrases.length
			? effectivePhrases[currentIndex + 1]
			: null
	);

	function wordsIn(phrase: MixerPhrase | null): MixerNote[] {
		if (!phrase) return [];
		return words.filter(
			(note) => note.start >= phrase.start && note.start < phrase.end
		);
	}

	const currentWords = $derived(wordsIn(currentPhrase));
	const nextWords = $derived(wordsIn(nextPhrase));

	// Whichever word the playhead is inside of, or has most
	// recently passed - a gap between words (a held note, a
	// short rest) keeps the last one lit rather than going
	// dark until the next one starts.
	const activeWord = $derived.by(() => {
		let active: MixerNote | null = null;
		for (const note of currentWords) {
			if (note.start <= playhead) active = note;
			else break;
		}
		return active;
	});

	// A word ending in a hyphen is mid-syllable, not a word
	// boundary - "Bil-" then "ly" should read as "Bil-ly"
	// with nothing between them, while every real word gets
	// a space after it. Computed here rather than left as a
	// literal space in the markup, since that space sits
	// right next to a closing tag and whitespace in exactly
	// that position is the kind of thing template compilers
	// sometimes trim - safer to make it an explicit string.
	function separatorAfter(word: string | undefined): string {
		return word?.endsWith("-") ? "" : " ";
	}
</script>

{#if currentPhrase}
	<div class="lyrics-panel">
		<label class="style-toggle">
			<input type="checkbox" bind:checked={lyricsSentenceStyle.value} />
			Sentence style
		</label>

		{#if lyricsSentenceStyle.value}
			<p class="sentence current">{#each currentWords as note}<span
					class="sentence-word"
					class:sung={note.start <= playhead}
				>{note.word}{separatorAfter(note.word)}</span>{/each}</p>
			{#if nextWords.length}
				<p class="sentence next">
					{#each nextWords as note}<span>{note.word}{separatorAfter(note.word)}</span>{/each}
				</p>
			{/if}
		{:else}
			<div class="word-row">
				{#each currentWords as note}
					<span class="word" class:active={note === activeWord}>
						{note.word}
					</span>
				{/each}
				{#if nextWords.length}
					<span class="row-gap"></span>
					{#each nextWords as note}
						<span class="word next">{note.word}</span>
					{/each}
				{/if}
			</div>
		{/if}
	</div>
{:else}
	<p class="lyrics-empty">No lyrics to show yet.</p>
{/if}

<style>
	.lyrics-panel {
		padding: 12px 4px;
	}
	.style-toggle {
		font-size: 11px;
		color: var(--body-text-color-subdued);
		display: flex;
		align-items: center;
		gap: 4px;
		cursor: pointer;
		margin-bottom: 10px;
		width: fit-content;
	}
	.style-toggle input[type="checkbox"] {
		appearance: auto;
		accent-color: #607d8b;
		width: 12px;
		height: 12px;
	}

	.word-row {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px;
	}
	.word {
		font-size: 15px;
		font-weight: 600;
		padding: 4px 12px;
		border-radius: 14px;
		border: 1px solid var(--border-color-primary);
		background: var(--background-fill-primary);
		color: var(--body-text-color);
	}
	.word.active {
		background: #2e7d32;
		border-color: #2e7d32;
		color: white;
	}
	.word.next {
		opacity: 0.45;
		font-size: 13px;
	}
	.row-gap {
		width: 16px;
	}

	.sentence {
		font-size: 20px;
		margin: 4px 0;
	}
	.sentence.next {
		font-size: 16px;
		opacity: 0.4;
	}
	.sentence-word {
		color: var(--body-text-color-subdued);
	}
	.sentence-word.sung {
		color: #2e7d32;
		font-weight: 700;
	}

	.lyrics-empty {
		font-size: 13px;
		color: var(--body-text-color-subdued);
	}
</style>