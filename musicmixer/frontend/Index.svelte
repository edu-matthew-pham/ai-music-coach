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
		previewSideBySide,
		partsSideBySide
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
	const phrasesByPart = $derived(gradio.props.value?.phrases_by_part ?? {});

	// The tunes of a several-tune song, and which one this
	// person is singing. Both come straight from Python;
	// an ordinary song sends an empty list, and everything
	// below that reads `parts.length` stays hidden.
	const parts = $derived(gradio.props.value?.parts ?? []);

	const singing = $derived(
		gradio.props.value?.part ?? (parts.length ? parts[0] : null)
	);
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
	const lyricsMode = $derived.by((): "paired" | "windowed" | "tab" | "singstar" | "parts" => {
		// An explicit choice, same standing as the view
		// presets below - only ever reachable when there is
		// more than one tune to show side by side, so turning
		// it on for one song and then loading a solo song
		// cannot silently strand the panel in a mode with
		// nothing to show.
		if (partsSideBySide.value && parts.length > 1) return "parts";
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
	// than fighting it.
	//
	// This used to fold the container-width check (!narrow)
	// into this same boolean, which is exactly the kind of
	// layout-in-JS the responsive-layout plan calls out - the
	// width part now lives in CSS instead (see
	// .lyrics-and-notes.singstar.preview-wide's @container
	// rule below). What's left here is pure feature state: is
	// the preview actually on and actually side-by-side. It is
	// NOT redundant with NotesPanel's own narrow-driven
	// disabling of that same toggle - previewSideBySide is a
	// persisted module-level value, so a person could enable
	// it while wide, then resize narrower without ever
	// touching the checkbox again, leaving it stuck true. The
	// CSS width gate is what actually protects against that
	// stale value at narrow width now, not this boolean.
	const singstarPreviewWide = $derived(
		viewPreset.value === "singstar" &&
			showNextPreview.value &&
			previewSideBySide.value
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

	// The practice speed, seeded the same moment. Unlike
	// loopFrom (which starts null and is only ever seeded
	// once), rate always has a real value, so there is no
	// "unset" state to guard on - setRate's own no-op guard
	// (see mixerEngine.svelte.ts) makes running this on
	// every remount safe regardless: build_mixer_fresh sends
	// 1.0 for a song that has just arrived (a real reset,
	// even mid-session), and build_mixer's carried value is
	// always what chooseRate below last wrote into this same
	// object, so re-seeding it is a harmless no-op.
	if (gradio.props.value?.rate != null) {
		engine.setRate(gradio.props.value.rate);
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

	// Picking another tune is a change of who is singing,
	// not of the music: every tune's sound and notes are
	// already here, so this only tells Python which one to
	// judge and which words to show. Nothing is rebuilt and
	// the engine keeps playing underneath.
	function chooseTune(name: string): void {
		if (gradio.props.value) {
			gradio.props.value.part = name;
		}
		gradio.dispatch("change");
	}

	// Setting the practice speed, the same shape as
	// chooseTune with one addition: engine.setRate() stops
	// playback on its own (a mid-note buffer swap is the
	// silent timing seam this engine has been burned by
	// before - see mixerEngine.svelte.ts), so a rate change
	// mid-song would otherwise leave the music dead until
	// Play is pressed again. Resuming here, the same
	// wasPlaying pattern selectBar already uses for a bar
	// click, turns that into a brief pause rather than a
	// silence someone has to notice and fix themselves.
	function chooseRate(value: number): void {
		const wasPlaying = engine.playing;
		engine.setRate(value);
		if (gradio.props.value) {
			gradio.props.value.rate = engine.rate;
		}
		gradio.dispatch("change");
		if (wasPlaying) {
			engine.play(layers);
		}
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
	<!-- Two elements, on purpose. mixer-container is the size
	     query container and holds the width measurement; .mixer
	     inside it holds the tokens and everything else. A container
	     query cannot style the container itself (measured, not
	     assumed - see the CSS below), so the tokens have to sit on
	     a child of the queried element or their band overrides
	     silently never apply. -->
	<div class="mixer-container" bind:clientWidth={containerWidth}>
	<div class="mixer" style="--read-scale: {readScale.value}">
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

			<!-- Which tune is yours, in a song made of several.
			     Folded into the same row as play/stop rather
			     than a row of its own - hidden entirely for an
			     ordinary song, where there is nothing to choose
			     between. Clicking one does not rebuild
			     anything: every tune is already loaded and
			     playing, so this only changes whose words show
			     and who gets judged. -->
			{#if parts.length > 1}
				<div class="part-chooser" role="group" aria-label="Your part">
					<span class="part-label">Singing</span>
					{#each parts as tune (tune)}
						<button
							type="button"
							class="part-button"
							class:chosen={tune === singing}
							aria-pressed={tune === singing}
							onclick={() => chooseTune(tune)}
						>
							{tune}
						</button>
					{/each}
					<label class="mixer-toggle parts-toggle">
						<input type="checkbox" bind:checked={partsSideBySide.value} />
						Show all parts
					</label>
				</div>
			{/if}
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
					<MixerModal {layers} onLevelChanged={levelChanged} onRateChanged={chooseRate} />
				{/if}
				<TransportSettings
					bind:follow
					hasTimeline={timeline.length > 0}
					onClearSelection={clearSelection}
					onToggleRepeat={toggleRepeat}
					onMasterVolumeChanged={masterVolumeChanged}
					onRateChanged={chooseRate}
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
				<div class="lyrics-and-notes singstar" class:preview-wide={singstarPreviewWide}>
					{#if panels.notes}
						<div class="notes-cell">
							<NotesPanel {notes} {timeline} {phrases} {playhead} {narrow} {singing} {parts} />
						</div>
					{/if}
					{#if panels.lyrics}
						<div class="lyrics-cell">
							<LyricsPanel {notes} {timeline} {phrases} {phrasesByPart} {playhead} mode={lyricsMode} {singing} {parts} />
						</div>
					{/if}
				</div>
			{:else}
				<div class="lyrics-and-notes">
					{#if panels.lyrics}
						<div class="lyrics-cell">
							<LyricsPanel {notes} {timeline} {phrases} {phrasesByPart} {playhead} mode={lyricsMode} {singing} {parts} />
						</div>
					{/if}
					{#if panels.notes}
						<div class="notes-cell">
							<NotesPanel {notes} {timeline} {phrases} {playhead} {narrow} {singing} {parts} />
						</div>
					{/if}
				</div>
			{/if}
		{/if}
	</div>
	</div>
</Block>

<style>
	/* Shared by every checkbox toggle across the mixer -
	   NotesPanel, LyricsPanel, TransportSettings, and the
	   parts toggle below - so the four copies that used to
	   exist can't quietly drift apart the way they had
	   (13px/11px font, 15px/12px box, 3px/4px gap). Global
	   because Svelte's scoped styles don't cross component
	   files; Index.svelte is always mounted, so this is
	   always available. Colour and box size stay a per-use
	   override where a panel wants its own accent, rather
	   than forced to one value here. */
	:global(.mixer-toggle) {
		font-size: 11px;
		color: var(--body-text-color-subdued);
		display: flex;
		align-items: center;
		gap: 3px;
		cursor: pointer;
	}
	:global(.mixer-toggle input[type="checkbox"]) {
		appearance: auto;
		width: 12px;
		height: 12px;
	}

	.mixer-container {
		/* The size query container. This is a SEPARATE element
		   from .mixer, and that separation is the whole point:
		   a @container rule cannot style the container element
		   itself - by spec, an element's own styles are not
		   allowed to depend on its own size, so the browser
		   silently ignores such a rule with no error. The
		   first version of this put container-type and the
		   tokens on the same .mixer element, and every
		   band-override rule (`@container ... { .mixer {...} }`)
		   did nothing at all - measured in headless Chromium
		   at 375px, not assumed: the narrow token stayed at
		   its wide value. Splitting the container onto this
		   wrapper makes .mixer a CHILD of the container, which
		   is the shape a query CAN style.
		   `inline-size` queries width only (not height), which
		   is all this component's layout ever needs. Named
		   "mixer" so a query says `@container mixer (...)`
		   explicitly rather than matching an anonymous nearest
		   ancestor.
		   width: 100% because inline-size containment stops
		   the box being sized from its content; without a
		   definite width from its parent it can shrink below
		   what's inside it. Also measured: 359px at a 375px
		   viewport with 8px body padding, i.e. exactly its
		   parent's content width, which is correct. */
		container-type: inline-size;
		container-name: mixer;
		width: 100%;
	}
	.mixer {
		font-family: sans-serif;
		position: relative;

		/* Spacing and text tokens, wide (default) values here,
		   narrower bands override below (the header rows are the
		   first consumers; stage 4 of the responsive-layout plan
		   sweeps the remaining hard-coded pixel sizes onto this
		   same set). Keep these three
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
		/* Was a fixed "8px 18px" - now the mixer's own spacing
		   tokens (declared on .mixer, adjusted per band by the
		   @container rules there), so every header row tightens
		   automatically at narrower widths instead of needing
		   its own copy of the same three numbers. */
		gap: var(--mixer-space-2) calc(var(--mixer-space-3) + 2px);
		margin-bottom: var(--mixer-space-1);
	}
	.header-transport {
		/* No wrapping cause to worry about - two buttons, every
		   width - but explicit anyway so a future addition here
		   inherits the same behaviour as the other two rows. */
		flex-wrap: wrap;
	}
	@container mixer (max-width: 599px) {
		.header-transport :global(.transport) {
			/* "Full-width transport on narrow" - Play/Pause and
			   Stop grow to share the row evenly rather than
			   sitting at their natural (small) width with empty
			   space beside them, which is what a phone-width
			   header otherwise leaves. Only at narrow: on medium
			   and wide the two buttons stay their natural size
			   next to everything else already on the row.
			   The stretching itself comes entirely from the
			   buttons' own `flex: 1 1 0` below - there used to
			   be a `justify-content: stretch` rule here too, on
			   the mistaken assumption it was doing some of the
			   work. It wasn't: `stretch` isn't a valid flexbox
			   value for justify-content (only for align-content/
			   align-self), so it was silently ignored by every
			   browser the whole time. Removed rather than left
			   as dead, misleading CSS. */
			width: 100%;
		}
		.header-transport :global(.transport button) {
			flex: 1 1 0;
		}
	}
	.header-views {
		justify-content: space-between;
	}
	.part-chooser {
		display: flex;
		gap: 0.4rem;
		align-items: center;
		flex-wrap: wrap;
	}

	.parts-toggle {
		margin-left: 0.6rem;
	}

	.part-label {
		font-size: 0.85rem;
		opacity: 0.7;
	}

	.part-button {
		padding: 0.25rem 0.7rem;
		border: 1px solid var(--border-color-primary, #ccc);
		border-radius: 999px;
		background: transparent;
		cursor: pointer;
		font-size: 0.9rem;
	}

	.part-button.chosen {
		background: var(--color-accent, #2e7d32);
		color: #fff;
		border-color: transparent;
	}

	.settings-toggle {
		font: inherit;
		font-size: var(--mixer-text-sm);
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
	/* NARROW_MAX below must match responsive.ts's own
	   NARROW_MAX (600) - see the note on .mixer's own
	   @container rules further up this file. */
	@container mixer (max-width: 599px) {
		.lyrics-and-notes {
			flex-direction: column;
		}
		.lyrics-and-notes .lyrics-cell,
		.lyrics-and-notes .notes-cell {
			min-width: 0;
		}
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
	.lyrics-and-notes.singstar.preview-wide {
		/* Notes' own "side by side" preview genuinely wants
		   the width back (two phrases' worth of pitch boxes
		   next to each other) - margins step aside for it
		   rather than squeezing it into the same 1200px cap
		   everything else defaults to. */
		max-width: none;
		margin: 0;
	}
	@container mixer (max-width: 599px) {
		.lyrics-and-notes.singstar.preview-wide {
			/* The width half of what used to be JS's !narrow
			   check (see singstarPreviewWide's own comment in
			   the script above) - even if the preview toggle is
			   stuck on from a wider session, don't let it push
			   the layout past the container at narrow width.
			   NotesPanel already disables the toggle itself at
			   this band, so this is a backstop for a stale
			   value, not the primary mechanism. */
			max-width: 1200px;
			margin: 0 auto;
		}
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
	.notes-cell {
		flex: 7 1 260px;
		min-width: 260px;
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