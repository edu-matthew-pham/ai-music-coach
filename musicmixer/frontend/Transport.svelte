<script lang="ts">
	// Row one, always visible at every width: play/pause and a
	// real stop. Everything else that used to live in this
	// component (volume, Mic, Follow, Clear selection, the old
	// elapsed-time readout) moved to TransportSettings.svelte,
	// which Index.svelte can fold away on a narrow screen -
	// this component never collapses, since these two buttons
	// plus the seek bar are the minimum needed to use the app
	// at all.
	//
	// The old elapsed-time readout ("48.3s") was dropped
	// entirely rather than moved - SeekBar's own readout
	// (position, elapsed/total) already covers it, and keeping
	// both was a duplicate, the same shape of redundancy Lyrics
	// and Notes' own word-label overlap was once flagged for.
	import { engine } from "./mixerEngine.svelte";

	interface Props {
		onTogglePlay: () => void;
		onStop: () => void;
	}

	let { onTogglePlay, onStop }: Props = $props();
</script>

<div class="transport">
	<button
		class="play-pause"
		onclick={onTogglePlay}
		aria-label={engine.playing ? "Pause" : "Play"}
	>
		{engine.playing ? "\u23f8" : "\u25b6"}
		{engine.playing ? "Pause" : "Play"}
	</button>
	<button onclick={onStop} aria-label="Stop">
		{"\u23f9"} Stop
	</button>
</div>

<style>
	.transport {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.transport button {
		padding: 6px 14px;
		font-size: 13px;
		font-weight: 600;
		cursor: pointer;
	}
</style>