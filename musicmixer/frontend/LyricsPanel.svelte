<script lang="ts">
	import type { MixerNote, MixerPhrase } from "./types";

	// No pitch here, deliberately - this is the other half of
	// the SingStar reference: words as pills in a row, the
	// current one lit up, the next line already visible so
	// there's a moment to read ahead before it arrives. The
	// pitch-box view (NotesPanel) is a different, denser tool
	// for a different question; this one just answers "what
	// do I sing right now."
	interface Props {
		notes: MixerNote[];
		phrases: MixerPhrase[];
		playhead: number;
	}

	let { notes, phrases, playhead }: Props = $props();

	// Words live on melody notes only - harmonies and bass
	// never carry them, same rule the note view follows.
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

	// Same rule as the note view: the page changes once the
	// current phrase has actually finished, not the instant
	// the next one begins, so a still-sounding word is never
	// swapped out from under the singer.
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
	// short rest) should keep the last one lit rather than
	// going dark until the next one starts.
	const activeWord = $derived.by(() => {
		let active: MixerNote | null = null;
		for (const note of currentWords) {
			if (note.start <= playhead) active = note;
			else break;
		}
		return active;
	});

	function caption(phrase: MixerPhrase | null): string {
		if (!phrase) return "";
		return phrase.label.replace(/^\d+\.\s*/, "");
	}
</script>

{#if currentPhrase}
	<div class="lyrics-panel">
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

		<p class="caption current">{caption(currentPhrase)}</p>
		{#if nextPhrase}
			<p class="caption next">{caption(nextPhrase)}</p>
		{/if}
	</div>
{:else}
	<p class="lyrics-empty">No lyrics to show yet.</p>
{/if}

<style>
	.lyrics-panel {
		padding: 12px 4px;
	}
	.word-row {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px;
		margin-bottom: 10px;
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
	.caption {
		font-size: 18px;
		margin: 2px 0;
	}
	.caption.current {
		font-weight: 600;
	}
	.caption.next {
		opacity: 0.5;
		font-size: 15px;
	}
	.lyrics-empty {
		font-size: 13px;
		color: var(--body-text-color-subdued);
	}
</style>