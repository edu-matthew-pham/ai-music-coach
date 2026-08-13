<script lang="ts">
	import { diagramInstruments, diagramLayers, previewNextChord } from "./mixerPanels.svelte";
	import type { MixerBar, MixerDiagrams } from "./types";

	// Four layers per instrument, stacked: structure (the
	// instrument itself - keys, frets, strings) always at
	// the bottom and never toggled off, then the key's
	// scale, every place the current chord's notes occur,
	// and one beginner shape for it - the last three all
	// independently toggleable, and all three can be on at
	// once. Python guarantees all of these share one
	// coordinate system for a given instrument, so no
	// positioning happens here - this component only decides
	// which layers are visible and which chord to look up.
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

	const currentIndex = $derived(
		timeline.findIndex((bar) => playhead >= bar.start && playhead < bar.end)
	);

	const currentBar = $derived(
		currentIndex >= 0 ? timeline[currentIndex] : undefined
	);

	// Each timeline entry is already one whole chord's span,
	// not one physical bar - read_chart merges consecutive
	// bars holding the same chord into a single entry before
	// this ever reaches the mixer. So the very next entry is
	// the next chord change, with no scanning needed to find
	// it.
	const nextBar = $derived(
		currentIndex >= 0 && currentIndex + 1 < timeline.length
			? timeline[currentIndex + 1]
			: undefined
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
		<input type="checkbox" bind:checked={diagramLayers.chordNotes} />
		Chord notes
	</label>
	<label class="instrument-toggle">
		<input type="checkbox" bind:checked={diagramLayers.chordShape} />
		Chord shape
	</label>
	<span class="layer-gap"></span>
	<label class="instrument-toggle">
		<input type="checkbox" bind:checked={previewNextChord.value} />
		Preview next chord
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
			{@const nextNotesSvg = nextBar
				? diagrams.chords?.[name]?.[nextBar.name]
				: undefined}
			{@const nextShapeSvg = nextBar
				? diagrams.shapes?.[name]?.[nextBar.name]
				: undefined}
			<div class="instrument-card">
				<h4>{name}</h4>
				{#if structureSvg}
					<div class="diagram-stack">
						<div class="layer structure-layer">{@html structureSvg}</div>
						{#if diagramLayers.scale && scaleSvg}
							<div class="layer stacked scale-layer">{@html scaleSvg}</div>
						{/if}
						{#if diagramLayers.chordNotes && notesSvg}
							<div class="layer stacked chord-notes-layer">{@html notesSvg}</div>
						{/if}
						{#if diagramLayers.chordShape && shapeSvg}
							<div class="layer stacked chord-shape-layer">{@html shapeSvg}</div>
						{/if}
					</div>
					{#if diagramLayers.chordNotes && !notesSvg}
						<p class="instrument-note">
							Chord notes: {currentBar ? "no picture for this bar." : "nothing playing yet."}
						</p>
					{/if}
					{#if diagramLayers.chordShape && !shapeSvg}
						<p class="instrument-note">
							Chord shape: {currentBar
								? `no standard shape for ${currentBar.name} on ${name}.`
								: "nothing playing yet."}
						</p>
					{/if}

					{#if previewNextChord.value}
						{#if nextBar}
							<p class="next-chord-label">Next: {nextBar.name}</p>
							<div class="diagram-stack next-chord-preview">
								<div class="layer structure-layer">{@html structureSvg}</div>
								{#if diagramLayers.scale && scaleSvg}
									<div class="layer stacked scale-layer">{@html scaleSvg}</div>
								{/if}
								{#if diagramLayers.chordNotes && nextNotesSvg}
									<div class="layer stacked chord-notes-layer">{@html nextNotesSvg}</div>
								{/if}
								{#if diagramLayers.chordShape && nextShapeSvg}
									<div class="layer stacked chord-shape-layer">{@html nextShapeSvg}</div>
								{/if}
							</div>
						{:else}
							<p class="instrument-note">Next: nothing after this.</p>
						{/if}
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
		/* Sized by its one normal-flow child, the structure
		   layer below - the stacked overlays are absolute
		   and don't contribute to this box's own size. */
		display: inline-block;
	}
	.layer {
		display: block;
	}
	.structure-layer :global(svg) {
		/* The svg tags themselves are injected via {@html}
		   from Python and arrive with their own explicit
		   width="100%" attribute - styling the wrapping div
		   alone (two earlier attempts) never reaches past
		   that, since Svelte's scoped styles don't apply
		   inside {@html} content without :global(), and a
		   div sized to "auto" around a child that's itself
		   sized to "100% of the div" is circular and
		   resolves unpredictably rather than to the child's
		   own intrinsic size.
		   Targeting the actual <svg> here and fixing its
		   height while leaving width unset lets the browser
		   compute width from the drawing's own intrinsic
		   aspect ratio, so every instrument renders at the
		   same height with no letterbox gap and no
		   distortion.
		   120px is a DISPLAY size, deliberately not the same
		   number as the shared viewBox height in
		   instrument_diagrams.py's PIANO_LAYOUT/
		   FRETBOARD_LAYOUT/VIOLIN_LAYOUT (196) - those are
		   internal drawing-space units, not screen pixels,
		   and setting this to 196 rendered everything at its
		   full native coordinate size, which is genuinely
		   huge. This number is a UI judgement call for the
		   panel - 100 is what looked right - free to retune
		   further by eye if it ever needs it; it only needs
		   to stay the same across every instrument, not
		   match anything in Python. */
		display: block;
		width: auto;
		height: 100px;
	}
	.layer.stacked {
		/* An overlay has to fill exactly the box the
		   structure layer already established, not size
		   itself independently. */
		position: absolute;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		pointer-events: none;
	}
	.layer.stacked :global(svg) {
		display: block;
		width: 100%;
		height: 100%;
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
	.next-chord-label {
		font-size: 11px;
		color: var(--body-text-color-subdued);
		margin: 8px 0 2px;
	}
	.next-chord-preview {
		opacity: 0.55;
	}
</style>