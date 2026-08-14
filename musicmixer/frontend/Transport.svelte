<script lang="ts">
	import { engine } from "./mixerEngine.svelte";
	import { mic } from "./micPitch.svelte";
	import type { MixerLayerData } from "./mixerEngine.svelte";

	function toggleMic(event: Event): void {
		const wanted = (event.target as HTMLInputElement).checked;
		if (wanted) {
			mic.enable();
		} else {
			mic.disable();
		}
	}

	interface Props {
		layers: MixerLayerData[];
		playhead: number;
		follow: boolean;
		hasTimeline: boolean;
		onClearSelection: () => void;
		onToggleRepeat: () => void;
	}

	let {
		layers,
		playhead,
		follow = $bindable(),
		hasTimeline,
		onClearSelection,
		onToggleRepeat
	}: Props = $props();
</script>

<div class="transport">
	<button onclick={() => engine.play(layers)}>Play</button>
	<button onclick={() => engine.stop()}>Stop</button>
	<button onclick={onClearSelection}>Clear selection</button>
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
		<!-- TEMPORARY DEBUG - see micPitch.svelte.ts. Downloads
		     a WAV of the exact raw signal the detector sees,
		     for comparing the live capture path against a file
		     recorded outside the browser. -->
		<button
			onclick={() => mic.debugStartRecording(5)}
			disabled={mic.debugRecording}
		>
			{mic.debugRecording ? "Recording..." : "Record 5s (debug)"}
		</button>
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
</style>