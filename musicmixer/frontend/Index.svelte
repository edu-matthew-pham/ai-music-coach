<script lang="ts">
	import type { MusicMixerProps, MusicMixerEvents } from "./types";
	import type { MixerBar } from "./types";
	import type { MixerPhrase } from "./types";
	import { Gradio } from "@gradio/utils";
	import { Block } from "@gradio/atoms";
	import { onDestroy, onMount } from "svelte";
	import { engine } from "./mixerEngine.svelte";
	import { panels, instrumentsBesideMixer, sideBySideLayout } from "./mixerPanels.svelte";
	import Transport from "./Transport.svelte";
	import PanelToggles from "./PanelToggles.svelte";
	import ChordStrip from "./ChordStrip.svelte";
	import FaderPanel from "./FaderPanel.svelte";
	import NotesPanel from "./NotesPanel.svelte";
	import PhraseList from "./PhraseList.svelte";
	import LyricsPanel from "./LyricsPanel.svelte";
	import InstrumentPanel from "./InstrumentPanel.svelte";

	// This file is deliberately thin: it wires Gradio's value
	// in and out, and holds the handful of actions that touch
	// both the engine and Python's copy of the value. Every
	// panel - Transport, PanelToggles, ChordStrip, FaderPanel
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
	// "Beside mixer" splitting the space) just as easily as
	// on a phone, and it should respond to the room it is
	// actually given either way. One breakpoint, tuned by
	// looking at the real layout rather than argued about
	// in advance.
	const NARROW_BREAKPOINT = 600;
	let containerWidth = $state(0);
	const narrow = $derived(
		containerWidth > 0 && containerWidth < NARROW_BREAKPOINT
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
	<div class="mixer" bind:clientWidth={containerWidth}>
		<button
			type="button"
			class="fullscreen-toggle"
			onclick={toggleFullscreen}
			aria-pressed={fullscreenActive}
			title={fullscreenActive ? "Exit full screen" : "Full screen"}
		>
			{fullscreenActive ? "\u2715 Exit full screen" : "\u26f6 Full screen"}
		</button>

		<Transport
			{layers}
			{playhead}
			bind:follow
			hasTimeline={timeline.length > 0}
			onClearSelection={clearSelection}
			onToggleRepeat={toggleRepeat}
		/>

		<PanelToggles
			hasTimeline={timeline.length > 0}
			hasNotes={notes.length > 0}
			hasDiagrams={Object.keys(diagrams.structure ?? {}).length > 0}
			{narrow}
		/>

		{#if panels.strip}
			<ChordStrip {timeline} {playhead} {follow} onSelectBar={selectBar} />
		{/if}

		{#if panels.phrases}
			<PhraseList {phrases} {playhead} onSelectPhrase={selectPhrase} {narrow} />
		{/if}

		{#if panels.notes}
			<NotesPanel {notes} {timeline} {phrases} {playhead} {narrow} />
		{/if}

		{#if panels.lyrics}
			<LyricsPanel {notes} {phrases} {playhead} />
		{/if}

		{#if panels.faders || panels.instruments}
			<div
				class="mixer-and-instruments"
				class:beside={instrumentsBesideMixer.value && panels.faders && panels.instruments}
				class:shrink={sideBySideLayout.value === "shrink" && !narrow}
			>
				{#if panels.faders}
					<div class="mixer-and-instruments-item">
						<FaderPanel {layers} onLevelChanged={levelChanged} />
					</div>
				{/if}

				{#if panels.instruments}
					<div class="mixer-and-instruments-item">
						<InstrumentPanel {diagrams} {timeline} {playhead} />
					</div>
				{/if}
			</div>
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
	.mixer-and-instruments {
		display: flex;
		flex-direction: column;
	}
	.mixer-and-instruments.beside {
		flex-direction: row;
		flex-wrap: wrap;
		gap: 16px;
		align-items: flex-start;
	}
	.mixer-and-instruments.beside .mixer-and-instruments-item {
		flex: 1 1 320px;
		min-width: 280px;
	}
	.mixer-and-instruments.beside.shrink {
		flex-wrap: nowrap;
	}
	.mixer-and-instruments.beside.shrink .mixer-and-instruments-item {
		flex: 1 1 0;
		min-width: 0;
	}
</style>