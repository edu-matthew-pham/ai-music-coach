<script lang="ts">
	import { engine } from "./mixerEngine.svelte";
	import { mic } from "./micPitch.svelte";

	function toggleMic(event: Event): void {
		const wanted = (event.target as HTMLInputElement).checked;
		if (wanted) {
			mic.enable();
		} else {
			mic.disable();
		}
	}

	interface Props {
		playhead: number;
		follow: boolean;
		hasTimeline: boolean;
		onTogglePlay: () => void;
		onStop: () => void;
		onClearSelection: () => void;
		onToggleRepeat: () => void;
		onMasterVolumeChanged: () => void;
	}

	let {
		playhead,
		follow = $bindable(),
		hasTimeline,
		onTogglePlay,
		onStop,
		onClearSelection,
		onToggleRepeat,
		onMasterVolumeChanged
	}: Props = $props();
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
	<button onclick={onClearSelection}>Clear selection</button>
	<label class="volume">
		Volume
		<input
			type="range"
			min="0"
			max="1"
			step="0.05"
			bind:value={engine.masterVolume}
			oninput={onMasterVolumeChanged}
		/>
		<span class="value">
			{Math.round(engine.masterVolume * 100)}%
		</span>
	</label>
	{#if engine.loopFrom !== null && engine.loopTo !== null}
		<label class="repeat">
			<input
				type="checkbox"
				bind:checked={engine.repeat}
				onchange={onToggleRepeat}
			/>
			Repeat
		</label>
	{/if}
	<label class="repeat">
		<input
			type="checkbox"
			checked={mic.state === "on" || mic.state === "starting"}
			onchange={toggleMic}
		/>
		Mic
	</label>
	{#if mic.state === "denied"}
		<span class="mic-note">Mic blocked - allow it in the browser to see your pitch</span>
	{:else if mic.state === "error"}
		<span class="mic-note">Mic could not start</span>
	{:else if mic.state === "on"}
		<label class="repeat">
			<input type="checkbox" bind:checked={mic.recordingEnabled} />
			Record
		</label>
		{#if mic.recordingFrameCount > 0}
			<button onclick={() => mic.downloadRecording()}>
				Download recording
			</button>
		{/if}
	{/if}
	<span class="time">{playhead.toFixed(1)}s</span>
	{#if hasTimeline}
		<label class="repeat">
			<input type="checkbox" bind:checked={follow} />
			Follow
		</label>
	{/if}
</div>

<style>
	.transport {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-bottom: 6px;
	}
	.transport button {
		padding: 6px 14px;
		font-size: 13px;
		font-weight: 600;
		cursor: pointer;
	}
	.mic-note {
		font-size: 11px;
		color: var(--body-text-color-subdued);
	}
	.time {
		font-size: 12px;
		color: var(--body-text-color-subdued);
		margin-left: auto;
	}
	.repeat {
		font-size: 13px;
		display: flex;
		align-items: center;
		gap: 4px;
		cursor: pointer;
	}
	.repeat input[type="checkbox"] {
		/* Gradio's theme resets input appearance broadly
		   enough that a checked box drew no checkmark at all
		   - it wasn't disappearing, there was simply nothing
		   left to render once checked. Forced back on and
		   given an explicit colour rather than an inherited
		   one that might match its own background. */
		appearance: auto;
		accent-color: #2e7d32;
		width: 15px;
		height: 15px;
	}
	.volume {
		font-size: 13px;
		display: flex;
		align-items: center;
		gap: 4px;
	}
	.volume input[type="range"] {
		width: 90px;
	}
	.volume .value {
		width: 34px;
		font-size: 12px;
		color: var(--body-text-color-subdued);
		text-align: right;
	}
</style>