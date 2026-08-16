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
	// Not bind:value - Svelte 5's bind writes the DOM's own
	// default back into state when the state is undefined
	// (bindings/input.js: `if (get() == null) set(...)`), and
	// a fresh range input's default is its midpoint. Since
	// engine.levels starts empty and Index seeds it in a
	// $effect (after mount), every fader was silently landing
	// on 0.5 before the opening levels could be applied, and
	// the "only if not yet set" guard then correctly left the
	// 0.5 alone. Reading the value with a fallback and
	// writing on input keeps the same behaviour with no
	// write-back path.
	function levelOf(layer: MixerLayerData): number {
		return engine.levels[layer.name] ?? layer.level;
	}

	function setFromInput(name: string, event: Event): void {
		engine.levels[name] = Number((event.currentTarget as HTMLInputElement).value);
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
				value={levelOf(layer)}
				oninput={(event) => setFromInput(layer.name, event)}
			/>
			<span class="value">
				{Math.round(levelOf(layer) * 100)}%
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