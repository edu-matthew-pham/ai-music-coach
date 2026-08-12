<script lang="ts">
	import { engine } from "./mixerEngine.svelte";
	import { noteLayers, showNextPreview, previewSideBySide } from "./mixerPanels.svelte";
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
	}

	let { notes, timeline, phrases, playhead }: Props = $props();

	const ROW_HEIGHT = 14;

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
	}

	function computePage(phrase: MixerPhrase | null, width: number): Page | null {
		if (!phrase) return null;

		const bars = timeline.filter(
			(bar) => bar.start < phrase.end && bar.end > phrase.start
		);

		const pageNotes = notes.filter(
			(note) =>
				noteLayers[note.layer] &&
				note.start >= phrase.start &&
				note.start < phrase.end
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

		const height = (highest - lowest + 1) * ROW_HEIGHT;
		const span = phrase.end - phrase.start;
		const pxPerSecond = span > 0 ? width / span : 60;

		return {
			phrase,
			bars,
			notes: pageNotes,
			pitchRange: { lowest, highest },
			width,
			height,
			pxPerSecond
		};
	}

	const currentPage = $derived.by(() => {
		const width = showNextPreview.value && previewSideBySide.value
			? (viewportWidth - 8) / 2
			: viewportWidth;
		return computePage(currentPhrase, width);
	});

	const nextPage = $derived.by(() => {
		if (!showNextPreview.value) return null;
		const width = previewSideBySide.value
			? (viewportWidth - 8) / 2
			: viewportWidth;
		return computePage(nextPhrase, width);
	});

	function y(page: Page, midi: number): number {
		return (page.pitchRange.highest - midi) * ROW_HEIGHT;
	}

	function x(page: Page, time: number): number {
		return (time - page.phrase.start) * page.pxPerSecond;
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
				{#if note.word}
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
		<label class="layer-toggle">
			<input type="checkbox" bind:checked={previewSideBySide.value} />
			Side by side
		</label>
	{/if}
</div>

{#if currentPage}
	<div class="pages" class:row={showNextPreview.value && previewSideBySide.value} bind:this={container}>
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
	.note-empty {
		font-size: 13px;
		color: var(--body-text-color-subdued);
	}
</style>