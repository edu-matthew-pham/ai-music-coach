<script lang="ts">
	import { engine } from "./mixerEngine.svelte";
	import { mic } from "./micPitch.svelte";
	import { noteLayers, showNextPreview, previewSideBySide, notesShowLabels, showLiveTrace, notesOctaveShift, notesShowChords } from "./mixerPanels.svelte";
	import type { MixerNote, MixerBar, MixerPhrase } from "./types";

	// A static page per phrase, hard-cut to the next rather
	// than scrolled - the way SingStar shows a line of notes:
	// still, until the line finishes, then instantly replaced.
	//
	// This panel is read-only by design, for now. Selecting a
	// stretch is still the chord strip's or phrase list's job.
	interface Props {
		notes: MixerNote[];
		timeline: MixerBar[];
		phrases: MixerPhrase[];
		playhead: number;
		narrow?: boolean;
	}

	let { notes, timeline, phrases, playhead, narrow = false }: Props = $props();

	const ROW_HEIGHT = 14;

	// A thin strip above the note boxes, present only when
	// chords are showing at all - so a page with the toggle
	// off draws exactly as it always has, byte-for-byte.
	const CHORD_ROW_HEIGHT = 16;

	// A chord's real position within its bar, in seconds -
	// the same beat_in_bar/bar.beats fraction ChordStrip
	// already uses for the same purpose, just converted to
	// this panel's own time axis instead of a CSS percentage.
	function chordTime(bar: MixerBar, chord: MixerBar["chords"][number]): number {
		return bar.start + (chord.beat_in_bar / bar.beats) * (bar.end - bar.start);
	}

	const effectivePhrases = $derived.by((): MixerPhrase[] => {
		if (phrases.length) return phrases;
		if (!notes.length) return [];
		const end = notes.reduce(
			(max, note) => Math.max(max, note.start + note.length), 0
		);
		return [{ start: 0, end, label: "1. Whole part" }];
	});

	// The switch happens once the current page's phrase has
	// finished, not the instant the next one starts - the
	// rule that matters when a bar straddles the boundary:
	// the outgoing phrase keeps it until done with it.
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

	function noteName(midi: number): string {
		const names = [
			"C", "C#", "D", "D#", "E", "F",
			"F#", "G", "G#", "A", "A#", "B"
		];
		return names[midi % 12] + Math.floor(midi / 12 - 1);
	}

	let container: HTMLElement | null = $state(null);
	let viewportWidth = $state(600);

	$effect(() => {
		if (container) viewportWidth = container.clientWidth || viewportWidth;
	});

	// Everything a page needs to draw itself: which bars,
	// which notes, the pitch range those notes need, and a
	// scale that fits this phrase's own bars to the width
	// available - shared by current and next so a preview
	// is drawn with the same rules as the active page, not
	// a simplified stand-in.
	interface Page {
		phrase: MixerPhrase;
		bars: MixerBar[];
		notes: MixerNote[];
		pitchRange: { lowest: number; highest: number };
		width: number;
		height: number;
		pxPerSecond: number;
		chordOffset: number;
	}

	function computePage(phrase: MixerPhrase | null, width: number): Page | null {
		if (!phrase) return null;

		const bars = timeline.filter(
			(bar) => bar.start < phrase.end && bar.end > phrase.start
		);

		const pageNotes = notes
			.filter(
				(note) =>
					noteLayers[note.layer] &&
					note.start >= phrase.start &&
					note.start < phrase.end
			)
			.map((note) =>
				notesOctaveShift.value === 0
					? note
					: { ...note, midi: note.midi + notesOctaveShift.value * 12 }
			);

		let lowest = 60;
		let highest = 72;

		if (pageNotes.length) {
			lowest = pageNotes[0].midi;
			highest = pageNotes[0].midi;
			for (const note of pageNotes) {
				if (note.midi < lowest) lowest = note.midi;
				if (note.midi > highest) highest = note.midi;
			}
			lowest -= 1;
			highest += 1;
		}

		const chordOffset = notesShowChords.value ? CHORD_ROW_HEIGHT : 0;
		const height = (highest - lowest + 1) * ROW_HEIGHT + chordOffset;
		const span = phrase.end - phrase.start;
		const pxPerSecond = span > 0 ? width / span : 60;

		return {
			phrase,
			bars,
			notes: pageNotes,
			pitchRange: { lowest, highest },
			width,
			height,
			pxPerSecond,
			chordOffset
		};
	}

	// Side by side genuinely cannot fit below the width
	// breakpoint - this is the container's own space running
	// out, not a preference to override, so narrow forces the
	// stacked layout regardless of what the toggle says. The
	// toggle itself stays untouched; it just has nothing to
	// do until there is room for it again.
	const sideBySide = $derived(
		showNextPreview.value && previewSideBySide.value && !narrow
	);

	const currentPage = $derived.by(() => {
		const width = sideBySide
			? (viewportWidth - 8) / 2
			: viewportWidth;
		return computePage(currentPhrase, width);
	});

	const nextPage = $derived.by(() => {
		if (!showNextPreview.value) return null;
		const width = sideBySide
			? (viewportWidth - 8) / 2
			: viewportWidth;
		return computePage(nextPhrase, width);
	});

	function y(page: Page, midi: number): number {
		return (page.pitchRange.highest - midi) * ROW_HEIGHT + page.chordOffset;
	}

	function x(page: Page, time: number): number {
		return (time - page.phrase.start) * page.pxPerSecond;
	}

	// Hz to the same vertical scale the boxes use, as a
	// continuous value - a quarter-tone sharp draws a
	// quarter of a row high, which is the whole point of a
	// raw line over quantised boxes.
	function midiFloat(freq: number): number {
		return 69 + 12 * Math.log2(freq / 440);
	}

	function traceY(page: Page, freq: number): number {
		const midi = midiFloat(freq);
		const clamped = Math.min(
			page.pitchRange.highest + 0.5,
			Math.max(page.pitchRange.lowest - 0.5, midi)
		);
		return (page.pitchRange.highest - clamped) * ROW_HEIGHT + ROW_HEIGHT / 2 + page.chordOffset;
	}

	// The sung line, cut to this page's phrase, broken into
	// separate strokes wherever the voice stopped (unvoiced
	// frames are simply absent from the trace) or the frames
	// jump in time (a loop wrapping around). One SVG path
	// per continuous stretch of singing; gaps stay gaps.
	const GAP_SECONDS = 0.15;

	function tracePaths(page: Page): string[] {
		if (!showLiveTrace.value) return [];
		const paths: string[] = [];
		let current = "";
		let lastTime = -Infinity;
		for (const frame of mic.trace) {
			if (frame.time < page.phrase.start || frame.time >= page.phrase.end) {
				continue;
			}
			const px = x(page, frame.time);
			const py = traceY(page, frame.freq);
			if (frame.time - lastTime > GAP_SECONDS) {
				if (current) paths.push(current);
				current = `M ${px.toFixed(1)} ${py.toFixed(1)}`;
			} else {
				current += ` L ${px.toFixed(1)} ${py.toFixed(1)}`;
			}
			lastTime = frame.time;
		}
		if (current) paths.push(current);
		return paths;
	}
</script>

{#snippet pageSvg(page: Page, showPlayhead: boolean, dimmed: boolean)}
	<svg
		width={page.width}
		height={page.height}
		viewBox="0 0 {page.width} {page.height}"
		class:dimmed
	>
		{#if showPlayhead && engine.loopFrom !== null && engine.loopTo !== null}
			<rect
				class="loop-region"
				x={x(page, Math.max(engine.loopFrom, page.phrase.start))}
				y="0"
				width={Math.max(
					0,
					x(page, Math.min(engine.loopTo, page.phrase.end)) -
						x(page, Math.max(engine.loopFrom, page.phrase.start))
				)}
				height={page.height}
			/>
		{/if}

		{#each page.bars as bar}
			<line
				class="bar-line"
				x1={x(page, bar.start)}
				y1="0"
				x2={x(page, bar.start)}
				y2={page.height}
			/>
		{/each}

		{#if notesShowChords.value}
			{#each page.bars as bar}
				{#each bar.chords as chord}
					<text
						class="chord-name"
						class:carried={chord.carried}
						x={x(page, chordTime(bar, chord))}
						y={CHORD_ROW_HEIGHT - 4}
					>
						{chord.name}
					</text>
				{/each}
			{/each}
		{/if}

		{#each page.notes as note}
			<g>
				<rect
					class="note-box"
					x={x(page, note.start)}
					y={y(page, note.midi) + 1}
					width={Math.max(note.length * page.pxPerSecond - 1, 2)}
					height={ROW_HEIGHT - 2}
					fill={note.colour}
					fill-opacity={note.layer === "Melody" ? 0.22 : 0.14}
					stroke={note.colour}
				/>
				{#if note.length * page.pxPerSecond > 20}
					<text
						class="note-label"
						x={x(page, note.start) + (note.length * page.pxPerSecond) / 2}
						y={y(page, note.midi) + ROW_HEIGHT / 2}
						fill={note.colour}
					>
						{noteName(note.midi)}
					</text>
				{/if}
				{#if note.word && notesShowLabels.value}
					<text
						class="note-word"
						x={x(page, note.start) + (note.length * page.pxPerSecond) / 2}
						y={y(page, note.midi) + ROW_HEIGHT + 10}
					>
						{note.word}
					</text>
				{/if}
			</g>
		{/each}

		{#if showPlayhead && showLiveTrace.value}
			{#each tracePaths(page) as segment}
				<path class="pitch-trace" d={segment} />
			{/each}
			{#if !engine.playing && mic.state === "on" && mic.livePitch !== null}
				<!-- Free-running: nothing is playing, so there is
				     no song time to draw a line against - just a
				     dot at the playhead showing the pitch being
				     sung right now, for warming up. -->
				<circle
					class="pitch-live-dot"
					data-live-midi={midiFloat(mic.livePitch).toFixed(2)}
					cx={x(page, Math.min(Math.max(playhead, page.phrase.start), page.phrase.end))}
					cy={traceY(page, mic.livePitch)}
					r="4"
				/>
			{/if}
		{/if}

		{#if showPlayhead}
			<line
				class="playhead"
				x1={x(page, playhead)}
				y1="0"
				x2={x(page, playhead)}
				y2={page.height}
			/>
		{/if}
	</svg>
{/snippet}

<div class="notes-toggles">
	{#each Object.keys(noteLayers) as name}
		<label class="layer-toggle">
			<input type="checkbox" bind:checked={noteLayers[name]} />
			{name}
		</label>
	{/each}
	<label class="layer-toggle preview-toggle">
		<input type="checkbox" bind:checked={showNextPreview.value} />
		Preview next phrase
	</label>
	{#if showNextPreview.value}
		<label class="layer-toggle" class:disabled={narrow}>
			<input
				type="checkbox"
				bind:checked={previewSideBySide.value}
				disabled={narrow}
			/>
			Side by side
		</label>
	{/if}
	<label class="layer-toggle">
		<input type="checkbox" bind:checked={notesShowLabels.value} />
		Word labels
	</label>
	<label class="layer-toggle">
		<input type="checkbox" bind:checked={notesShowChords.value} />
		Chords
	</label>
	{#if mic.state === "on" || mic.trace.length}
		<label class="layer-toggle">
			<input type="checkbox" bind:checked={showLiveTrace.value} />
			Live pitch
		</label>
	{/if}
	<div class="octave-shift" role="group" aria-label="Notes octave">
		<span class="octave-shift-label">Notes:</span>
		{#each [[-1, "Down"], [0, "As written"], [1, "Up"]] as [value, label] (value)}
			<button
				type="button"
				class="octave-shift-button"
				class:active={notesOctaveShift.value === value}
				onclick={() => (notesOctaveShift.value = value as -1 | 0 | 1)}
			>
				{label}
			</button>
		{/each}
	</div>
</div>

{#if currentPage}
	<div class="pages" class:row={sideBySide} bind:this={container}>
		<div class="notes-container">
			{@render pageSvg(currentPage, true, false)}
		</div>
		{#if nextPage}
			<div class="notes-container next-page">
				{@render pageSvg(nextPage, false, true)}
			</div>
		{/if}
	</div>
{:else}
	<p class="note-empty">No layers selected to show.</p>
{/if}

<style>
	.notes-toggles {
		display: flex;
		flex-wrap: wrap;
		gap: 12px;
		margin: 4px 0;
	}
	.layer-toggle {
		font-size: 11px;
		color: var(--body-text-color-subdued);
		display: flex;
		align-items: center;
		gap: 3px;
		cursor: pointer;
	}
	.layer-toggle input[type="checkbox"] {
		appearance: auto;
		accent-color: #607d8b;
		width: 12px;
		height: 12px;
	}
	.preview-toggle {
		margin-left: auto;
	}
	.layer-toggle.disabled {
		opacity: 0.5;
		cursor: default;
	}
	.octave-shift {
		display: flex;
		align-items: center;
		gap: 4px;
	}
	.octave-shift-label {
		font-size: 11px;
		color: var(--body-text-color-subdued);
	}
	.octave-shift-button {
		font-size: 11px;
		color: var(--body-text-color-subdued);
		background: transparent;
		border: 1px solid var(--border-color-primary);
		border-radius: 4px;
		padding: 2px 8px;
		cursor: pointer;
	}
	.octave-shift-button.active {
		background: #607d8b;
		border-color: #607d8b;
		color: white;
	}
	.pages {
		display: flex;
		flex-direction: column;
	}
	.pages.row {
		flex-direction: row;
		gap: 8px;
		align-items: flex-start;
	}
	.pages.row .notes-container {
		flex: 1;
		min-width: 0;
	}
	.notes-container {
		border: 1px solid var(--border-color-primary);
		border-radius: 4px;
		margin: 4px 0 8px;
	}
	.next-page {
		opacity: 0.55;
	}
	svg.dimmed {
		background: var(--background-fill-secondary, #fafafa);
	}
	.note-box {
		stroke-width: 1;
		rx: 2;
	}
	.note-label {
		font-size: 8px;
		text-anchor: middle;
		dominant-baseline: middle;
		pointer-events: none;
	}
	.chord-name {
		font-size: 11px;
		font-weight: 700;
		text-anchor: start;
		fill: var(--body-text-color);
		pointer-events: none;
	}
	.chord-name.carried {
		font-weight: 400;
		opacity: 0.5;
	}
	.note-word {
		font-size: 9px;
		text-anchor: middle;
		fill: var(--body-text-color-subdued, #555);
		pointer-events: none;
	}
	.loop-region {
		fill: #fff3e0;
	}
	.bar-line {
		stroke: var(--border-color-primary);
		stroke-width: 1;
		opacity: 0.5;
	}
	.playhead {
		stroke: #2e7d32;
		stroke-width: 2;
	}
	.pitch-trace {
		stroke: #d32f2f;
		stroke-width: 2;
		fill: none;
		stroke-linecap: round;
		stroke-linejoin: round;
		opacity: 0.85;
		pointer-events: none;
	}
	.pitch-live-dot {
		fill: #d32f2f;
		opacity: 0.85;
		pointer-events: none;
	}
	.note-empty {
		font-size: 13px;
		color: var(--body-text-color-subdued);
	}
</style>