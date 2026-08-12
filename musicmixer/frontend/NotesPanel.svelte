<script lang="ts">
	import { engine } from "./mixerEngine.svelte";
	import { noteLayers } from "./mixerPanels.svelte";
	import type { MixerNote, MixerBar, MixerPhrase } from "./types";

	// A static page per phrase, hard-cut to the next rather
	// than scrolled - the way SingStar shows a line of notes:
	// still, until the line finishes, then instantly replaced.
	// Scrolling made you track two moving things at once (the
	// playhead and the background sliding under it), which
	// was the actual readability problem; a still page removes
	// one of them entirely.
	//
	// This panel is read-only by design, for now. Selecting a
	// stretch is still the chord strip's job.
	interface Props {
		notes: MixerNote[];
		timeline: MixerBar[];
		phrases: MixerPhrase[];
		playhead: number;
	}

	let { notes, timeline, phrases, playhead }: Props = $props();

	const ROW_HEIGHT = 14;

	// A song with no lyric line breaks has no phrases to page
	// by - rather than keep two different windowing schemes,
	// the whole song becomes one page in that case, spanning
	// from the first note to the last.
	const effectivePhrases = $derived.by((): MixerPhrase[] => {
		if (phrases.length) return phrases;
		if (!notes.length) return [];
		const end = notes.reduce(
			(max, note) => Math.max(max, note.start + note.length), 0
		);
		return [{ start: 0, end, label: "1. Whole part" }];
	});

	// The switch happens once the current page's phrase has
	// finished, not the instant the next one starts - the two
	// are the same instant for contiguous phrases, but this is
	// the rule that matters when a bar straddles the boundary:
	// the outgoing phrase keeps that bar until it is done with
	// it, rather than the incoming phrase claiming it early and
	// cutting the still-sounding line short.
	const currentPhrase = $derived.by((): MixerPhrase | null => {
		if (!effectivePhrases.length) return null;
		const found = effectivePhrases.find((phrase) => playhead < phrase.end);
		return found ?? effectivePhrases[effectivePhrases.length - 1];
	});

	// Bars overlapping this phrase at all - a bar the phrase
	// only partly covers still belongs to this page, since the
	// alternative is a page whose last bar is silently missing
	// the tail end of what is actually sounding.
	const pageBars = $derived.by(() => {
		if (!currentPhrase) return [];
		return timeline.filter(
			(bar) => bar.start < currentPhrase!.end && bar.end > currentPhrase!.start
		);
	});

	const pageNotes = $derived.by(() => {
		if (!currentPhrase) return [];
		return notes.filter(
			(note) =>
				noteLayers[note.layer] &&
				note.start >= currentPhrase!.start &&
				note.start < currentPhrase!.end
		);
	});

	const pitchRange = $derived.by(() => {
		if (!pageNotes.length) return { lowest: 60, highest: 72 };
		let lowest = pageNotes[0].midi;
		let highest = pageNotes[0].midi;
		for (const note of pageNotes) {
			if (note.midi < lowest) lowest = note.midi;
			if (note.midi > highest) highest = note.midi;
		}
		return { lowest: lowest - 1, highest: highest + 1 };
	});

	const height = $derived(
		(pitchRange.highest - pitchRange.lowest + 1) * ROW_HEIGHT
	);

	function y(midi: number): number {
		return (pitchRange.highest - midi) * ROW_HEIGHT;
	}

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

	// Equal-width bars, filling the page exactly. Constant
	// tempo is assumed - a real time-signature change mid-song
	// isn't modelled here - so equal width and equal time are
	// the same thing, and the scale is just the page's own bar
	// count substituted in where a fixed number used to be.
	const pxPerSecond = $derived.by(() => {
		if (!currentPhrase) return 60;
		const span = currentPhrase.end - currentPhrase.start;
		if (span <= 0) return 60;
		return viewportWidth / span;
	});

	function x(time: number): number {
		if (!currentPhrase) return 0;
		return (time - currentPhrase.start) * pxPerSecond;
	}
</script>

<div class="notes-toggles">
	{#each Object.keys(noteLayers) as name}
		<label class="layer-toggle">
			<input type="checkbox" bind:checked={noteLayers[name]} />
			{name}
		</label>
	{/each}
</div>

{#if pageNotes.length && currentPhrase}
	<div class="notes-container" bind:this={container}>
		<svg width={viewportWidth} {height} viewBox="0 0 {viewportWidth} {height}">
			{#if engine.loopFrom !== null && engine.loopTo !== null}
				<rect
					class="loop-region"
					x={x(Math.max(engine.loopFrom, currentPhrase.start))}
					y="0"
					width={Math.max(
						0,
						x(Math.min(engine.loopTo, currentPhrase.end)) -
							x(Math.max(engine.loopFrom, currentPhrase.start))
					)}
					{height}
				/>
			{/if}

			{#each pageBars as bar}
				<line
					class="bar-line"
					x1={x(bar.start)}
					y1="0"
					x2={x(bar.start)}
					y2={height}
				/>
			{/each}

			{#each pageNotes as note}
				<g>
					<rect
						class="note-box"
						x={x(note.start)}
						y={y(note.midi) + 1}
						width={Math.max(note.length * pxPerSecond - 1, 2)}
						height={ROW_HEIGHT - 2}
						fill={note.colour}
						fill-opacity={note.layer === "Melody" ? 0.22 : 0.14}
						stroke={note.colour}
					/>
					{#if note.length * pxPerSecond > 20}
						<text
							class="note-label"
							x={x(note.start) + (note.length * pxPerSecond) / 2}
							y={y(note.midi) + ROW_HEIGHT / 2}
							fill={note.colour}
						>
							{noteName(note.midi)}
						</text>
					{/if}
					{#if note.word}
						<text
							class="note-word"
							x={x(note.start) + (note.length * pxPerSecond) / 2}
							y={y(note.midi) + ROW_HEIGHT + 10}
						>
							{note.word}
						</text>
					{/if}
				</g>
			{/each}

			<line
				class="playhead"
				x1={x(playhead)}
				y1="0"
				x2={x(playhead)}
				y2={height}
			/>
		</svg>
	</div>
{:else}
	<p class="note-empty">No layers selected to show.</p>
{/if}

<style>
	.notes-toggles {
		display: flex;
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
	.notes-container {
		border: 1px solid var(--border-color-primary);
		border-radius: 4px;
		margin: 4px 0 8px;
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