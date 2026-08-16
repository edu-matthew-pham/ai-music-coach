<script lang="ts">
	import { flip } from "svelte/animate";
	import type { MixerBar, MixerNote, MixerPhrase } from "./types";
	import {
		lyricsShowChords,
		lyricsShowBars,
		lyricsScale,
		setLyricsScale,
		PANEL_SCALE_MIN,
		PANEL_SCALE_MAX,
		PANEL_SCALE_STEP
	} from "./mixerPanels.svelte";

	// Four modes, one prop, decided once by Index.svelte from
	// panels.notes + viewPreset - this component no longer
	// infers anything from a combination of booleans. Two
	// booleans (solo/tabView) meant four real states lived as
	// overlapping CSS classes and scattered conditionals, and
	// every fix to one mode kept disturbing another.
	//
	// paired    - beside NotesPanel, narrow. Current line plus
	//             everything after; sung lines drop off the
	//             top as playback advances (a real karaoke
	//             prompter, not a scrolling transcript).
	// windowed  - Notes off, in an ordinary window. Full song,
	//             single column, full width, vertical scroll-
	//             follow keeps the current line centred.
	// tab       - the Tab view preset. Full song, laid out in
	//             real (JS-partitioned, not CSS multi-column)
	//             columns like a tab reader on a TV or wide
	//             screen, horizontal scroll-follow.
	// singstar  - the SingStar preset, stacked below Notes.
	//             Current line plus up to three ahead, capped
	//             (SINGSTAR_LOOKAHEAD below) and centred - a
	//             glance-down reference for playing along, not
	//             a document to read ahead in, but with a
	//             little more runway than "just the next line"
	//             for someone who wants to see a phrase or two
	//             of a chord change coming.
	interface Props {
		notes: MixerNote[];
		timeline: MixerBar[];
		phrases: MixerPhrase[];
		playhead: number;
		mode?: "paired" | "windowed" | "tab" | "singstar";
	}

	let { notes, timeline, phrases, playhead, mode = "paired" }: Props = $props();

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

	// paired's own list: sung lines simply stop being
	// rendered, rather than staying in the list and being
	// scrolled past. The current line is always first, by
	// construction, which is what makes it feel anchored with
	// no scrolling needed - animate:flip (in the template)
	// closes the gap when a line drops off the top.
	const visiblePhrases = $derived(
		currentIndex >= 0 ? effectivePhrases.slice(currentIndex) : []
	);

	// The flat list every non-tab mode renders through. tab
	// doesn't use this - it partitions effectivePhrases into
	// columns instead (see tabColumns below) - but computing
	// it uniformly here keeps the mode switch in one place.
	const displayPhrases = $derived.by((): MixerPhrase[] => {
		switch (mode) {
			case "windowed":
			case "tab":
				return effectivePhrases;
			case "singstar":
				// Current plus up to SINGSTAR_LOOKAHEAD ahead - a
				// fixed window, not "current plus however many
				// happen to fit". slice past the end of the array
				// just yields a shorter array, so the last phrase
				// of a song correctly shows fewer lines, not an
				// error.
				return currentIndex >= 0
					? effectivePhrases.slice(currentIndex, currentIndex + 1 + SINGSTAR_LOOKAHEAD)
					: [];
			case "paired":
			default:
				return visiblePhrases;
		}
	});

	// SingStar's own lookahead - current line plus this many
	// after it, at most. "Up to" because displayPhrases above
	// slices past the array's end harmlessly (a shorter array,
	// not an error), so the last few phrases of a song
	// correctly taper down to fewer lines rather than needing
	// special-casing here.
	const SINGSTAR_LOOKAHEAD = 3;

	// Tab's column widths and line budget both track lyricsScale,
	// reactively - bigger text needs wider columns (or a line
	// wraps more) and fits fewer lines before a column would
	// run long, so both numbers move together whenever the
	// scale buttons are pressed, with no separate wiring.
	//
	// This is a fixed LINE COUNT per column, not a measured
	// height - deliberately generous (10 lines at 1x, most
	// real phrases are one line) rather than tightly packed.
	// A column is allowed to run past the nominal height if a
	// phrase happens to wrap across several lines; the layout
	// below is built so that's genuinely harmless (see
	// .lyrics-columns' min-height, not height, further down) -
	// the column just ends up a little taller than its
	// neighbours, not clipped and not forcing a reflow.
	const LINES_PER_COLUMN_AT_1X = 10;
	const COLUMN_WIDTH_AT_1X = 320;

	const linesPerColumn = $derived(
		Math.max(3, Math.round(LINES_PER_COLUMN_AT_1X / lyricsScale.value))
	);
	const columnWidth = $derived(Math.round(COLUMN_WIDTH_AT_1X * lyricsScale.value));

	const tabColumns = $derived.by((): MixerPhrase[][] => {
		if (mode !== "tab") return [];
		const columns: MixerPhrase[][] = [];
		for (let i = 0; i < effectivePhrases.length; i += linesPerColumn) {
			columns.push(effectivePhrases.slice(i, i + linesPerColumn));
		}
		return columns;
	});

	// Scroll-follow, one behaviour per mode - paired and
	// singstar need none (their current line is always first,
	// or always the only bold one in a two-line window, by
	// construction); windowed scrolls the current LINE toward
	// the panel's vertical centre; tab scrolls the current
	// line's COLUMN toward the horizontal centre, since within
	// a column nothing needs to move (a column is never taller
	// than what fits comfortably, by the generous line budget
	// above) - only which column is in view changes.
	let phraseElements: Record<number, HTMLElement> = {};
	let columnElements: Record<number, HTMLElement> = {};

	$effect(() => {
		if (mode === "windowed" && currentIndex >= 0 && phraseElements[currentIndex]) {
			phraseElements[currentIndex].scrollIntoView({
				behavior: "smooth",
				block: "center"
			});
		}
	});

	$effect(() => {
		if (mode === "tab" && currentIndex >= 0) {
			const columnIndex = Math.floor(currentIndex / linesPerColumn);
			// block: "nearest" rather than "center" - the panel
			// no longer caps its own height in tab mode (a
			// column is free to run long), so this is scrolling
			// the actual page vertically too if it centres;
			// "nearest" only moves the page if the column has
			// genuinely scrolled out of view, not on every line.
			columnElements[columnIndex]?.scrollIntoView({
				behavior: "smooth",
				inline: "center",
				block: "nearest"
			});
		}
	});

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

{#snippet lyricsLine(phrase: MixerPhrase)}
	{@const isCurrent = phrase === currentPhrase}
	{@const line = lineFor(phrase)}
	<div class="lyrics-line" class:current={isCurrent}>
		{#if line.split.leadIn.length}
			<p class="lead-in-line" class:plain={!isCurrent}>
				{leadInText(line.split.leadIn)}
			</p>
		{/if}
		<p class="sentence" class:current={isCurrent}>
			{#each line.words as note, i}{@render wordSpan(note, i, line.eventsByWord, isCurrent)}{/each}
		</p>
	</div>
{/snippet}

{#if currentPhrase}
	<div
		class="lyrics-panel"
		class:mode-windowed={mode === "windowed"}
		class:mode-tab={mode === "tab"}
		class:mode-singstar={mode === "singstar"}
		style="--lyrics-scale: {lyricsScale.value}"
	>
		<div class="lyrics-toggles">
			<label class="chords-toggle">
				<input type="checkbox" bind:checked={lyricsShowChords.value} />
				Chords
			</label>
			<label class="chords-toggle">
				<input type="checkbox" bind:checked={lyricsShowBars.value} />
				Bars
			</label>
			<div class="panel-scale-control" role="group" aria-label="Lyrics text size">
				<button
					type="button"
					class="panel-scale-button"
					disabled={lyricsScale.value <= PANEL_SCALE_MIN}
					aria-label="Smaller lyrics text"
					onclick={() => setLyricsScale(lyricsScale.value - PANEL_SCALE_STEP)}
				>
					&minus;
				</button>
				<button
					type="button"
					class="panel-scale-value"
					disabled={lyricsScale.value === 1}
					aria-label="Reset lyrics text size to 100%"
					onclick={() => setLyricsScale(1)}
				>
					{Math.round(lyricsScale.value * 100)}%
				</button>
				<button
					type="button"
					class="panel-scale-button"
					disabled={lyricsScale.value >= PANEL_SCALE_MAX}
					aria-label="Bigger lyrics text"
					onclick={() => setLyricsScale(lyricsScale.value + PANEL_SCALE_STEP)}
				>
					&plus;
				</button>
			</div>
		</div>

		{#if mode === "tab"}
			<div class="lyrics-columns">
				{#each tabColumns as column, colIndex}
					<div
						class="lyrics-column"
						style="width: {columnWidth}px"
						bind:this={columnElements[colIndex]}
					>
						{#each column as phrase (phrase.start)}
							{@render lyricsLine(phrase)}
						{/each}
					</div>
				{/each}
			</div>
		{:else}
			<div class="lyrics-list" class:mode-windowed={mode === "windowed"}>
				{#each displayPhrases as phrase, index (phrase.start)}
					<div bind:this={phraseElements[index]} animate:flip={{ duration: 220 }}>
						{@render lyricsLine(phrase)}
					</div>
				{/each}
			</div>
		{/if}
	</div>
{:else}
	<p class="lyrics-empty">No lyrics to show yet.</p>
{/if}

<style>
	.lyrics-panel {
		padding: 12px 4px;
		/* Base (paired): 1/4 to 1/3 of whatever row it's placed
		   in - Lyrics doesn't need more than that to be
		   readable, and the point of this design is giving
		   that extra width back to whatever it sits beside
		   (NotesPanel) rather than Lyrics claiming a full-
		   width row for one line. Actual width is set by the
		   flex basis Index.svelte gives this panel's wrapper,
		   not here - this is the internal scroll boundary once
		   that width is decided. */
		max-height: 70vh;
		overflow-y: auto;
	}
	.lyrics-panel.mode-windowed {
		/* Alone in an ordinary window, full width - more room
		   to scroll before the internal boundary matters. */
		max-height: 85vh;
	}
	.lyrics-panel.mode-tab {
		/* Tab owns its own scroll region on .lyrics-columns
		   instead (a min-height, horizontally-scrolling row -
		   see below), so the vertical max-height/overflow-y
		   this panel normally carries has to be cancelled here
		   or the two would fight each other. */
		max-height: none;
		overflow: visible;
	}
	.lyrics-panel.mode-singstar .lyrics-toggles {
		/* Centred to match the centred text below it - a left-
		   aligned toolbar over centred lines looked lopsided,
		   and singstar's whole point is being glanced at from
		   a distance, where that asymmetry is exactly the kind
		   of thing that reads as "off" without being easy to
		   say why. */
		justify-content: center;
	}
	.lyrics-panel.mode-singstar .sentence,
	.lyrics-panel.mode-singstar .lead-in-line {
		text-align: center;
	}

	.lyrics-toggles {
		display: flex;
		align-items: center;
		gap: 12px;
	}
	.panel-scale-control {
		display: flex;
		align-items: stretch;
		gap: 2px;
		margin-left: auto;
	}
	.panel-scale-button {
		font: inherit;
		font-size: 12px;
		width: 22px;
		padding: 0;
		border: 1px solid var(--border-color-primary);
		border-radius: 5px;
		background: var(--background-fill-primary);
		color: var(--body-text-color-subdued);
		cursor: pointer;
	}
	.panel-scale-button:hover:not(:disabled) {
		background: var(--background-fill-secondary, #f5f5f5);
	}
	.panel-scale-button:disabled {
		opacity: 0.4;
		cursor: default;
	}
	.panel-scale-value {
		font: inherit;
		width: 38px;
		padding: 0 4px;
		border: 1px solid var(--border-color-primary);
		border-radius: 5px;
		background: var(--background-fill-primary);
		font-size: 10px;
		color: var(--body-text-color-subdued);
		text-align: center;
		cursor: pointer;
	}
	.panel-scale-value:hover:not(:disabled) {
		background: var(--background-fill-secondary, #f5f5f5);
	}
	.panel-scale-value:disabled {
		cursor: default;
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
		font-size: calc(20px * var(--lyrics-scale, 1));
		margin: 4px 0;
	}
	.sentence:not(.current) {
		/* Smaller than the current line, but full-strength
		   colour - no opacity fade. The current line already
		   stands out on its own (bigger text, plus the sung
		   words turning green as they're reached), so a faded
		   "coming up" line was just harder to read for no
		   real gain in emphasis. */
		font-size: calc(15px * var(--lyrics-scale, 1));
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
		font-size: calc(12px * var(--lyrics-scale, 1));
		font-weight: 700;
		color: #607d8b;
	}
	.bar-tick {
		font-size: calc(12px * var(--lyrics-scale, 1));
		font-weight: 700;
		color: var(--body-text-color-subdued);
		opacity: 0.65;
	}
	.lead-in-line {
		font-size: calc(13px * var(--lyrics-scale, 1));
		font-weight: 700;
		letter-spacing: 0.15em;
		color: var(--body-text-color-subdued);
		opacity: 0.5;
		margin: 4px 0 2px;
	}
	.lead-in-line.plain {
		font-size: calc(11px * var(--lyrics-scale, 1));
	}
	.lyrics-list {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	.lyrics-list.mode-windowed {
		/* Full-width single column. Longer lines wrap across
		   more of the row instead of staying in a narrow
		   strip - already a real improvement over the paired
		   layout without needing columns, which only earn
		   their keep at tab's real width. */
		max-width: 900px;
	}
	.lyrics-columns {
		/* Real columns, built in the script (tabColumns) rather
		   than CSS column-*: scrollIntoView doesn't reliably
		   target a position inside a CSS multicol box, which
		   is what made the horizontal follow effect flaky in
		   an earlier version of this. Each .lyrics-column below
		   is an ordinary flex child - a real element that can
		   be measured and scrolled to.
		   min-height, not height: a fixed height plus
		   overflow-y:hidden would CLIP a column that runs
		   longer than its generous line budget (an occasional
		   wrapped phrase). min-height only sets a floor - the
		   row's actual height still grows to fit its tallest
		   column, so a long column pushes the box taller
		   instead of losing content off the bottom. The trade
		   is a small amount of empty space below shorter
		   columns most of the time, in exchange for never
		   silently cutting lyrics off - the right side of that
		   trade for a panel showing the whole song.
		   overflow-x is the only scroll axis this needs -
		   overflow-y is left at its default (visible), which
		   is what lets a tall column push the box's real
		   height rather than being boxed in by one. */
		display: flex;
		align-items: flex-start;
		gap: 32px;
		min-height: 75vh;
		overflow-x: auto;
		padding-bottom: 8px;
	}
	.lyrics-column {
		display: flex;
		flex-direction: column;
		gap: 10px;
		flex: 0 0 auto;
	}
	.lyrics-line {
		/* No fixed width, no nowrap - a long line WRAPS across
		   several rows rather than being clipped or scrolled
		   past sideways. */
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