<script lang="ts">
	import { engine } from "./mixerEngine.svelte";
	import type { MixerNote } from "./types";

	// This panel is read-only by design, for now. Selecting a
	// stretch is still the chord strip's job - both panels
	// read the same playhead and loop bounds, so toggling
	// this on adds a picture without adding a second, competing
	// way to choose what plays. If clicking inside the note
	// view to select turns out to be wanted later, it can call
	// the same engine.select() the strip already does; nothing
	// here would need to change to support that.
	interface Props {
		notes: MixerNote[];
		playhead: number;
		follow: boolean;
	}

	let { notes, playhead, follow }: Props = $props();

	const PX_PER_SECOND = 60;
	const ROW_HEIGHT = 14;

	const pitchRange = $derived.by(() => {
		if (!notes.length) return { lowest: 60, highest: 72 };
		let lowest = notes[0].midi;
		let highest = notes[0].midi;
		for (const note of notes) {
			if (note.midi < lowest) lowest = note.midi;
			if (note.midi > highest) highest = note.midi;
		}
		// A row of headroom either side, so a note at the
		// very top or bottom of the range is not drawn
		// flush against the edge.
		return { lowest: lowest - 1, highest: highest + 1 };
	});

	const duration = $derived(
		notes.reduce((max, note) => Math.max(max, note.start + note.length), 0)
	);

	const width = $derived(Math.max(duration * PX_PER_SECOND, 200));
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

	$effect(() => {
		if (follow && container) {
			const target = playhead * PX_PER_SECOND - container.clientWidth / 2;
			container.scrollLeft = Math.max(0, target);
		}
	});
</script>

{#if notes.length}
	<div class="notes-container" bind:this={container}>
		<svg {width} {height} viewBox="0 0 {width} {height}">
			{#if engine.loopFrom !== null && engine.loopTo !== null}
				<rect
					class="loop-region"
					x={engine.loopFrom * PX_PER_SECOND}
					y="0"
					width={(engine.loopTo - engine.loopFrom) * PX_PER_SECOND}
					{height}
				/>
			{/if}

			{#each notes as note}
				<g>
					<rect
						class="note-box"
						x={note.start * PX_PER_SECOND}
						y={y(note.midi) + 1}
						width={Math.max(note.length * PX_PER_SECOND - 1, 2)}
						height={ROW_HEIGHT - 2}
						fill={note.colour}
						fill-opacity={note.layer === "Melody" ? 0.22 : 0.14}
						stroke={note.colour}
					/>
					{#if note.length * PX_PER_SECOND > 20}
						<text
							class="note-label"
							x={note.start * PX_PER_SECOND + (note.length * PX_PER_SECOND) / 2}
							y={y(note.midi) + ROW_HEIGHT / 2}
							fill={note.colour}
						>
							{noteName(note.midi)}
						</text>
					{/if}
					{#if note.word}
						<text
							class="note-word"
							x={note.start * PX_PER_SECOND + (note.length * PX_PER_SECOND) / 2}
							y={y(note.midi) + ROW_HEIGHT + 10}
						>
							{note.word}
						</text>
					{/if}
				</g>
			{/each}

			<line
				class="playhead"
				x1={playhead * PX_PER_SECOND}
				y1="0"
				x2={playhead * PX_PER_SECOND}
				y2={height}
			/>
		</svg>
	</div>
{:else}
	<p class="note-empty">No notes to show yet.</p>
{/if}

<style>
	.notes-container {
		overflow-x: auto;
		border: 1px solid var(--border-color-primary);
		border-radius: 4px;
		margin: 8px 0;
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
	.playhead {
		stroke: #2e7d32;
		stroke-width: 2;
	}
	.note-empty {
		font-size: 13px;
		color: var(--body-text-color-subdued);
	}
</style>
