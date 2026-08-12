<script lang="ts">
	// The whole test. No audio, no faders, no Gradio value
	// binding beyond what the template needs - just: does a
	// number in counter.svelte.ts survive this component
	// being torn down and rebuilt?
	import type { MusicMixerProps, MusicMixerEvents } from "./types";
	import { Gradio } from "@gradio/utils";
	import { Block } from "@gradio/atoms";
	import { onMount, onDestroy } from "svelte";
	import { counter, increment } from "./counter.svelte";

	const props = $props();
	const gradio = new Gradio<MusicMixerEvents, MusicMixerProps>(props);

	counter.mounts += 1;

	console.log("[test] MOUNTED", {
		mounts: counter.mounts,
		counter_value: counter.value
	});

	onDestroy(() => {
		console.log("[test] DESTROYED", {
			mounts: counter.mounts,
			counter_value: counter.value
		});
	});

	function bump(): void {
		increment();
		console.log("[test] bump ->", counter.value);

		// Also exercise the normal Gradio round trip, since
		// that is what has been triggering the remounts -
		// writing to value and dispatching change.
		if (gradio.props.value) {
			gradio.props.value.loop_start = counter.value;
		}
		gradio.dispatch("change");
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
	<div style="font-family: sans-serif; padding: 12px;">
		<p>
			Module counter: <strong>{counter.value}</strong>
			&nbsp;·&nbsp; This instance has mounted
			<strong>{counter.mounts}</strong> time(s) total.
		</p>
		<button onclick={bump}>Bump (dispatches change, like a real click)</button>
	</div>
</Block>