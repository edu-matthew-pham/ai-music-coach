<script lang="ts">
	import {
		diagramInstruments,
		diagramVariant,
		diagramLayers,
		ensureInstrumentToggle,
		ensureInstrumentVariant,
		ensureInstrumentScale,
		diagramScale,
		previewChordCount
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
	// The current chord is found from the timeline entry
	// (bar) the playhead is inside of, the same way
	// ChordStrip finds its current bar - then within that
	// bar's own chords list, whichever one's start has
	// arrived. Kept independent of ChordStrip rather than
	// passed a bar object, since this panel can be shown
	// without the Chart panel being open at all.
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
			ensureInstrumentScale(family);
		}
	});

	const currentIndex = $derived(
		timeline.findIndex((bar) => playhead >= bar.start && playhead < bar.end)
	);

	const currentBar = $derived(
		currentIndex >= 0 ? timeline[currentIndex] : undefined
	);

	// Which musical key the Scale layer should draw - the
	// current bar's own key (Piece.key_at, resolved once in
	// Python and sent per bar), or the piece's opening key
	// before anything has started playing. diagrams.scale is
	// keyed by this musical key first, then by instrument -
	// not the same "key" as the instrument-variant loop
	// variable used further down in the template, which is
	// an unrelated naming collision worth keeping distinct.
	const currentMusicalKey = $derived(
		currentBar?.key ?? timeline[0]?.key
	);

	// A bar's own chords carry their position as beat_in_bar,
	// not seconds - converted here against that bar's own
	// beats-to-seconds ratio, since a phrase-view bar and a
	// bar elsewhere in the piece are not guaranteed the same
	// tempo-relative width once real per-bar lengths are
	// possible.
	function chordsWithSeconds(
		bar: MixerBar | undefined
	): { name: string; start: number }[] {
		if (!bar) return [];

		const secondsPerBeat = (bar.end - bar.start) / bar.beats;

		return bar.chords.map((chord) => ({
			name: chord.name,
			start: bar.start + chord.beat_in_bar * secondsPerBeat
		}));
	}

	// The chord actually sounding at the playhead - a bar can
	// now hold more than one (a syncopated split, or an
	// ordinary mid-bar change), so this is the last one whose
	// own start has arrived, the same "starts under, still
	// sounding" rule chord_at already uses in Python.
	const currentChord = $derived.by(() => {
		let found: { name: string; start: number } | undefined;

		for (const chord of chordsWithSeconds(currentBar)) {
			if (chord.start <= playhead) {
				found = chord;
			}
		}

		return found;
	});

	// The next N chords to arrive after the current one - a
	// later change in the same bar first, then bar by bar
	// forward. Walks as far as it needs to (a long carried
	// chord may sit across several bars), but stops at the
	// count asked for; this is a short preview of what is
	// coming, not a second chart. Carried entries are the
	// same chord still sounding, not a change, so they are
	// skipped rather than shown as a repeat.
	const nextChords = $derived.by(() => {
		const wanted = previewChordCount.value;
		if (wanted === 0 || currentIndex < 0) return [];

		const found: { name: string; start: number }[] = [];
		const currentStart = currentChord?.start ?? -Infinity;

		for (let i = currentIndex; i < timeline.length && found.length < wanted; i++) {
			const bar = timeline[i];
			const chords = chordsWithSeconds(bar);
			for (let c = 0; c < chords.length && found.length < wanted; c++) {
				if (i === currentIndex && chords[c].start <= currentStart) continue;
				if (bar.chords[c].carried) continue;
				found.push(chords[c]);
			}
		}

		return found;
	});

	const chosenInstruments = $derived(
		families.filter((family) => diagramInstruments[family])
	);

	// The actual key to look up in Python's data for a chosen
	// family: its name plus whichever variant is currently
	// selected for it, reconstructed here rather than stored
	// anywhere, since the two together are the only thing that
	// was ever ambiguous.
	// The one display height every diagram is drawn at, at
	// scale 1 - a UI number, deliberately not the shared
	// viewBox height in instrument_diagrams.py (196, drawing
	// units, huge on screen). Width follows each
	// instrument's own aspect ratio from there. Was a fixed
	// 100px in the stylesheet; now the base the per-family
	// scale slider multiplies.
	const BASE_HEIGHT = 100;

	// Preview chords draw as a row that always totals the
	// same width as the main diagram above it, rather than at
	// a fixed fraction of its size - measured from the real
	// rendered width (aspect ratio varies by instrument: a
	// piano and a violin neck are not the same shape), not
	// computed from BASE_HEIGHT, since the main diagram's
	// width is derived from its own intrinsic aspect ratio
	// and isn't known until it's actually on screen.
	//
	// At 1 upcoming chord this makes the single preview the
	// same size as the main diagram - deliberately reviving
	// what the very first "Next chord" design showed (a full
	// duplicate), now without the opacity that made it read
	// as broken rather than as a preview: showing one chord
	// at full size, chosen on purpose, is different from
	// showing one at full size because nothing shrank it.
	// At 2 or 3, each preview divides that same total width,
	// so the row's right edge always lines up with the main
	// diagram's, never overhanging it or leaving a gap.
	let mainWidths: Record<string, number> = $state({});
	const PREVIEW_GAP = 10;

	function previewSize(
		family: string,
		mainHeight: number,
		count: number
	): { width: number; height: number } {
		const mainWidth = mainWidths[family];
		if (!mainWidth || !count) return { width: 0, height: 0 };

		const width = (mainWidth - PREVIEW_GAP * (count - 1)) / count;
		// Same aspect ratio as the main diagram, so a shrunk
		// preview is a scaled copy, not a squashed one.
		const height = width * (mainHeight / mainWidth);
		return { width, height };
	}

	function keyFor(family: string): string {
		return `${family}, ${diagramVariant[family]}`;
	}

	// Discrete +/- buttons rather than a range slider - a
	// slider needs fine pointer control that a remote, a
	// touch tap from across a couch, or a fumbled click
	// mid-jam doesn't reliably give. Clamped to the same
	// 0.5-2.5 range the slider used; 10% steps, so 100% (the
	// reset target) always lands on an exact stop rather
	// than something the step size can drift past.
	const SCALE_MIN = 0.5;
	const SCALE_MAX = 2.5;
	const SCALE_STEP = 0.1;

	function setScale(family: string, next: number): void {
		const clamped = Math.min(SCALE_MAX, Math.max(SCALE_MIN, next));
		// Round to one decimal - repeated +/- on a float step
		// drifts (0.1 + 0.1 + 0.1 !== 0.3), and that drift
		// would show up as an ugly percentage and eventually
		// miss the exact 100% stop the reset button relies on.
		diagramScale[family] = Math.round(clamped * 10) / 10;
	}
</script>

<div class="instrument-toggles">
	{#each families as family}
		<span class="instrument-with-variant">
			<label class="instrument-toggle">
				<!-- checked= + onchange, not bind:checked - the same
				     reason the variant radios below already work
				     and this didn't: Svelte 5's bind writes the
				     DOM's default (unchecked -> false) back into
				     undefined state at mount, before the $effect
				     calling ensureInstrumentToggle runs, so its
				     "not yet set" guard saw false and kept it. -->
				<input
					type="checkbox"
					checked={diagramInstruments[family] ?? false}
					onchange={(event) =>
						(diagramInstruments[family] = (event.currentTarget as HTMLInputElement).checked)}
				/>
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
	<span class="instrument-toggle">
		Coming up
		<span class="variant-toggle" role="radiogroup" aria-label="Chords to preview">
			{#each [0, 1, 2, 3] as count}
				<label class="variant-option">
					<input
						type="radio"
						name="preview-count"
						checked={previewChordCount.value === count}
						onchange={() => (previewChordCount.value = count as 0 | 1 | 2 | 3)}
					/>
					{count === 0 ? "off" : count}
				</label>
			{/each}
		</span>
	</span>
</div>

{#if !chosenInstruments.length}
	<p class="instrument-empty">Choose an instrument to see it.</p>
{:else}
	<div class="instrument-grid">
		{#each chosenInstruments as family}
			{@const instrumentKey = keyFor(family)}
			{@const structureSvg = diagrams.structure?.[instrumentKey]}
			{@const scaleSvg = currentMusicalKey
				? diagrams.scale?.[currentMusicalKey]?.[instrumentKey]
				: undefined}
			{@const notesSvg = currentChord
				? diagrams.chords?.[instrumentKey]?.[currentChord.name]
				: undefined}
			{@const shapeSvg = currentChord
				? diagrams.shapes?.[instrumentKey]?.[currentChord.name]
				: undefined}
			{@const scale = diagramScale[family] ?? 1}
			<div class="instrument-card">
				<div class="card-head">
					<h4>{family} <span class="variant-label">({diagramVariant[family]})</span></h4>
					<div class="scale-control" role="group" aria-label="{family} size">
						<button
							type="button"
							class="scale-button"
							disabled={scale <= SCALE_MIN}
							aria-label="Shrink {family}"
							onclick={() => setScale(family, scale - SCALE_STEP)}
						>
							&minus;
						</button>
						<button
							type="button"
							class="scale-value"
							disabled={scale === 1}
							aria-label="Reset {family} size to 100%"
							onclick={() => setScale(family, 1)}
						>
							{Math.round(scale * 100)}%
						</button>
						<button
							type="button"
							class="scale-button"
							disabled={scale >= SCALE_MAX}
							aria-label="Enlarge {family}"
							onclick={() => setScale(family, scale + SCALE_STEP)}
						>
							&plus;
						</button>
					</div>
				</div>
				{#if structureSvg}
					<div
						class="diagram-stack"
						style="--diagram-height: {BASE_HEIGHT * scale}px"
						bind:clientWidth={mainWidths[family]}
					>
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
							Chord notes: {currentChord ? "no picture for this bar." : "nothing playing yet."}
						</p>
					{/if}
					{#if diagramLayers.chordShape && !shapeSvg}
						<p class="instrument-note">
							Chord shape: {currentChord
								? `no standard shape for ${currentChord.name} on ${family}.`
								: "nothing playing yet."}
						</p>
					{/if}

					{#if previewChordCount.value > 0}
						{@const preview = previewSize(family, BASE_HEIGHT * scale, nextChords.length)}
						<div class="preview-row" data-preview-row={family}>
							{#if nextChords.length}
								{#each nextChords as chord (chord.start)}
									{@const previewNotes = diagrams.chords?.[instrumentKey]?.[chord.name]}
									{@const previewShape = diagrams.shapes?.[instrumentKey]?.[chord.name]}
									<div class="preview-chord">
										<div
											class="diagram-stack sized"
											style="--diagram-height: {preview.height}px; width: {preview.width}px"
										>
											<div class="layer structure-layer">{@html structureSvg}</div>
											{#if diagramLayers.chordNotes && previewNotes}
												<div class="layer stacked chord-notes-layer">{@html previewNotes}</div>
											{/if}
											{#if diagramLayers.chordShape && previewShape}
												<div class="layer stacked chord-shape-layer">{@html previewShape}</div>
											{/if}
										</div>
										<div class="preview-name">{chord.name}</div>
									</div>
								{/each}
							{:else}
								<p class="instrument-note">Nothing after this.</p>
							{/if}
						</div>
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
		appearance: auto;
		accent-color: #607d8b;
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
	.card-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
		margin: 0 0 4px;
	}
	.instrument-card h4 {
		margin: 0;
		font-size: 12px;
		color: var(--body-text-color-subdued);
	}
	.scale-control {
		display: flex;
		align-items: stretch;
		gap: 2px;
	}
	.scale-button {
		font: inherit;
		font-size: 13px;
		width: 26px;
		padding: 0;
		border: 1px solid var(--border-color-primary);
		border-radius: 6px;
		background: var(--background-fill-primary);
		color: var(--body-text-color-subdued);
		cursor: pointer;
	}
	.scale-button:hover:not(:disabled) {
		background: var(--background-fill-secondary, #f5f5f5);
	}
	.scale-button:disabled {
		opacity: 0.4;
		cursor: default;
	}
	.scale-value {
		/* Also a button (resets to 100%) so it needs the same
		   reset as the others, not a plain span's defaults. */
		font: inherit;
		width: 42px;
		padding: 0 4px;
		border: 1px solid var(--border-color-primary);
		border-radius: 6px;
		background: var(--background-fill-primary);
		font-size: 10px;
		color: var(--body-text-color-subdued);
		text-align: center;
		cursor: pointer;
	}
	.scale-value:hover:not(:disabled) {
		background: var(--background-fill-secondary, #f5f5f5);
	}
	.scale-value:disabled {
		/* Already at 100% - visibly inert, not a dead-looking
		   button with nothing to click through to. */
		cursor: default;
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
		height: var(--diagram-height, 100px);
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
	.preview-row {
		display: flex;
		flex-wrap: nowrap;
		gap: 10px;
		margin-top: 8px;
		padding-top: 6px;
		border-top: 1px solid var(--border-color-primary);
	}
	.preview-chord {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 2px;
	}
	.diagram-stack.sized {
		/* Width is set inline per preview (computed to match
		   the main diagram's own measured aspect ratio) - the
		   intrinsic-width behaviour below (auto width from an
		   svg's own aspect ratio) would otherwise fight that,
		   since a shrunk preview's svg is the same intrinsic
		   drawing as the full-size one. */
		display: block;
	}
	.diagram-stack.sized .structure-layer :global(svg) {
		width: 100%;
	}
	.preview-name {
		font-size: 11px;
		color: var(--body-text-color-subdued);
	}
</style>