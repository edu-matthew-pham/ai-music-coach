<script lang="ts">
	import { flip } from "svelte/animate";
	import type { MixerBar, MixerNote, MixerPhrase } from "./types";
	import { lyricsShowChords, lyricsShowBars } from "./mixerPanels.svelte";

	// A narrow, vertically-scrolling column - reading ahead,
	// not navigation. PhraseList (restored as its own panel)
	// is the click-to-jump control; this panel's only job is
	// showing every line, current one in full (chords, bar
	// ticks, word-by-word rhythm), the rest plain and left to
	// wrap in whatever width it's given. Deliberately no
	// click handler here - the same phrase clickable in two
	// different places, one of them narrow and easy to miss,
	// invites a mis-tap more than it adds anything PhraseList
	// doesn't already do. Meant to sit beside NotesPanel,
	// each taking a share of the same vertical space rather
	// than Lyrics claiming a full-width row for one line.
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

	// Sung lines simply stop being rendered, rather than
	// staying in the list and being scrolled past - a real
	// karaoke prompter, not a scrolling transcript. This is
	// what makes the current line feel anchored: it's always
	// the first item in visiblePhrases, so it always lands at
	// the same spot at the top of the panel with no scrolling
	// needed to bring it there. Everything below it shifts up
	// to fill the gap (animate:flip, in the template) instead
	// of the page jumping to chase a highlight further down a
	// long list.
	const visiblePhrases = $derived(
		currentIndex >= 0 ? effectivePhrases.slice(currentIndex) : []
	);

	function wordsIn(phrase: MixerPhrase | null): MixerNote[] {
		if (!phrase) return [];
		return words.filter(
			(note) => note.start >= phrase.start && note.start < phrase.end
		);
	}

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

	// Every line gets its own chord/bar events now, not just
	// the current one - "coming up" chords are exactly the
	// kind of thing worth reading ahead for, the same reason
	// the instrument panel's own preview row exists. Kept as
	// a plain function rather than a $derived map: called
	// once per phrase inside the {#each} below via {@const},
	// so nothing computes for a phrase that isn't being
	// rendered.
	function lineFor(phrase: MixerPhrase): {
		words: MixerNote[];
		split: { leadIn: RhythmEvent[]; rest: RhythmEvent[] };
		eventsByWord: Map<number, RhythmEvent[]>;
	} {
		const phraseWords = wordsIn(phrase);
		const split = splitLeadIn(allEvents(phrase), phraseWords);
		return { words: phraseWords, split, eventsByWord: eventsByWord(phraseWords, split.rest) };
	}
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

		<div class="lyrics-list">
			{#each visiblePhrases as phrase (phrase.start)}
				{@const isCurrent = phrase === currentPhrase}
				{@const line = lineFor(phrase)}
				<div class="lyrics-line" class:current={isCurrent} animate:flip={{ duration: 220 }}>
					{#if line.split.leadIn.length}
						<p class="lead-in-line" class:plain={!isCurrent}>
							{leadInText(line.split.leadIn)}
						</p>
					{/if}
					<p class="sentence" class:current={isCurrent}>
						{#each line.words as note, i}{@render wordSpan(note, i, line.eventsByWord, isCurrent)}{/each}
					</p>
				</div>
			{/each}
		</div>
	</div>
{:else}
	<p class="lyrics-empty">No lyrics to show yet.</p>
{/if}

<style>
	.lyrics-panel {
		padding: 12px 4px;
		/* 1/4 to 1/3 of whatever row it's placed in - Lyrics
		   doesn't need more than that to be readable, and the
		   point of this design is giving that extra width
		   back to whatever it sits beside (NotesPanel) rather
		   than Lyrics claiming a full-width row for one line.
		   Actual width is set by the flex basis Index.svelte
		   gives this panel's wrapper, not here - this is the
		   internal scroll boundary once that width is decided. */
		max-height: 70vh;
		overflow-y: auto;
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
		font-size: calc(20px * var(--read-scale, 1));
		margin: 4px 0;
	}
	.sentence:not(.current) {
		/* Smaller than the current line, but full-strength
		   colour - no opacity fade. The current line already
		   stands out on its own (bigger text, plus the sung
		   words turning green as they're reached), so a faded
		   "coming up" line was just harder to read for no
		   real gain in emphasis. */
		font-size: calc(15px * var(--read-scale, 1));
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
		font-size: calc(12px * var(--read-scale, 1));
		font-weight: 700;
		color: #607d8b;
	}
	.bar-tick {
		font-size: calc(12px * var(--read-scale, 1));
		font-weight: 700;
		color: var(--body-text-color-subdued);
		opacity: 0.65;
	}
	.lead-in-line {
		font-size: calc(13px * var(--read-scale, 1));
		font-weight: 700;
		letter-spacing: 0.15em;
		color: var(--body-text-color-subdued);
		opacity: 0.5;
		margin: 4px 0 2px;
	}
	.lead-in-line.plain {
		font-size: calc(11px * var(--read-scale, 1));
	}
	.lyrics-list {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	.lyrics-line {
		/* No fixed width, no nowrap - the whole point of the
		   column being narrow is that a long line WRAPS
		   across several rows rather than being clipped or
		   scrolled past sideways. */
		margin: 0;
		overflow-wrap: break-word;
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