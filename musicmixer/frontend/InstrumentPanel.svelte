<script lang="ts">
	import { diagramInstruments, diagramLayers } from "./mixerPanels.svelte";
	import type { MixerBar, MixerDiagrams } from "./types";

	// Two transparent layers per instrument, stacked: the
	// key's scale (drawn once, doesn't move) underneath, the
	// current bar's chord tones on top. Python guarantees
	// both share one coordinate system for a given
	// (key, instrument) pair, so no positioning happens here
	// - this component only decides which strings to look up
	// and whether each layer is visible.
	//
	// The current chord is found the same way ChordStrip
	// finds the current bar: the first timeline entry the
	// playhead is inside of. Kept independent of ChordStrip
	// rather than passed a bar object, since this panel can
	// be shown without the Chart panel being open at all.
	interface Props {
		diagrams: MixerDiagrams;
		timeline: MixerBar[];
		playhead: number;
	}

	let { diagrams, timeline, playhead }: Props = $props();

	const currentBar = $derived(
		timeline.find((bar) => playhead >= bar.start && playhead < bar.end)
	);

	const chosenInstruments = $derived(
		Object.keys(diagramInstruments).filter((name) => diagramInstruments[name])
	);
</script>

<div class="instrument-toggles">
	{#each Object.keys(diagramInstruments) as name}
		<label class="instrument-toggle">
			<input type="checkbox" bind:checked={diagramInstruments[name]} />
			{name}
		</label>
	{/each}
	<span class="layer-gap"></span>
	<label class="instrument-toggle">
		<input type="checkbox" bind:checked={diagramLayers.scale} />
		Scale
	</label>
	<label class="instrument-toggle">
		<input type="checkbox" bind:checked={diagramLayers.chord} />
		Chord
	</label>
</div>

{#if !chosenInstruments.length}
	<p class="instrument-empty">Choose an instrument to see it.</p>
{:else}
	<div class="instrument-grid">
		{#each chosenInstruments as name}
			{@const scaleSvg = diagrams.scale?.[name]}
			{@const chordSvg = currentBar
				? diagrams.chords?.[name]?.[currentBar.name]
				: undefined}
			<div class="instrument-card">
				<h4>{name}</h4>
				<div class="diagram-stack">
					{#if diagramLayers.scale && scaleSvg}
						<div class="layer scale-layer">{@html scaleSvg}</div>
					{/if}
					{#if diagramLayers.chord && chordSvg}
						<div
							class="layer chord-layer"
							class:stacked={diagramLayers.scale && scaleSvg}
						>{@html chordSvg}</div>
					{/if}
					{#if !diagramLayers.scale && !diagramLayers.chord}
						<p class="instrument-empty">No layer selected.</p>
					{:else if diagramLayers.chord && !chordSvg}
						<p class="instrument-empty">
							{currentBar ? "No chord picture for this bar." : "Nothing playing yet."}
						</p>
					{/if}
				</div>
			</div>
		{/each}
	</div>
{/if}

<style>
	.instrument-toggles {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 12px;
		margin: 4px 0 8px;
	}
	.instrument-toggle {
		font-size: 11px;
		color: var(--body-text-color-subdued);
		display: flex;
		align-items: center;
		gap: 3px;
		cursor: pointer;
	}
	.instrument-toggle input[type="checkbox"] {
		appearance: auto;
		accent-color: #607d8b;
		width: 12px;
		height: 12px;
	}
	.layer-gap {
		width: 1px;
		align-self: stretch;
		background: var(--border-color-primary);
	}
	.instrument-grid {
		display: flex;
		flex-wrap: wrap;
		gap: 16px;
	}
	.instrument-card h4 {
		margin: 0 0 4px;
		font-size: 12px;
		color: var(--body-text-color-subdued);
	}
	.diagram-stack {
		position: relative;
	}
	.layer {
		width: 100%;
	}
	.chord-layer.stacked {
		position: absolute;
		top: 0;
		left: 0;
		pointer-events: none;
	}
	.instrument-empty {
		font-size: 12px;
		color: var(--body-text-color-subdued);
	}
</style>
