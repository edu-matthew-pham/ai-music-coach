<script lang="ts">
	import { onMount } from "svelte";
	import { mixerOpen } from "./mixerPanels.svelte";
	import { engine } from "./mixerEngine.svelte";
	import FaderPanel from "./FaderPanel.svelte";
	import type { MixerLayerData } from "./mixerEngine.svelte";

	// The fader panel, floated over the page instead of laid
	// out in it. Levels are set between takes and then left
	// alone, so the faders do not earn a permanent slot; and
	// a panel that lives in the flow pushes whatever sits
	// under it (the instrument diagrams, most recently) down
	// the page every time it opens. A sheet over the top
	// moves nothing.
	//
	// The engine keeps playing underneath - it is
	// module-scoped and never remounts - so a fader can be
	// dragged mid-song and heard, the same as before. This
	// is a Svelte overlay inside the component for exactly
	// that reason: a Gradio-level dialog would round-trip
	// and remount the whole component around it.
	//
	// The button that opens it and the sheet itself live in
	// one file so the open/close pair cannot drift apart.
	// FaderPanel is reused unchanged - only where it renders
	// moved, not what it does.
	interface Props {
		layers: MixerLayerData[];
		onLevelChanged: (name: string) => void;
		onRateChanged: (value: number) => void;
	}

	let { layers, onLevelChanged, onRateChanged }: Props = $props();

	function open(): void {
		mixerOpen.value = true;
	}

	function close(): void {
		mixerOpen.value = false;
	}

	// Backdrop click and Escape both close it. On a shared
	// screen driven from across a room, a small close button
	// in one corner cannot be the only way out.
	onMount(() => {
		function handleEscape(event: KeyboardEvent): void {
			if (event.key === "Escape" && mixerOpen.value) close();
		}
		window.addEventListener("keydown", handleEscape);
		return () => window.removeEventListener("keydown", handleEscape);
	});
</script>

<button
	type="button"
	class="mix-button"
	onclick={open}
	aria-expanded={mixerOpen.value}
	aria-haspopup="dialog"
	aria-label="Open the mixer"
	title="Open the mixer"
>
	<span class="mix-icon" aria-hidden="true">&#9776;</span>
	<span class="mix-label">Mix</span>
</button>

{#if mixerOpen.value}
	<div
		class="mixer-backdrop"
		onclick={close}
		onkeydown={(event) => {
			if (event.key === "Enter" || event.key === " ") close();
		}}
		role="presentation"
	>
		<div
			class="mixer-sheet"
			role="dialog"
			aria-label="Mixer"
			aria-modal="true"
			tabindex="-1"
			onclick={(event) => event.stopPropagation()}
			onkeydown={(event) => event.stopPropagation()}
		>
			<div class="mixer-sheet-head">
				<span class="mixer-sheet-title">Mixer</span>
				<button type="button" class="mixer-close" onclick={close} aria-label="Close mixer">
					&#10005;
				</button>
			</div>
			<label class="rate-slider">
				Speed
				<input
					type="range"
					min="0.5"
					max="1.5"
					step="0.05"
					value={engine.rate}
					oninput={(event) =>
						onRateChanged(Number((event.target as HTMLInputElement).value))}
				/>
				<span class="value">{Math.round(engine.rate * 100)}%</span>
			</label>
			<FaderPanel {layers} {onLevelChanged} />
		</div>
	</div>
{/if}

<style>
	.mix-button {
		/* Sized to sit inline in the header row alongside
		   Transport and PanelToggles - it lived beside a
		   full-height Lyrics panel before, which called for
		   a squarer 52px button; now it is one control among
		   several text-sized ones. */
		font: inherit;
		display: flex;
		align-items: center;
		gap: 4px;
		padding: 5px 10px;
		border: 1px solid var(--border-color-primary);
		border-radius: 8px;
		background: var(--background-fill-primary);
		color: var(--body-text-color-subdued);
		cursor: pointer;
	}
	.mix-button:hover {
		background: var(--background-fill-secondary, #f5f5f5);
	}
	.mix-icon {
		font-size: 16px;
	}
	.mix-label {
		font-size: 11px;
	}
	.mixer-backdrop {
		/* fixed to the viewport, which is also right inside
		   main.py's fullscreen-mode wrapper - that wrapper is
		   itself position: fixed, so this covers it either
		   way. */
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.45);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 100;
	}
	.mixer-sheet {
		width: min(520px, calc(100vw - 32px));
		background: var(--background-fill-primary, #fff);
		border: 1px solid var(--border-color-primary);
		border-radius: 12px;
		padding: 14px 18px 18px;
	}
	.mixer-sheet-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 8px;
	}
	.mixer-sheet-title {
		font-size: 14px;
		font-weight: 600;
	}
	.mixer-close {
		font: inherit;
		font-size: 14px;
		width: 30px;
		height: 30px;
		border: 1px solid var(--border-color-primary);
		border-radius: 6px;
		background: var(--background-fill-primary);
		cursor: pointer;
	}
	.rate-slider {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 13px;
		margin-bottom: 10px;
	}
	.rate-slider input[type="range"] {
		flex: 1;
	}
	.rate-slider .value {
		width: 34px;
		font-size: 12px;
		color: var(--body-text-color-subdued);
		text-align: right;
	}
</style>