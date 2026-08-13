<script lang="ts">
	import { diagramInstruments, diagramLayers } from "./mixerPanels.svelte";
	import type { MixerBar, MixerDiagrams } from "./types";

	// Three layers per instrument, stacked: structure (the
	// instrument itself - keys, frets, strings) always at
	// the bottom and never toggled off, the key's scale
	// above it, and the current bar's chord above that in
	// one of two pictures - every place the chord occurs, or
	// one beginner shape for it. Python guarantees all of
	// these share one coordinate system for a given
	// instrument, so no positioning happens here - this
	// component only decides which layers are visible and
	// which chord to look up.
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
	<span class="layer-gap"></span>
	<label class="instrument-toggle">
		<input
			type="radio"
			name="chordMode"
			checked={diagramLayers.chordMode === "off"}
			onchange={() => (diagramLayers.chordMode = "off")}
		/>
		Off
	</label>
	<label class="instrument-toggle">
		<input
			type="radio"
			name="chordMode"
			checked={diagramLayers.chordMode === "notes"}
			onchange={() => (diagramLayers.chordMode = "notes")}
		/>
		Chord notes
	</label>
	<label class="instrument-toggle">
		<input
			type="radio"
			name="chordMode"
			checked={diagramLayers.chordMode === "shape"}
			onchange={() => (diagramLayers.chordMode = "shape")}
		/>
		Chord shape
	</label>
</div>

{#if !chosenInstruments.length}
	<p class="instrument-empty">Choose an instrument to see it.</p>
{:else}
	<div class="instrument-grid">
		{#each chosenInstruments as name}
			{@const structureSvg = diagrams.structure?.[name]}
			{@const scaleSvg = diagrams.scale?.[name]}
			{@const notesSvg = currentBar
				? diagrams.chords?.[name]?.[currentBar.name]
				: undefined}
			{@const shapeSvg = currentBar
				? diagrams.shapes?.[name]?.[currentBar.name]
				: undefined}
			{@const usingShapeFallback =
				diagramLayers.chordMode === "shape" && !!currentBar && !shapeSvg && !!notesSvg}
			{@const chordSvg =
				diagramLayers.chordMode === "shape" ? (shapeSvg ?? notesSvg) : notesSvg}
			<div class="instrument-card">
				<h4>{name}</h4>
				{#if structureSvg}
					<div class="diagram-stack">
						<div class="layer structure-layer">{@html structureSvg}</div>
						{#if diagramLayers.scale && scaleSvg}
							<div class="layer stacked scale-layer">{@html scaleSvg}</div>
						{/if}
						{#if diagramLayers.chordMode !== "off" && chordSvg}
							<div class="layer stacked chord-layer">{@html chordSvg}</div>
						{/if}
						{#if diagramLayers.chordMode !== "off" && !chordSvg}
							<p class="instrument-empty">
								{currentBar ? "No chord picture for this bar." : "Nothing playing yet."}
							</p>
						{/if}
					</div>
					{#if usingShapeFallback}
						<p class="instrument-note">
							No standard shape for {currentBar?.name} on {name} - showing every position instead.
						</p>
					{/if}
				{:else}
					<p class="instrument-empty">No picture for this instrument yet.</p>
				{/if}
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
	.instrument-toggle input[type="checkbox"],
	.instrument-toggle input[type="radio"] {
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
	.layer.stacked {
		position: absolute;
		top: 0;
		left: 0;
		pointer-events: none;
	}
	.instrument-empty {
		font-size: 12px;
		color: var(--body-text-color-subdued);
	}
	.instrument-note {
		font-size: 11px;
		color: var(--body-text-color-subdued);
		font-style: italic;
		margin: 4px 0 0;
	}
</style>