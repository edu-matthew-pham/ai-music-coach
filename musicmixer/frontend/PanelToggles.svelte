<script lang="ts">
	import {
		panels,
		instrumentsBesideMixer,
		sideBySideLayout
	} from "./mixerPanels.svelte";

	interface Props {
		hasTimeline: boolean;
		hasNotes: boolean;
		hasDiagrams: boolean;
		narrow?: boolean;
	}

	let { hasTimeline, hasNotes, hasDiagrams, narrow = false }: Props = $props();
</script>

<div class="panel-toggles">
	{#if hasTimeline}
		<label class="panel-toggle">
			<input type="checkbox" bind:checked={panels.strip} />
			Chart
		</label>
	{/if}
	{#if hasNotes}
		<label class="panel-toggle">
			<input type="checkbox" bind:checked={panels.phrases} />
			Phrases
		</label>
		<label class="panel-toggle">
			<input type="checkbox" bind:checked={panels.notes} />
			Visual notes
		</label>
		<label class="panel-toggle">
			<input type="checkbox" bind:checked={panels.lyrics} />
			Lyrics
		</label>
	{/if}
	<label class="panel-toggle">
		<input type="checkbox" bind:checked={panels.faders} />
		Mixer
	</label>
	{#if hasDiagrams}
		<label class="panel-toggle">
			<input type="checkbox" bind:checked={panels.instruments} />
			Instruments
		</label>
		<label class="panel-toggle">
			<input type="checkbox" bind:checked={instrumentsBesideMixer.value} />
			Beside mixer
		</label>
		{#if instrumentsBesideMixer.value}
			<label class="panel-toggle" class:disabled={narrow}>
				<input
					type="checkbox"
					checked={sideBySideLayout.value === "shrink"}
					disabled={narrow}
					onchange={(event) =>
						(sideBySideLayout.value = event.currentTarget.checked
							? "shrink"
							: "wrap")}
				/>
				Shrink to fit
			</label>
		{/if}
	{/if}
</div>
<style>
	.panel-toggles {
		display: flex;
		gap: 14px;
		margin-bottom: 8px;
	}
	.panel-toggle {
		font-size: 12px;
		color: var(--body-text-color-subdued);
		display: flex;
		align-items: center;
		gap: 4px;
		cursor: pointer;
	}
	.panel-toggle.disabled {
		opacity: 0.5;
		cursor: default;
	}
	.panel-toggle input[type="checkbox"] {
		appearance: auto;
		accent-color: #607d8b;
		width: 13px;
		height: 13px;
	}
</style>