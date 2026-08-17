<script lang="ts">
	// Everything that used to live in Transport.svelte except
	// play/pause and stop - volume, Repeat, Mic, Record/
	// Download, Follow, Clear selection. Grouped separately so
	// Index.svelte can fold all of it behind one "Settings"
	// toggle on a narrow screen, while Transport's own two
	// buttons and the seek bar stay visible regardless of
	// width - these are the controls used while music plays,
	// those are set up between takes.
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
		follow: boolean;
		hasTimeline: boolean;
		onClearSelection: () => void;
		onToggleRepeat: () => void;
		onMasterVolumeChanged: () => void;
	}

	let {
		follow = $bindable(),
		hasTimeline,
		onClearSelection,
		onToggleRepeat,
		onMasterVolumeChanged
	}: Props = $props();
</script>

<div class="transport-settings">
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
	{#if hasTimeline}
		<label class="repeat">
			<input type="checkbox" bind:checked={follow} />
			Follow
		</label>
	{/if}
</div>

<style>
	.transport-settings {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 8px;
	}
	.transport-settings button {
		padding: 6px 14px;
		font-size: 13px;
		font-weight: 600;
		cursor: pointer;
	}
	.mic-note {
		font-size: 11px;
		color: var(--body-text-color-subdued);
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
