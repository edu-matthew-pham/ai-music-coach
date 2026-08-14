<script lang="ts">
	import {
		diagramInstruments,
		diagramVariant,
		diagramLayers,
		ensureInstrumentToggle,
		ensureInstrumentVariant,
		previewNextChord
	} from "./mixerPanels.svelte";
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

	// Python's own data, not a list typed a second time here -
	// diagrams.structure always carries every size variant
	// instrument_diagrams.py's INSTRUMENTS list knows about
	// ("Piano, 2 octaves", "Piano, 3 octaves", ...), whether
	// or not a picture happens to be toggled on. Split each
	// into the family the player thinks about ("Piano") and
	// the size variant ("3 octaves") - the toggle belongs to
	// the family, the variant is a sub-choice within it.
	const availableInstruments = $derived(Object.keys(diagrams.structure ?? {}));

	function familyOf(name: string): string {
		return name.split(", ")[0];
	}

	function variantOf(name: string): string {
		return name.slice(familyOf(name).length + 2);
	}

	// One entry per family, in first-seen order, listing every
	// variant Python sent for it - always 2 today (compact and
	// full), but nothing here assumes that count.
	const familyVariants = $derived.by(() => {
		const map = new Map<string, string[]>();
		for (const name of availableInstruments) {
			const family = familyOf(name);
			const variant = variantOf(name);
			const existing = map.get(family);
			if (existing) {
				existing.push(variant);
			} else {
				map.set(family, [variant]);
			}
		}
		return map;
	});

	const families = $derived([...familyVariants.keys()]);

	// Each family gets a toggle-state entry and a chosen
	// variant the first time it's seen; both helpers are
	// no-ops once set, so safe to call on every render.
	$effect(() => {
		for (const [family, variants] of familyVariants) {
			ensureInstrumentToggle(family);
			ensureInstrumentVariant(family, variants[0]);
		}
	});

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
		families.filter((family) => diagramInstruments[family])
	);

	// The actual key to look up in Python's data for a chosen
	// family: its name plus whichever variant is currently
	// selected for it, reconstructed here rather than stored
	// anywhere, since the two together are the only thing that
	// was ever ambiguous.
	function keyFor(family: string): string {
		return `${family}, ${diagramVariant[family]}`;
	}
</script>

<div class="instrument-toggles">
	{#each families as family}
		<span class="instrument-with-variant">
			<label class="instrument-toggle">
				<input type="checkbox" bind:checked={diagramInstruments[family]} />
				{family}
			</label>
			{#if (familyVariants.get(family)?.length ?? 0) > 1}
				<span class="variant-toggle">
					{#each familyVariants.get(family) ?? [] as variant}
						<label class="variant-option">
							<input
								type="radio"
								name="variant-{family}"
								checked={diagramVariant[family] === variant}
								onchange={() => (diagramVariant[family] = variant)}
							/>
							{variant}
						</label>
					{/each}
				</span>
			{/if}
		</span>
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
		{#each chosenInstruments as family}
			{@const key = keyFor(family)}
			{@const structureSvg = diagrams.structure?.[key]}
			{@const scaleSvg = diagrams.scale?.[key]}
			{@const notesSvg = currentBar
				? diagrams.chords?.[key]?.[currentBar.name]
				: undefined}
			{@const shapeSvg = currentBar
				? diagrams.shapes?.[key]?.[currentBar.name]
				: undefined}
			{@const nextNotesSvg = nextBar
				? diagrams.chords?.[key]?.[nextBar.name]
				: undefined}
			{@const nextShapeSvg = nextBar
				? diagrams.shapes?.[key]?.[nextBar.name]
				: undefined}
			<div class="instrument-card">
				<h4>{family} <span class="variant-label">({diagramVariant[family]})</span></h4>
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
								? `no standard shape for ${currentBar.name} on ${family}.`
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
	.instrument-with-variant {
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.variant-toggle {
		display: flex;
		gap: 6px;
		padding: 1px 6px;
		border-radius: 10px;
		background: var(--background-fill-secondary);
	}
	.variant-option {
		font-size: 10px;
		color: var(--body-text-color-subdued);
		display: flex;
		align-items: center;
		gap: 2px;
		cursor: pointer;
	}
	.variant-option input[type="radio"] {
		width: 10px;
		height: 10px;
		margin: 0;
	}
	.variant-label {
		font-weight: 400;
		opacity: 0.7;
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
		   100px is a DISPLAY size, deliberately not the same
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