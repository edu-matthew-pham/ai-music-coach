<script lang="ts">
	import { flip } from "svelte/animate";
	import { onMount } from "svelte";
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
		singing?: string | null;
		parts?: string[];
	}

	let {
		notes, timeline, phrases, playhead, mode = "paired",
		singing = null, parts = []
	}: Props = $props();

	// Whose words these are. An ordinary song has one sung
	// line, always called "Melody"; a song with several
	// tunes names them itself and says which one is being
	// sung, so the words follow that rather than a name
	// fixed here.
	const myLayer = $derived(singing || "Melody");

	const words = $derived(
		notes.filter((note) => note.layer === myLayer && note.word)
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
				return effectivePhrases;
			case "tab":
				// Columns layout: the full song, split across
				// columns elsewhere (tabColumns) - this list
				// itself needs every phrase. Single layout: a
				// phone can't see a horizontal column, and a
				// vertical list long enough to need scroll-to-
				// centre loses the same "where am I" anchor a
				// mobile player already complained about once
				// today, for the same reason - the current line
				// jumping to the middle of the screen makes it
				// easy to lose while the song keeps moving.
				// Paired's own answer (visiblePhrases: sung
				// lines simply stop rendering, current line
				// always first) already solves exactly this, so
				// single layout reuses it rather than inventing
				// a second version of the same fix.
				return tabLayout === "columns" ? effectivePhrases : visiblePhrases;
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

	// Tab's column WIDTH tracks lyricsScale - bigger text, wider
	// column, so wrapping stays reasonable. This is the width a
	// column WANTS; whether the screen has room for more than one
	// of them is a separate question, answered by tabLayout
	// below, not by shrinking the column to fit.
	const COLUMN_WIDTH_AT_1X = 320;
	const columnWidth = $derived(Math.round(COLUMN_WIDTH_AT_1X * lyricsScale.value));

	// The real responsive decision for Tab view. Tab means
	// "lyrics only, laid out like a tab reader" - and a tab
	// reader's columns only make sense when at least two of them
	// fit side by side; that's what makes reading across a wide
	// screen work. On a portrait phone, one 320px column already
	// exceeds the ~200px actually available, so "columns" there
	// is one narrow strip plus a sideways scroll to reach the
	// next - not a tab reader at all, just a worse single page.
	//
	// An earlier pass got this wrong by shrinking the column to
	// fit the phone (down to a 220px floor). That optimised the
	// size of the wrong layout: the honest answer on a phone is
	// not a smaller column, it is NO columns - one full-width
	// list with vertical scroll-follow, which is exactly what
	// windowed mode already does and is already right on a
	// phone. So Tab view now picks between two layouts from the
	// measured width, and the single-column case reuses the
	// windowed rendering path rather than a special narrow
	// column layout of its own.
	//
	// The threshold is "two columns plus their gap fit", read
	// off the same measured availableWidth the line budget
	// already uses - device and orientation fall out of that for
	// free (a phone rotated to landscape may well fit two and
	// gets columns; back to portrait it drops to one). Before
	// the first measurement lands, columns is assumed - a phone
	// then re-flows to single once measured, a desktop stays
	// put; either way nothing is hidden during that first paint.
	// Must match .lyrics-columns' `gap` in the CSS below.
	const COLUMN_GAP_PX = 32;
	const tabLayout = $derived.by((): "columns" | "single" => {
		if (mode !== "tab") return "single";
		if (availableWidth <= 0) return "columns";
		return availableWidth >= columnWidth * 2 + COLUMN_GAP_PX ? "columns" : "single";
	});

	// Column HEIGHT - how many lines fit before a new column
	// starts - is now MEASURED, not estimated. Two earlier
	// versions of this were both guesses and both wrong on real
	// screens: a fixed "10 lines at 1x", then "75% of the browser
	// window at 42px a line". The second one still put too many
	// lines in a column on an ordinary monitor, for two reasons
	// worth keeping on record:
	//
	// 1. The panel is not at the top of the window. Gradio's nav
	//    bar, the page heading, the Song section, the transport
	//    row and the seek bar all sit above it, so "75% of the
	//    window" is far more room than the panel actually has.
	//    Now measured: the real distance from where the columns
	//    box starts on screen to the bottom of the viewport.
	//    That's the space the panel is GIVEN, not the space it
	//    takes up - measuring its own height would be circular,
	//    since its height is set by how many lines were put in it.
	//
	// 2. 42px a line was worked out from the CSS, not rendered.
	//    Gradio's font stack, and the chord-tag row that sits
	//    above the words when Chords is on, both make a real line
	//    taller. Now measured: the rendered height of the first
	//    actual line, re-read whenever the text scale changes.
	//
	// Both measurements are taken after render (onMount, and
	// after each resize/scale change) so they see the real
	// layout. Until the first measurement lands, a conservative
	// fallback keeps the first paint sane rather than blank.
	//
	// The safety net is unchanged and does not depend on either
	// measurement being exact: scroll-follow (below) always
	// brings the current line's column into view, so a phrase
	// that wraps across several lines can still make one column
	// run a little long - slightly uneven columns, never a lost
	// or hidden current line.
	const FALLBACK_LINES = 8;
	const BOTTOM_MARGIN_PX = 24;
	// Must match .lyrics-column's `gap` in the CSS below.
	const COLUMN_LINE_GAP_PX = 10;

	let panelElement = $state<HTMLElement | null>(null);
	let columnsElement = $state<HTMLElement | null>(null);
	let availableHeight = $state(0);
	let availableWidth = $state(0);
	let lineHeight = $state(0);
	// The reserve: how much taller the CURRENT line is than a
	// typical one, so it can be subtracted from the budget
	// before dividing. See measure()'s own comment for why this
	// exists - the original design's intent was a generous
	// budget that leaves headroom, not one that exactly fills
	// the space and treats overflow as routine.
	let currentLineExtra = $state(0);

	function measure(): void {
		if (typeof window === "undefined") return;
		// Width comes from the panel itself, which exists in BOTH
		// of Tab's layouts. It must not come from .lyrics-columns:
		// that element is only rendered in the columns layout, so
		// once a phone had dropped to single there would be nothing
		// left to measure, and rotating to landscape could never
		// find its way back to columns. The panel is the stable
		// thing across the switch, so it is what gets measured.
		if (panelElement) {
			availableWidth = panelElement.getBoundingClientRect().width;
		}
		// Height budget for a column: how tall a column can be and
		// still fit on screen without vertical scrolling. Read off
		// the columns box when it exists; in single layout there is
		// no line budget to compute, so it simply isn't needed.
		//
		// Real bug, seen in production on a desktop monitor after
		// this shipped: the first version computed this as
		// `window.innerHeight - columnsBox.getBoundingClientRect().top`,
		// which is "how much of the VIEWPORT is below the box RIGHT
		// NOW" - a number that changes with every scroll. measure()
		// runs on mount and on resize/scale change, but not on
		// scroll, and the mixer is far down the page when it mounts
		// (the Song section, headings and Gradio's own chrome sit
		// above it), so on mount `top` was large, the result tiny,
		// clamped to the 3-line floor - and nothing ever
		// re-measured once main.py's Playback link scrolled the
		// mixer up into view half a second later. The panel looked
		// right for an instant, then collapsed to three-line
		// columns and stayed there. Measuring viewport-relative
		// position and never re-measuring on scroll was the
		// contradiction; the fix is to make the number not depend
		// on scroll position at all.
		//
		// So: the box's offset from the top of the MIXER (a scroll-
		// independent, document-relative distance - the mixer's own
		// header rows, seek bar and phrase strip are what sit
		// above the columns, and they scroll WITH the mixer, so
		// their height above the box is fixed) is what's above the
		// columns once the mixer is scrolled to the top of the
		// screen, which is exactly the state the Playback link puts
		// it in and the state a person reading Tab view is in.
		// innerHeight minus that is the room a column has. The
		// nearest positioned ancestor is .mixer (position: relative
		// in Index.svelte), so offsetTop is relative to it - not to
		// the page, and not to the viewport.
		if (columnsElement) {
			const mixerRoot = columnsElement.closest(".mixer") as HTMLElement | null;
			const boxTopInMixer = mixerRoot
				? columnsElement.getBoundingClientRect().top - mixerRoot.getBoundingClientRect().top
				: columnsElement.offsetTop;
			availableHeight = Math.max(0, window.innerHeight - boxTopInMixer - BOTTOM_MARGIN_PX);
		}
		if (columnsElement) {
			// The yardstick is a TYPICAL line, deliberately not the
			// first one. Real bug, seen in production right after
			// the scroll fix above landed: the first line of the
			// first column is the CURRENT line at the start of a
			// song, and the current line is drawn bigger (its own
			// font-size, see .sentence.current) and here wrapped
			// onto two rows - measured 117px against 52px for every
			// other line. Dividing the height budget by that
			// inflated number gave 5 lines a column instead of 10.
			// The scroll bug had been masking this one: fixing it
			// just let this second wrong number through, which is
			// exactly why the columns still looked short.
			// So: the first line that is NOT current. There is
			// always at least one unless the song is a single
			// phrase, in which case fall back to whatever line
			// exists - a one-line song does not need a line budget
			// anyway.
			const typical =
				columnsElement.querySelector<HTMLElement>(".lyrics-line:not(.current)") ??
				columnsElement.querySelector<HTMLElement>(".lyrics-line");
			if (typical) {
				// offsetHeight is the line's own box; the column's
				// flex gap (10px, .lyrics-column below) sits between
				// lines and is not part of any one line's box, so it
				// is added here to get the true per-line stride.
				lineHeight = typical.offsetHeight + COLUMN_LINE_GAP_PX;
			}
			// The reserve. The current line is drawn bigger (its
			// own font-size, .sentence.current) and often wraps
			// where a typical line doesn't - measured 117px against
			// 52px, a 65px difference on a real song. The current
			// line always exists SOMEWHERE, and moves between
			// columns as the song plays, so every column will
			// eventually hold it - this is not a rare case to
			// shrug off, it is the routine one. linesPerColumn
			// reserves this delta so the column that currently
			// holds it still fits, restoring the original design's
			// intent (a generous budget that leaves headroom) that
			// dividing by a bare typical height had quietly lost.
			// A phrase in DIFFERENT wrapping shoes than the one
			// caught here (e.g. two lines both wrapping unusually)
			// is what the documented fallback above still covers -
			// this reserve narrows that gap, it does not claim to
			// close it completely.
			const current = columnsElement.querySelector<HTMLElement>(".lyrics-line.current");
			currentLineExtra = current && typical
				? Math.max(0, current.offsetHeight - typical.offsetHeight)
				: 0;
		}
	}

	onMount(() => {
		measure();
		// Debounced: some mobile browsers fire resize repeatedly
		// while their address bar shows/hides during ordinary
		// scrolling, not just on a real rotation or window resize.
		// Reacting to every one would recompute which phrases
		// belong to which column mid-scroll for no reason.
		let timeout: ReturnType<typeof setTimeout> | null = null;
		function handleResize(): void {
			if (timeout !== null) clearTimeout(timeout);
			timeout = setTimeout(measure, 150);
		}
		window.addEventListener("resize", handleResize);
		window.addEventListener("orientationchange", handleResize);
		return () => {
			if (timeout !== null) clearTimeout(timeout);
			window.removeEventListener("resize", handleResize);
			window.removeEventListener("orientationchange", handleResize);
		};
	});

	// Re-measure the line height whenever the scale changes -
	// the font, and so the rendered line, changes with it. The
	// scale is read here only so this effect depends on it;
	// measure() itself reads the DOM. Runs after the DOM has
	// updated for the new scale, which is what makes the
	// measurement land on the new size rather than the old one.
	$effect(() => {
		void lyricsScale.value;
		void mode;
		measure();
	});

	const linesPerColumn = $derived(
		availableHeight > 0 && lineHeight > 0
			? Math.max(3, Math.floor((availableHeight - currentLineExtra) / lineHeight))
			: FALLBACK_LINES
	);

	const tabColumns = $derived.by((): MixerPhrase[][] => {
		if (mode !== "tab" || tabLayout !== "columns") return [];
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
		// windowed scrolls to keep the current line centred -
		// right there, since it renders the WHOLE song and the
		// current line can be anywhere in a long scroll region.
		// Tab's single layout does NOT join this any more: it
		// now renders through paired's own list (visiblePhrases,
		// see displayPhrases above), where the current line is
		// always first by construction - sung lines simply stop
		// rendering rather than needing to be scrolled past. No
		// scroll effect is needed for that, the same as paired
		// itself has never needed one; adding scrollIntoView on
		// top would fight the drop-off animation for no reason.
		if (mode === "windowed" && currentIndex >= 0 && phraseElements[currentIndex]) {
			phraseElements[currentIndex].scrollIntoView({
				behavior: "smooth",
				block: "center"
			});
		}
	});

	$effect(() => {
		if (mode === "tab" && tabLayout === "columns" && currentIndex >= 0) {
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
		class:tab-single={mode === "tab" && tabLayout === "single"}
		class:mode-singstar={mode === "singstar"}
		style="--lyrics-scale: {lyricsScale.value}"
		bind:this={panelElement}
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

		{#if mode === "tab" && tabLayout === "columns"}
			<!-- bind:this on the columns box gives measure() the
			     box's position for the height budget, and a root
			     to query a typical rendered line from - see the
			     line-height measurement in measure() for why it
			     deliberately does NOT read the first line. -->
			<div class="lyrics-columns" bind:this={columnsElement}>
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
			<!-- Tab's single-column layout no longer shares
			     windowed's rendering (see displayPhrases in the
			     script - it renders through paired's own
			     visiblePhrases now, lines dropping off the top
			     rather than a long scrolled list), so it no
			     longer piggybacks on windowed's class here
			     either. No max-width cap of its own for the same
			     reason paired has none: the widths that reach
			     this layout (see tabLayout) are already well
			     under what a cap would ever bind on. -->
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
		/* Tab's columns layout owns its own scroll region on
		   .lyrics-columns instead (a horizontally-scrolling row
		   - see below), so the vertical max-height/overflow-y
		   this panel normally carries has to be cancelled here
		   or the two would fight each other. */
		max-height: none;
		overflow: visible;
	}
	.lyrics-panel.mode-tab.tab-single {
		/* Tab's single-column layout now renders through
		   paired's own logic (visiblePhrases, drop-off from the
		   top - see displayPhrases in the script), not
		   windowed's scroll-to-centre. So it gets paired's own
		   scroll treatment back too: the base 70vh/auto above,
		   not windowed's 85vh. There is nothing tab-specific
		   left to say here other than undoing mode-tab's own
		   overflow:visible/max-height:none (needed for the
		   COLUMNS layout's horizontal scroll, wrong for this
		   one) - this rule exists only to cancel that, not to
		   add anything of its own. */
		max-height: 70vh;
		overflow-y: auto;
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
		   No height and no min-height on purpose. The line
		   count per column is now measured from the real space
		   below this box (see measure() in the script), so the
		   box's natural height IS the intended height - a CSS
		   floor here would only re-add empty space under short
		   columns, and a fixed height plus overflow-y:hidden
		   would CLIP a column that runs long from a wrapped
		   phrase. Left to grow: a long column pushes the box
		   taller instead of losing content off the bottom.
		   overflow-x is the only scroll axis this needs -
		   overflow-y stays at its default (visible), which is
		   what lets a tall column push the box's real height
		   rather than being boxed in by one.
		   width: 1px; min-width: 100% is a deliberate pair, not
		   a typo - the real bug, found and fixed by measuring
		   the real running app at 360px, not by inspection.
		   Every .lyrics-column below is flex: 0 0 auto with a
		   hard pixel width (non-shrinking, by design - a column
		   should never squash its own text). With three such
		   columns and no width rule here at all, this box (and
		   every block ancestor above it up to .lyrics-cell in
		   Index.svelte) sized itself to fit all of them - 1032px
		   measured on a 360px screen, nearly 3x over, which
		   overflow-x: auto never got a chance to catch because
		   nothing was ever small enough to need scrolling in the
		   first place. min-width: 100% forces this box to take
		   its real percentage share of whatever space its
		   ancestor actually allocated, REGARDLESS of its
		   children's content size, overriding the tiny width: 1px
		   (min-width always wins over a smaller conflicting
		   width) - only once the box has that real, bounded
		   width does overflow-x: auto have anything to clip
		   against and actually engage. Confirmed by injecting
		   this exact rule into the real running app and
		   measuring .lyrics-cell's rendered width drop from
		   1032px to 206px, not assumed from reasoning about the
		   box model alone - an earlier attempt (width: 100% on
		   .lyrics-panel, one level up) measurably changed
		   nothing, because .lyrics-panel's own containing block
		   had no definite width for a percentage to resolve
		   against either; forcing it here, on the innermost box
		   that actually needs to be bounded, is what works. */
		display: flex;
		align-items: flex-start;
		gap: 32px;
		width: 1px;
		min-width: 100%;
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