<script lang="ts">
	import type { MusicMixerProps, MusicMixerEvents } from "./types";
	import type { MixerBarData } from "./mixerEngine.svelte";
	import { Gradio } from "@gradio/utils";
	import { Block } from "@gradio/atoms";
	import { onDestroy } from "svelte";
	import { engine } from "./mixerEngine.svelte";
	import { panels } from "./mixerPanels.svelte";
	import Transport from "./Transport.svelte";
	import PanelToggles from "./PanelToggles.svelte";
	import ChordStrip from "./ChordStrip.svelte";
	import FaderPanel from "./FaderPanel.svelte";
	import NotesPanel from "./NotesPanel.svelte";

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

	const props = $props();
	const gradio = new Gradio<MusicMixerEvents, MusicMixerProps>(props);

	const layers = $derived(gradio.props.value?.layers ?? []);
	const timeline = $derived(gradio.props.value?.timeline ?? []);
	const notes = $derived(gradio.props.value?.notes ?? []);
	const phrases = $derived(gradio.props.value?.phrases ?? []);

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

	function selectBar(bar: MixerBarData, event: MouseEvent | KeyboardEvent): void {
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
	<div class="mixer">
		<Transport
			{layers}
			{playhead}
			bind:follow
			hasTimeline={timeline.length > 0}
			onClearSelection={clearSelection}
			onToggleRepeat={toggleRepeat}
		/>

		<PanelToggles hasTimeline={timeline.length > 0} hasNotes={notes.length > 0} />

		{#if panels.strip}
			<ChordStrip {timeline} {playhead} {follow} onSelectBar={selectBar} />
		{/if}

		{#if panels.notes}
			<NotesPanel {notes} {timeline} {phrases} {playhead} />
		{/if}

		{#if panels.faders}
			<FaderPanel {layers} onLevelChanged={levelChanged} />
		{/if}
	</div>
</Block>

<style>
	.mixer {
		font-family: sans-serif;
	}
</style>