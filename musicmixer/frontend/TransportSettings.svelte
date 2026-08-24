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

	// Conventional practice speeds, not a slider - one tap
	// beats dragging anything for the common case, and the
	// slider's own extra precision belongs in the Mix sheet
	// instead, set once between takes like a fader, not
	// fussed over mid-song. 100 is included so the current
	// speed is always visible, not just implied by nothing
	// being highlighted.
	const RATE_PRESETS = [0.5, 0.75, 1, 1.25, 1.5];

	// The Mix sheet's fine slider can land on a value none of
	// these five presets show (85%, say). Rather than leaving
	// the row looking like it disagrees with the actual speed
	// - nothing highlighted, no number visible anywhere in
	// this row - a small extra pill appears showing exactly
	// what is set. Only rendered when it's needed: an ordinary
	// preset match adds nothing here to keep the row as small
	// as it looks in the common case.
	const customRate = $derived(
		RATE_PRESETS.includes(engine.rate) ? null : engine.rate
	);

	interface Props {
		follow: boolean;
		hasTimeline: boolean;
		onClearSelection: () => void;
		onToggleRepeat: () => void;
		onMasterVolumeChanged: () => void;
		onRateChanged: (value: number) => void;
	}

	let {
		follow = $bindable(),
		hasTimeline,
		onClearSelection,
		onToggleRepeat,
		onMasterVolumeChanged,
		onRateChanged
	}: Props = $props();
</script>

<div class="transport-settings">
	<button onclick={onClearSelection}>Clear selection</button>
	<div class="speed-buttons" role="group" aria-label="Practice speed">
		<span class="speed-label">Speed</span>
		{#each RATE_PRESETS as preset (preset)}
			<button
				type="button"
				class="speed-button"
				class:chosen={engine.rate === preset}
				aria-pressed={engine.rate === preset}
				onclick={() => onRateChanged(preset)}
			>
				{Math.round(preset * 100)}%
			</button>
		{/each}
		{#if customRate !== null}
			<span class="speed-custom" aria-live="polite">
				{Math.round(customRate * 100)}%
			</span>
		{/if}
	</div>
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
		<label class="mixer-toggle repeat">
			<input
				type="checkbox"
				bind:checked={engine.repeat}
				onchange={onToggleRepeat}
			/>
			Repeat
		</label>
	{/if}
	<label class="mixer-toggle repeat">
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
		<label class="mixer-toggle repeat">
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
		<label class="mixer-toggle repeat">
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
	/* Base layout comes from .mixer-toggle (Index.svelte);
	   kept its own larger checkbox and font, and the fix
	   noted below, since those look like deliberate choices
	   for this row rather than accidental drift. */
	.repeat {
		font-size: 13px;
	}
	.repeat input[type="checkbox"] {
		/* Gradio's theme resets input appearance broadly
		   enough that a checked box drew no checkmark at all
		   - it wasn't disappearing, there was simply nothing
		   left to render once checked. Forced back on and
		   given an explicit colour rather than an inherited
		   one that might match its own background. */
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
	.speed-buttons {
		display: flex;
		align-items: center;
		gap: 3px;
		font-size: 12px;
	}
	.speed-label {
		margin-right: 1px;
	}
	.speed-button {
		padding: 0.1rem 0.35rem;
		border: 1px solid var(--border-color-primary, #ccc);
		border-radius: 999px;
		background: transparent;
		cursor: pointer;
		font-size: 10px;
	}
	.speed-custom {
		/* Not a button - nothing happens if you click it - so
		   it deliberately does not look like the presets
		   beside it: dashed border, no pointer cursor, and the
		   subdued colour the volume/text-size readouts already
		   use elsewhere in this row for "this is a number, not
		   a control". */
		padding: 0.1rem 0.35rem;
		border: 1px dashed var(--border-color-primary, #ccc);
		border-radius: 999px;
		font-size: 10px;
		color: var(--body-text-color-subdued);
	}
	.speed-button.chosen {
		background: var(--color-accent, #2e7d32);
		color: #fff;
		border-color: transparent;
	}
</style>