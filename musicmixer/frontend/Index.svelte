<script lang="ts">
	import type { MusicMixerProps, MusicMixerEvents } from "./types";
	import type { MixerBar } from "./types";
	import type { MixerPhrase } from "./types";
	import { Gradio } from "@gradio/utils";
	import { Block } from "@gradio/atoms";
	import { onDestroy, onMount } from "svelte";
	import { engine } from "./mixerEngine.svelte";
	import {
		panels,
		readScale,
		setReadScale,
		READ_SCALE_MIN,
		READ_SCALE_MAX,
		READ_SCALE_STEP,
		viewPreset,
		applyPreset,
		showNextPreview,
		previewSideBySide
	} from "./mixerPanels.svelte";
	import Transport from "./Transport.svelte";
	import PanelToggles from "./PanelToggles.svelte";
	import ChordStrip from "./ChordStrip.svelte";
	import PhraseList from "./PhraseList.svelte";
	import MixerModal from "./MixerModal.svelte";
	import NotesPanel from "./NotesPanel.svelte";
	import LyricsPanel from "./LyricsPanel.svelte";
	import InstrumentPanel from "./InstrumentPanel.svelte";

	// This file is deliberately thin: it wires Gradio's value
	// in and out, and holds the handful of actions that touch
	// both the engine and Python's copy of the value. Every
	// panel - Transport, PanelToggles, ChordStrip, MixerModal
	// - reads the shared engine/panels state directly rather
	// than being handed a slice of it, and calls back up here
	// only for the few actions that need to report to Python.
	// A new panel means a new file that imports engine the
	// same way, plus one line rendering it here - nothing
	// about the panels already working has to change.

	// $props() is captured into a named const rather than
	// inlined, and the warning below is a known false
	// positive for that: Gradio's constructor takes exactly
	// what $props() returns, and reactivity is established
	// inside the Gradio class itself (a $state field plus
	// an internal $effect watching this same argument for
	// the component's whole lifetime), not by how this
	// local variable is read afterwards. Confirmed against
	// upstream's own simpletextbox template and Gradio's
	// utils_svelte.ts source, which ship this identical
	// two-line form.
	const props = $props();
	// svelte-ignore state_referenced_locally
	const gradio = new Gradio<MusicMixerEvents, MusicMixerProps>(props);

	const layers = $derived(gradio.props.value?.layers ?? []);
	const timeline = $derived(gradio.props.value?.timeline ?? []);
	const notes = $derived(gradio.props.value?.notes ?? []);
	const phrases = $derived(gradio.props.value?.phrases ?? []);
	const diagrams = $derived(
		gradio.props.value?.diagrams ??
			{ structure: {}, scale: {}, chords: {}, shapes: {} }
	);

	// The component's own width, not the screen's - the
	// mixer can be narrow on a wide desktop (a small window,
	// a Gradio column sharing the row) just as easily as
	// on a phone, and it should respond to the room it is
	// actually given either way. One breakpoint, tuned by
	// looking at the real layout rather than argued about
	// in advance.
	const NARROW_BREAKPOINT = 600;
	let containerWidth = $state(0);
	const narrow = $derived(
		containerWidth > 0 && containerWidth < NARROW_BREAKPOINT
	);

	// LyricsPanel's one mode prop, decided here and nowhere
	// else - the view preset takes priority (it's an explicit
	// choice), otherwise it's derived from whether Notes is
	// showing at all. Replaces separately computed solo/
	// tabView booleans, which let the same state be implied
	// two different places and drift out of sync.
	const lyricsMode = $derived.by((): "paired" | "windowed" | "tab" | "singstar" => {
		if (viewPreset.value === "tab") return "tab";
		if (viewPreset.value === "singstar") return "singstar";
		return panels.notes ? "paired" : "windowed";
	});

	// SingStar's stacked layout gets margins on a wide screen
	// or TV by default - full edge-to-edge width doesn't
	// actually help two centred, glance-down panels, it just
	// stretches the gap between them. The one exception is
	// Notes' own "side by side" preview (the current phrase's
	// pitch boxes next to the upcoming phrase's, side by side
	// rather than stacked) - that genuinely wants the width
	// back, so margins step aside for it specifically rather
	// than fighting it. Mirrors NotesPanel's own condition for
	// entering that layout (showNextPreview && previewSideBySide
	// && !narrow) - if NotesPanel wouldn't actually go wide,
	// margins here shouldn't back off for nothing.
	const singstarWide = $derived(
		viewPreset.value === "singstar" &&
			showNextPreview.value &&
			previewSideBySide.value &&
			!narrow
	);

	// A loop is seconds into a particular song. Carried over
	// into a different one it means nothing - possibly a
	// stretch past the new song's own end - so it is cleared
	// here, the moment new layers are seen, rather than only
	// once Play is next pressed and forces a decode. Run
	// before the loop-seeding block below: a freshly built
	// mixer always sends loop_start as null anyway, so this
	// ordering just means nothing is left to re-seed by
	// mistake. Wrapped in $effect deliberately - plain
	// top-level code here would only run once, at mount, and
	// silently never clear a stale loop again after the
	// first song. It happens to keep working without this
	// today only because Gradio 6 remounts the whole
	// component on every value round trip; that is not a
	// reactivity guarantee worth relying on.
	$effect(() => {
		engine.noteLayers(layers);
	});

	// Fader positions default from the engine (survives a
	// remount) and fall back to each layer's opening level
	// only the first time that layer is ever seen.
	$effect(() => {
		for (const layer of layers) {
			if (!(layer.name in engine.levels)) {
				engine.levels[layer.name] = layer.level;
			}
		}
	});

	// Loop selection round-trips through Gradio's normal
	// value/change contract, since that already worked from
	// the first test - only the audio needed the engine.
	// Seeded from whatever Python last sent, so a remount
	// mid-selection does not lose it.
	if (gradio.props.value?.loop_start != null && engine.loopFrom === null) {
		engine.loopFrom = gradio.props.value.loop_start;
		engine.loopTo = gradio.props.value.loop_end ?? null;
	}

	// This instance's own display loop. Destroyed with the
	// instance; the engine and its sound are not.
	let playhead = $state(engine.position());
	let frame: number | null = null;

	function tick(): void {
		playhead = engine.position();
		frame = requestAnimationFrame(tick);
	}
	tick();

	onDestroy(() => {
		if (frame !== null) cancelAnimationFrame(frame);
	});

	let follow = $state(true);

	function reportValue(): void {
		if (gradio.props.value) {
			gradio.props.value.loop_start = engine.loopFrom;
			gradio.props.value.loop_end = engine.loopTo;
		}
		gradio.dispatch("change");
	}

	function selectBar(bar: MixerBar, event: MouseEvent | KeyboardEvent): void {
		const wasPlaying = engine.playing;

		// Only tell Python when the range itself changed - a
		// scrub or a preview leaves loop_start/loop_end
		// untouched, so there is nothing worth a round trip
		// for, and one fewer round trip is one fewer remount
		// to flicker through.
		const rangeChanged = engine.select(bar, event.shiftKey);
		playhead = engine.position();

		if (rangeChanged) {
			reportValue();
		}

		if (wasPlaying) {
			engine.play(layers);
		}
	}

	function selectPhrase(phrase: MixerPhrase, event: MouseEvent | KeyboardEvent): void {
		// Phrases work like the chart strip - click selects
		// and seeks, shift-click extends a range from the
		// last anchor to cover several phrases for repeating -
		// but with one deliberate difference: a phrase click
		// always starts playing. Practising a phrase is the
		// whole point of the panel, so picking one should not
		// be a separate step from hearing it - unlike a bar
		// click, which only resumes playback if it was already
		// running.
		const rangeChanged = engine.select(phrase, event.shiftKey);
		playhead = engine.position();

		if (rangeChanged) {
			reportValue();
		}

		engine.play(layers);
	}

	function clearSelection(): void {
		engine.clearLoop();
		playhead = 0;
		reportValue();
	}

	function toggleRepeat(): void {
		// Repeat is read once, when play() builds the audio
		// source - it can't take effect on a source that
		// already exists. So a change while playing has to
		// restart from here, with the new setting baked into
		// the new source, rather than trying to mutate one
		// already running.
		if (engine.playing) {
			engine.play(layers, engine.position());
		}
	}

	function levelChanged(name: string): void {
		engine.setLevel(name, engine.levels[name]);
		gradio.dispatch("input");
	}

	function masterVolumeChanged(): void {
		engine.setMasterVolume(engine.masterVolume);
		gradio.dispatch("input");
	}

	// Full screen covers the whole viewport by making
	// Gradio's own wrapper element position: fixed (the CSS
	// rule lives in main.py's global stylesheet, since a
	// component's scoped styles can't reach out to style
	// Gradio's own Block wrapper) - found by the same elem_id
	// main.py gave it, rather than a second hardcoded string
	// here that could drift from the one there.
	//
	// The toggle lives inside .mixer, not as a separate
	// Gradio button outside it: a control outside the element
	// being fullscreened gets visually covered the instant
	// fullscreen activates, since the wrapper now sits above
	// everything else in the page - Escape ends up the only
	// thing that still works. Inside, the button stays in the
	// fullscreened box itself and keeps working as a real
	// toggle, not just an escape hatch.
	let fullscreenActive = $state(false);

	function wrapperElement(): HTMLElement | null {
		const id = gradio.shared.elem_id;
		return id ? document.getElementById(id) : null;
	}

	// Full screen replaces whatever the page was scrolled to
	// with the mixer covering everything; exiting should land
	// back on the Playback section rather than wherever the
	// page underneath happened to be, or nowhere in
	// particular. Same scrollIntoView the nav bar's own
	// Playback link already uses (anchor_link in main.py), so
	// exiting behaves like following that link.
	function scrollToPlayback(): void {
		document.getElementById("playback")
			?.scrollIntoView({ behavior: "smooth" });
	}

	function toggleFullscreen(): void {
		const wrapper = wrapperElement();
		if (!wrapper) return;
		fullscreenActive = wrapper.classList.toggle("fullscreen-mode");
		document.body.style.overflow = fullscreenActive ? "hidden" : "";
		if (!fullscreenActive) scrollToPlayback();
	}

	onMount(() => {
		function handleEscape(event: KeyboardEvent): void {
			if (event.key !== "Escape" || !fullscreenActive) return;
			wrapperElement()?.classList.remove("fullscreen-mode");
			document.body.style.overflow = "";
			fullscreenActive = false;
			scrollToPlayback();
		}

		window.addEventListener("keydown", handleEscape);
		return () => window.removeEventListener("keydown", handleEscape);
	});
</script>

<Block
	visible={gradio.shared.visible}
	elem_id={gradio.shared.elem_id}
	elem_classes={gradio.shared.elem_classes}
	scale={gradio.shared.scale}
	min_width={gradio.shared.min_width}
	allow_overflow={true}
	padding={true}
>
	<div class="mixer" style="--read-scale: {readScale.value}" bind:clientWidth={containerWidth}>
		<button
			type="button"
			class="fullscreen-toggle"
			onclick={toggleFullscreen}
			aria-pressed={fullscreenActive}
			title={fullscreenActive ? "Exit full screen" : "Full screen"}
		>
			{fullscreenActive ? "\u2715 Exit full screen" : "\u26f6 Full screen"}
		</button>

		<!-- Reading order, top to bottom, is what the eye needs
		     while playing, then what only matters between
		     takes: transport, toggles, and the Mix button in
		     one row; the bar strip and phrase strip; the
		     instrument diagrams; then Lyrics and Notes sharing
		     one row at the bottom, each getting a share of the
		     same vertical space rather than either claiming a
		     full-width row on its own. That row is last on
		     purpose - Notes is the one panel whose height
		     genuinely changes while playing (more layers, a
		     longer phrase), and at the bottom that growth
		     pushes nothing else on the page. -->
		<div class="header-row">
			<Transport
				{layers}
				{playhead}
				bind:follow
				hasTimeline={timeline.length > 0}
				onClearSelection={clearSelection}
				onToggleRepeat={toggleRepeat}
				onMasterVolumeChanged={masterVolumeChanged}
			/>
			<PanelToggles
				hasTimeline={timeline.length > 0}
				hasNotes={notes.length > 0}
				hasDiagrams={Object.keys(diagrams.structure ?? {}).length > 0}
			/>
			<div class="text-scale-control" role="group" aria-label="Text size">
				<button
					type="button"
					class="text-scale-button"
					disabled={readScale.value <= READ_SCALE_MIN}
					aria-label="Smaller text"
					onclick={() => setReadScale(readScale.value - READ_SCALE_STEP)}
				>
					&minus;
				</button>
				<button
					type="button"
					class="text-scale-value"
					disabled={readScale.value === 1}
					aria-label="Reset text size to 100%"
					onclick={() => setReadScale(1)}
				>
					{Math.round(readScale.value * 100)}%
				</button>
				<button
					type="button"
					class="text-scale-button"
					disabled={readScale.value >= READ_SCALE_MAX}
					aria-label="Bigger text"
					onclick={() => setReadScale(readScale.value + READ_SCALE_STEP)}
				>
					&plus;
				</button>
			</div>
			<div class="preset-buttons" role="group" aria-label="View">
				<button
					type="button"
					class="preset-button"
					aria-pressed={viewPreset.value === "tab"}
					onclick={() => applyPreset("tab")}
				>
					{viewPreset.value === "tab" ? "Exit tab view" : "Tab view"}
				</button>
				<button
					type="button"
					class="preset-button"
					aria-pressed={viewPreset.value === "singstar"}
					onclick={() => applyPreset("singstar")}
				>
					{viewPreset.value === "singstar" ? "Exit SingStar view" : "SingStar view"}
				</button>
			</div>
			{#if panels.faders}
				<MixerModal {layers} onLevelChanged={levelChanged} />
			{/if}
		</div>

		{#if panels.strip}
			<ChordStrip {timeline} {playhead} {follow} onSelectBar={selectBar} />
		{/if}

		{#if panels.phrases}
			<PhraseList {phrases} {playhead} onSelectPhrase={selectPhrase} {narrow} />
		{/if}

		{#if panels.instruments}
			<InstrumentPanel {diagrams} {timeline} {playhead} />
		{/if}

		{#if panels.lyrics || panels.notes}
			{#if viewPreset.value === "singstar"}
				<!-- Notes above, a compact Lyrics strip below -
				     stacked, not side by side. Lyrics gets
				     mode="singstar": exactly current + next,
				     chords included - a glance-down reference
				     for an instrument while the pitch view
				     carries the singing, not a second thing
				     competing for the eye. -->
				<div class="lyrics-and-notes singstar" class:wide={singstarWide}>
					{#if panels.notes}
						<div class="notes-cell">
							<NotesPanel {notes} {timeline} {phrases} {playhead} {narrow} />
						</div>
					{/if}
					{#if panels.lyrics}
						<div class="lyrics-cell">
							<LyricsPanel {notes} {timeline} {phrases} {playhead} mode={lyricsMode} />
						</div>
					{/if}
				</div>
			{:else}
				<div class="lyrics-and-notes" class:narrow>
					{#if panels.lyrics}
						<div class="lyrics-cell">
							<LyricsPanel {notes} {timeline} {phrases} {playhead} mode={lyricsMode} />
						</div>
					{/if}
					{#if panels.notes}
						<div class="notes-cell">
							<NotesPanel {notes} {timeline} {phrases} {playhead} {narrow} />
						</div>
					{/if}
				</div>
			{/if}
		{/if}
	</div>
</Block>

<style>
	.mixer {
		font-family: sans-serif;
		position: relative;
	}
	.fullscreen-toggle {
		position: absolute;
		top: 0;
		right: 0;
		font: inherit;
		font-size: 11px;
		padding: 4px 10px;
		border: 1px solid var(--border-color-primary);
		border-radius: 6px;
		background: var(--background-fill-primary);
		color: var(--body-text-color-subdued);
		cursor: pointer;
		z-index: 1;
	}
	.fullscreen-toggle:hover {
		background: var(--background-fill-secondary, #f5f5f5);
	}
	.header-row {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 8px 18px;
		margin-bottom: 6px;
		/* leaves room for the absolute-positioned full-screen
		   toggle in the top-right corner */
		padding-right: 110px;
	}
	.lyrics-and-notes {
		display: flex;
		align-items: flex-start;
		gap: 16px;
	}
	.lyrics-and-notes.narrow {
		flex-direction: column;
	}
	.lyrics-and-notes.singstar {
		/* Stacked, not side by side - Notes first (the thing
		   actually being sung to), a compact Lyrics strip
		   below it. align-items: stretch so each cell takes
		   the full width rather than sizing to its own
		   content, the way flex-start (the default above)
		   would leave Lyrics only as wide as its text.
		   Margined and centred by default - on a wide monitor
		   or a TV, letting two already-centred panels stretch
		   edge to edge doesn't add anything, it just widens the
		   gap between short lines of text. 1200px keeps both
		   panels a comfortable reading width regardless of how
		   wide the actual screen is. */
		flex-direction: column;
		align-items: stretch;
		gap: 12px;
		max-width: 1200px;
		margin: 0 auto;
	}
	.lyrics-and-notes.singstar.wide {
		/* Notes' own "side by side" preview genuinely wants
		   the width back (two phrases' worth of pitch boxes
		   next to each other) - margins step aside for it
		   rather than squeezing it into the same 1200px cap
		   everything else defaults to. */
		max-width: none;
		margin: 0;
	}
	.lyrics-and-notes.singstar .lyrics-cell,
	.lyrics-and-notes.singstar .notes-cell {
		/* The 3:7 grow ratio and fixed bases below are what
		   split a shared ROW's leftover width - along a
		   column axis that's a different axis (height, not
		   width) and would just be noise here. Reset to
		   "take your own natural height, don't fight your
		   neighbour for space" instead. */
		flex: 0 1 auto;
		min-width: 0;
	}
	.lyrics-cell {
		/* flex-grow of 3 against notes-cell's 7 - what actually
		   sets a stable 30/70 split of leftover row space is
		   the GROW ratio, not the flex-basis percentages
		   (basis only sets each item's resting size before any
		   space gets divided up). Equal grow values (both 1)
		   is what silently pulled this to ~50/50 before, no
		   matter what the basis said. */
		flex: 3 1 220px;
		min-width: 220px;
	}
	.lyrics-and-notes.narrow .lyrics-cell {
		min-width: 0;
	}
	.notes-cell {
		flex: 7 1 260px;
		min-width: 260px;
	}
	.lyrics-and-notes.narrow .notes-cell {
		min-width: 0;
	}
	.text-scale-control {
		display: flex;
		align-items: stretch;
		gap: 2px;
	}
	.text-scale-button {
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
	.text-scale-button:hover:not(:disabled) {
		background: var(--background-fill-secondary, #f5f5f5);
	}
	.text-scale-button:disabled {
		opacity: 0.4;
		cursor: default;
	}
	.text-scale-value {
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
	.text-scale-value:hover:not(:disabled) {
		background: var(--background-fill-secondary, #f5f5f5);
	}
	.text-scale-value:disabled {
		cursor: default;
	}
	.preset-buttons {
		display: flex;
		gap: 6px;
	}
	.preset-button {
		font: inherit;
		font-size: 12px;
		padding: 5px 10px;
		border: 1px solid var(--border-color-primary);
		border-radius: 8px;
		background: var(--background-fill-primary);
		color: var(--body-text-color-subdued);
		cursor: pointer;
	}
	.preset-button:hover {
		background: var(--background-fill-secondary, #f5f5f5);
	}
	.preset-button[aria-pressed="true"] {
		border-color: #2e7d32;
		background: #e8f5e9;
		color: #2e7d32;
	}
</style>