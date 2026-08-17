<script lang="ts">
	import type { MusicMixerProps, MusicMixerEvents } from "./types";
	import type { MixerBar } from "./types";
	import type { MixerPhrase } from "./types";
	import { Gradio } from "@gradio/utils";
	import { Block } from "@gradio/atoms";
	import { onDestroy, onMount, setContext } from "svelte";
	import { engine } from "./mixerEngine.svelte";
	import { bandFor, SIZE_CONTEXT_KEY, type SizeContext } from "./responsive";
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
	import TransportSettings from "./TransportSettings.svelte";
	import SeekBar from "./SeekBar.svelte";
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

	// For the seek bar's range - the chart's own last bar end
	// when one exists (already the true song length in
	// seconds, chart or no chart underneath it makes no
	// difference to that number), the furthest note otherwise.
	// Same reduce pattern NotesPanel already uses per-phrase,
	// applied here to the whole song.
	const totalDuration = $derived(
		timeline.length > 0
			? timeline[timeline.length - 1].end
			: notes.reduce((max, note) => Math.max(max, note.start + note.length), 0)
	);

	// The component's own width, not the screen's - the
	// mixer can be narrow on a wide desktop (a small window,
	// a Gradio column sharing the row) just as easily as
	// on a phone, and it should respond to the room it is
	// actually given either way. Breakpoints now live in
	// responsive.ts, the one place NARROW_MAX/MEDIUM_MAX are
	// named for every file that needs them, rather than each
	// file keeping its own copy of the same numbers.
	let containerWidth = $state(0);
	const size = $derived(bandFor(containerWidth));
	const narrow = $derived(containerWidth > 0 && size === "narrow");

	// The one provider for the reactive size band - every
	// descendant component reads this via getContext instead
	// of being handed a `narrow` prop relayed down through
	// whatever sits between it and here. See responsive.ts's
	// own comment on why this is a getter, not a plain value.
	const sizeContext: SizeContext = {
		get band() {
			return size;
		}
	};
	setContext(SIZE_CONTEXT_KEY, sizeContext);

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

	// Whether the settings row (everything below the always-
	// visible transport/seek-bar/view-buttons rows) is open on
	// a narrow screen. Meaningless above the narrow breakpoint
	// - that row always renders there regardless of this value
	// - so it only needs to default closed for a first-time
	// phone visitor to see the minimal row, not a value that
	// needs to survive a remount the way panels/viewPreset do.
	let settingsOpen = $state(false);

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

	function togglePlay(): void {
		if (engine.playing) {
			engine.stop();
		} else {
			engine.play(layers);
		}
		playhead = engine.position();
	}

	function stopPlayback(): void {
		engine.stopAndRewind();
		playhead = engine.position();
	}

	// An ordinary scrubber, separate from the chart strip's
	// bar clicks - it only moves the playhead, never touches
	// loopFrom/loopTo. Reuses play()'s own `from` argument
	// (already how a preview click resumes mid-playback), so
	// no new engine method was needed for seeking itself, only
	// for the rewind-to-start Stop above.
	function seek(time: number): void {
		const clamped = Math.min(Math.max(time, 0), totalDuration);
		if (engine.playing) {
			engine.play(layers, clamped);
		} else {
			engine.offset = clamped;
		}
		playhead = clamped;
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

		<!-- The header used to be one flat wrapping row of
		     roughly twenty controls - fine on a desktop, a
		     wall of wrapped buttons on a phone, since nothing
		     grouped what mattered while playing separately
		     from what gets set up between takes. Now three
		     tiers: transport + seek bar (always visible, every
		     width - the minimum needed to use the app at all),
		     the three view buttons (also always visible, small
		     enough to never need folding), then everything else
		     behind a Settings toggle that only exists below the
		     narrow breakpoint - above it, that row just renders
		     open, unchanged from before. -->
		<div class="header-row header-transport">
			<Transport onTogglePlay={togglePlay} onStop={stopPlayback} />
		</div>

		<SeekBar {playhead} {totalDuration} {timeline} onSeek={seek} />

		<div class="header-row header-views">
			<div class="preset-buttons" role="group" aria-label="View">
				<button
					type="button"
					class="preset-button"
					aria-pressed={viewPreset.value === "tab"}
					onclick={() => applyPreset("tab", containerWidth)}
				>
					Tab view
				</button>
				<button
					type="button"
					class="preset-button"
					aria-pressed={viewPreset.value === "singstar"}
					onclick={() => applyPreset("singstar", containerWidth)}
				>
					SingStar view
				</button>
				<button
					type="button"
					class="preset-button"
					aria-pressed={viewPreset.value === "custom"}
					onclick={() => applyPreset("custom", containerWidth)}
				>
					Custom
				</button>
			</div>
			{#if narrow}
				<button
					type="button"
					class="settings-toggle"
					aria-expanded={settingsOpen}
					onclick={() => (settingsOpen = !settingsOpen)}
				>
					{settingsOpen ? "Hide settings" : "Settings"}
				</button>
			{/if}
		</div>

		{#if !narrow || settingsOpen}
			<div class="header-row header-settings">
				{#if viewPreset.value === "custom"}
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
				{/if}
				{#if panels.faders}
					<MixerModal {layers} onLevelChanged={levelChanged} />
				{/if}
				<TransportSettings
					bind:follow
					hasTimeline={timeline.length > 0}
					onClearSelection={clearSelection}
					onToggleRepeat={toggleRepeat}
					onMasterVolumeChanged={masterVolumeChanged}
				/>
				<button
					type="button"
					class="fullscreen-toggle-inline"
					onclick={toggleFullscreen}
					aria-pressed={fullscreenActive}
				>
					{fullscreenActive ? "\u2715 Exit full screen" : "\u26f6 Full screen"}
				</button>
			</div>
		{/if}

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

		/* Stage 1 of the responsive-layout plan: establishes
		   .mixer as a size query container so descendant CSS
		   can use @container instead of a JS `narrow` prop for
		   pure layout changes. `inline-size` queries width
		   only (not height), which is all this component's
		   layout ever needs. Named "mixer" so a query can say
		   `@container mixer (...)` explicitly rather than an
		   anonymous nearest-ancestor match - clearer at the
		   call site about which container is meant, useful if
		   a panel ever nests a second container of its own
		   later.
		   Containment note: inline-size containment also turns
		   on layout and style containment on this element. Not
		   expected to change anything here - .mixer has no
		   floats or margin-collapsing behaviour that reaches
		   outside it - but worth remembering as the first place
		   to look if something about .mixer's own box behaves
		   differently after this line, since containment is a
		   real behaviour change even though usually invisible. */
		container-type: inline-size;
		container-name: mixer;

		/* Spacing and text tokens, wide (default) values here,
		   narrower bands override below. Nothing reads these
		   yet - stage 1 only declares them, so this is a
		   verified no-op; stage 2 starts consuming them for the
		   header, and stage 4 sweeps the rest of the hard-coded
		   pixel sizes onto this same set. Keep these three
		   named steps rather than a continuous formula, for the
		   same reason the preset scale bands are discrete: a
		   number picked by looking at three real screens is
		   easier to check by eye than a computed curve. */
		--mixer-space-1: 4px;
		--mixer-space-2: 8px;
		--mixer-space-3: 16px;
		--mixer-text-sm: 12px;
		--mixer-text-base: 14px;
		--mixer-text-lg: 18px;
	}

	/* NARROW_MAX/MEDIUM_MAX below must match responsive.ts's
	   own NARROW_MAX (600) and MEDIUM_MAX (1100) exactly - CSS
	   cannot import the TS constant, so this is the one place
	   the two copies have to be kept in step by hand. */
	@container mixer (max-width: 599px) {
		.mixer {
			--mixer-space-1: 3px;
			--mixer-space-2: 6px;
			--mixer-space-3: 12px;
			--mixer-text-sm: 11px;
			--mixer-text-base: 13px;
			--mixer-text-lg: 16px;
		}
	}
	@container mixer (min-width: 600px) and (max-width: 1099px) {
		.mixer {
			/* medium's own numbers, listed explicitly rather
			   than left as an implied interpolation between
			   narrow and wide - a reader can see what medium
			   actually is without computing it by eye. */
			--mixer-space-1: 4px;
			--mixer-space-2: 7px;
			--mixer-space-3: 14px;
			--mixer-text-sm: 12px;
			--mixer-text-base: 13px;
			--mixer-text-lg: 17px;
		}
	}
	.fullscreen-toggle-inline {
		/* Was an absolutely-positioned corner button; now an
		   ordinary member of the settings row, which is what
		   let header-row drop the padding-right it used to
		   reserve for the old corner button. */
		font: inherit;
		font-size: 11px;
		padding: 4px 10px;
		border: 1px solid var(--border-color-primary);
		border-radius: 6px;
		background: var(--background-fill-primary);
		color: var(--body-text-color-subdued);
		cursor: pointer;
	}
	.fullscreen-toggle-inline:hover {
		background: var(--background-fill-secondary, #f5f5f5);
	}
	.header-row {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 8px 18px;
		margin-bottom: 6px;
	}
	.header-transport {
		/* No wrapping cause to worry about - two buttons, every
		   width - but explicit anyway so a future addition here
		   inherits the same behaviour as the other two rows. */
		flex-wrap: wrap;
	}
	.header-views {
		justify-content: space-between;
	}
	.settings-toggle {
		font: inherit;
		font-size: 12px;
		padding: 5px 12px;
		border: 1px solid var(--border-color-primary);
		border-radius: 6px;
		background: var(--background-fill-primary);
		color: var(--body-text-color-subdued);
		cursor: pointer;
	}
	.settings-toggle:hover {
		background: var(--background-fill-secondary, #f5f5f5);
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