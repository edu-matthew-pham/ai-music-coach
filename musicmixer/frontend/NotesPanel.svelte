<script lang="ts">
	import { engine } from "./mixerEngine.svelte";
	import { noteLayers } from "./mixerPanels.svelte";
	import type { MixerNote, MixerBar } from "./types";

	// This panel is read-only by design, for now. Selecting a
	// stretch is still the chord strip's job - both panels
	// read the same playhead and loop bounds, so toggling
	// this on adds a picture without adding a second, competing
	// way to choose what plays.
	interface Props {
		notes: MixerNote[];
		timeline: MixerBar[];
		playhead: number;
		follow: boolean;
	}

	let { notes, timeline, playhead, follow }: Props = $props();

	const ROW_HEIGHT = 14;

	// Only the toggled-on layers count towards what is drawn
	// AND towards the pitch range - bass alone gets a short
	// box, not a tall one with empty space where hidden
	// voices would have been.
	const visibleNotes = $derived(
		notes.filter((note) => noteLayers[note.layer])
	);

	const pitchRange = $derived.by(() => {
		if (!visibleNotes.length) return { lowest: 60, highest: 72 };
		let lowest = visibleNotes[0].midi;
		let highest = visibleNotes[0].midi;
		for (const note of visibleNotes) {
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

	// The scale is chosen so that a few bars fill the visible
	// width, rather than a fixed pixels-per-second that packed
	// the whole song in and crowded every label together the
	// way bar 3 always did on the static chart. Falls back to
	// the plain seconds-based scale when there is no bar data
	// to measure a bar's length from.
	const BARS_VISIBLE = 3;
	const FALLBACK_PX_PER_SECOND = 60;

	let viewportWidth = $state(600);

	const pxPerSecond = $derived.by(() => {
		if (timeline.length < 2) return FALLBACK_PX_PER_SECOND;
		const barLength = timeline[1].start - timeline[0].start;
		if (barLength <= 0) return FALLBACK_PX_PER_SECOND;
		return viewportWidth / (barLength * BARS_VISIBLE);
	});

	const duration = $derived(
		notes.reduce((max, note) => Math.max(max, note.start + note.length), 0)
	);

	const width = $derived(Math.max(duration * pxPerSecond, viewportWidth));

	let container: HTMLElement | null = $state(null);

	$effect(() => {
		if (container) viewportWidth = container.clientWidth || viewportWidth;
	});

	$effect(() => {
		if (follow && container) {
			const target = playhead * pxPerSecond - viewportWidth / 2;
			container.scrollLeft = Math.max(0, target);
		}
	});
</script>

<div class="notes-toggles">
	{#each Object.keys(noteLayers) as name}
		<label class="layer-toggle">
			<input type="checkbox" bind:checked={noteLayers[name]} />
			{name}
		</label>
	{/each}
</div>

{#if visibleNotes.length}
	<div class="notes-container" bind:this={container}>
		<svg {width} {height} viewBox="0 0 {width} {height}">
			{#if engine.loopFrom !== null && engine.loopTo !== null}
				<rect
					class="loop-region"
					x={engine.loopFrom * pxPerSecond}
					y="0"
					width={(engine.loopTo - engine.loopFrom) * pxPerSecond}
					{height}
				/>
			{/if}

			{#each timeline as bar}
				<line
					class="bar-line"
					x1={bar.start * pxPerSecond}
					y1="0"
					x2={bar.start * pxPerSecond}
					y2={height}
				/>
			{/each}

			{#each visibleNotes as note}
				<g>
					<rect
						class="note-box"
						x={note.start * pxPerSecond}
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
							x={note.start * pxPerSecond + (note.length * pxPerSecond) / 2}
							y={y(note.midi) + ROW_HEIGHT / 2}
							fill={note.colour}
						>
							{noteName(note.midi)}
						</text>
					{/if}
					{#if note.word}
						<text
							class="note-word"
							x={note.start * pxPerSecond + (note.length * pxPerSecond) / 2}
							y={y(note.midi) + ROW_HEIGHT + 10}
						>
							{note.word}
						</text>
					{/if}
				</g>
			{/each}

			<line
				class="playhead"
				x1={playhead * pxPerSecond}
				y1="0"
				x2={playhead * pxPerSecond}
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
		overflow-x: auto;
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