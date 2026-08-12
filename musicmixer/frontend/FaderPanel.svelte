<script lang="ts">
	import { engine } from "./mixerEngine.svelte";
	import type { MixerLayerData } from "./mixerEngine.svelte";

	interface Props {
		layers: MixerLayerData[];
		onLevelChanged: (name: string) => void;
	}

	let { layers, onLevelChanged }: Props = $props();

	function toggleMute(name: string, opening: number): void {
		engine.levels[name] = engine.levels[name] > 0 ? 0 : opening;
		onLevelChanged(name);
	}
</script>

<div class="faders">
	{#each layers as layer (layer.name)}
		<div class="fader-row">
			<span class="name" style="color:{layer.colour}">
				{layer.name}
			</span>
			<button class="mute" onclick={() => toggleMute(layer.name, layer.level)}>
				M
			</button>
			<input
				type="range"
				min="0"
				max="1"
				step="0.05"
				bind:value={engine.levels[layer.name]}
				oninput={() => onLevelChanged(layer.name)}
			/>
			<span class="value">
				{Math.round((engine.levels[layer.name] ?? 0) * 100)}%
			</span>
		</div>
	{/each}
</div>

<style>
	.fader-row {
		display: flex;
		align-items: center;
		gap: 12px;
		margin: 6px 0;
	}
	.name {
		width: 120px;
		font-size: 13px;
		font-weight: 600;
	}
	.mute {
		width: 30px;
		padding: 4px 0;
		font-size: 13px;
		cursor: pointer;
	}
	input[type="range"] {
		flex: 1;
		max-width: 320px;
	}
	.value {
		width: 38px;
		font-size: 12px;
		color: var(--body-text-color-subdued);
		text-align: right;
	}
</style>
