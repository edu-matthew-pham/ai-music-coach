<script lang="ts">
	import type { MixerBar, MixerNote, MixerPhrase } from "./types";
	import { lyricsShowChords, lyricsShowBars } from "./mixerPanels.svelte";

	interface Props {
		notes: MixerNote[];
		timeline: MixerBar[];
		phrases: MixerPhrase[];
		playhead: number;
	}

	let { notes, timeline, phrases, playhead }: Props = $props();

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

	// A chord's real position in seconds - the same
	// beat_in_bar/bar.beats fraction ChordStrip and the Notes
	// panel already use, just landed on this panel's own
	// word-by-word layout instead of a bar strip or a pitch
	// axis.
	function chordTime(bar: MixerBar, chord: MixerBar["chords"][number]): number {
		return bar.start + (chord.beat_in_bar / bar.beats) * (bar.end - bar.start);
	}

	type RhythmEvent =
		| { time: number; type: "chord"; name: string }
		| { time: number; type: "bar" };

	// Every real chord CHANGE inside this phrase - carried
	// entries (the same chord still sounding when a later bar
	// opens) are dropped here, not just dimmed, per the "only
	// the bold ones" steer: a bar with nothing new happening
	// shows its "|" and nothing else.
	function chordEvents(phrase: MixerPhrase | null): RhythmEvent[] {
		if (!phrase || !lyricsShowChords.value) return [];
		const found: RhythmEvent[] = [];
		for (const bar of timeline) {
			if (bar.start >= phrase.end || bar.end <= phrase.start) continue;
			for (const chord of bar.chords) {
				if (chord.carried) continue;
				const time = chordTime(bar, chord);
				if (time >= phrase.start && time < phrase.end) {
					found.push({ time, type: "chord", name: chord.name });
				}
			}
		}
		return found;
	}

	// "|" at every bar's own start, unconditionally - a
	// landmark independent of whether a chord happens to sit
	// there too. Ordered before chords in the merge below so
	// a coincident chord reads "| G", not "G |".
	function barEvents(phrase: MixerPhrase | null): RhythmEvent[] {
		if (!phrase || !lyricsShowBars.value) return [];
		const found: RhythmEvent[] = [];
		for (const bar of timeline) {
			if (bar.start >= phrase.start && bar.start < phrase.end) {
				found.push({ time: bar.start, type: "bar" });
			}
		}
		return found;
	}

	function allEvents(phrase: MixerPhrase | null): RhythmEvent[] {
		return [...barEvents(phrase), ...chordEvents(phrase)].sort((a, b) => a.time - b.time);
	}

	// Anything before the phrase's own first sung word has no
	// word to attach to - an instrumental intro, most often.
	// Piling all of it onto word 0 read as a wall of bars
	// stacked on the first syllable; split off instead into
	// its own lead-in line, the way a real lead sheet prints
	// intro bars before the vocal starts.
	function splitLeadIn(
		events: RhythmEvent[],
		words: MixerNote[]
	): { leadIn: RhythmEvent[]; rest: RhythmEvent[] } {
		if (!words.length) return { leadIn: events, rest: [] };
		const firstStart = words[0].start;
		return {
			leadIn: events.filter((event) => event.time < firstStart),
			rest: events.filter((event) => event.time >= firstStart)
		};
	}

	function leadInText(events: RhythmEvent[]): string {
		return events.map((event) => (event.type === "bar" ? "|" : event.name)).join(" ");
	}

	// Which events belong above each word - an event is
	// attached to whichever word is sounding when it happens,
	// the same "timing decides, not eyeballing" rule the rest
	// of this feature follows.
	function eventsByWord(
		words: MixerNote[],
		events: RhythmEvent[]
	): Map<number, RhythmEvent[]> {
		const map = new Map<number, RhythmEvent[]>();
		if (!words.length || !events.length) return map;

		let wordIndex = 0;
		for (const event of events) {
			while (
				wordIndex < words.length - 1 &&
				words[wordIndex + 1].start <= event.time
			) {
				wordIndex++;
			}
			const existing = map.get(wordIndex) ?? [];
			existing.push(event);
			map.set(wordIndex, existing);
		}
		return map;
	}

	const currentSplit = $derived(splitLeadIn(allEvents(currentPhrase), currentWords));
	const nextSplit = $derived(splitLeadIn(allEvents(nextPhrase), nextWords));

	const currentEventsByWord = $derived(eventsByWord(currentWords, currentSplit.rest));
	const nextEventsByWord = $derived(eventsByWord(nextWords, nextSplit.rest));
</script>

{#snippet wordSpan(note: MixerNote, i: number, eventsMap: Map<number, RhythmEvent[]>, showSung: boolean)}<span class="word-unit">{#if eventsMap.get(i)}<span class="chord-tags">{#each eventsMap.get(i) as event}{#if event.type === "bar"}<span class="bar-tick">|</span>{:else}<span class="chord-tag">{event.name}</span>{/if}{/each}</span>{/if}<span class="sentence-word" class:sung={showSung && note.start <= playhead}>{note.word}</span></span>{separatorAfter(note.word)}{/snippet}

{#if currentPhrase}
	<div class="lyrics-panel">
		<div class="lyrics-toggles">
			<label class="chords-toggle">
				<input type="checkbox" bind:checked={lyricsShowChords.value} />
				Chords
			</label>
			<label class="chords-toggle">
				<input type="checkbox" bind:checked={lyricsShowBars.value} />
				Bars
			</label>
		</div>
		{#if currentSplit.leadIn.length}
			<p class="lead-in-line">{leadInText(currentSplit.leadIn)}</p>
		{/if}
		<p class="sentence current">{#each currentWords as note, i}{@render wordSpan(note, i, currentEventsByWord, true)}{/each}</p>
		{#if nextWords.length}
			{#if nextSplit.leadIn.length}
				<p class="lead-in-line next">{leadInText(nextSplit.leadIn)}</p>
			{/if}
			<p class="sentence next">
				{#each nextWords as note, i}{@render wordSpan(note, i, nextEventsByWord, false)}{/each}
			</p>
		{/if}
	</div>
{:else}
	<p class="lyrics-empty">No lyrics to show yet.</p>
{/if}

<style>
	.lyrics-panel {
		padding: 12px 4px;
	}

	.lyrics-toggles {
		display: flex;
		gap: 12px;
	}
	.chords-toggle {
		font-size: 11px;
		color: var(--body-text-color-subdued);
		display: flex;
		align-items: center;
		gap: 3px;
		cursor: pointer;
		width: fit-content;
	}
	.chords-toggle input[type="checkbox"] {
		appearance: auto;
		accent-color: #607d8b;
		width: 12px;
		height: 12px;
	}
	.sentence {
		font-size: 20px;
		margin: 4px 0;
	}
	.word-unit {
		display: inline-flex;
		flex-direction: column;
		align-items: flex-start;
		vertical-align: bottom;
	}
	.chord-tags {
		display: flex;
		gap: 3px;
		line-height: 1;
		margin-bottom: 1px;
	}
	.chord-tag {
		font-size: 12px;
		font-weight: 700;
		color: #607d8b;
	}
	.bar-tick {
		font-size: 12px;
		font-weight: 700;
		color: var(--body-text-color-subdued);
		opacity: 0.65;
	}
	.lead-in-line {
		font-size: 13px;
		font-weight: 700;
		letter-spacing: 0.15em;
		color: var(--body-text-color-subdued);
		opacity: 0.5;
		margin: 4px 0 2px;
	}
	.lead-in-line.next {
		font-size: 11px;
		opacity: 0.3;
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