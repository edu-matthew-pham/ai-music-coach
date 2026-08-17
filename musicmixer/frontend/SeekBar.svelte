<script lang="ts">
	// An ordinary video-style scrubber - drag anywhere in the
	// song, no need to know what a bar is. Separate from
	// ChordStrip's bar clicks on purpose: that panel is for
	// musicians selecting a range to loop and is hidden in Tab
	// and SingStar; this is plain "take me here" navigation,
	// so it stays visible in every view, the same as Transport.
	// Dragging moves the playhead only - it never touches
	// loopFrom/loopTo, unlike a bar click, which can replace
	// the selection outright.
	//
	// Two units live here, in two places, and that's the point:
	// the ruler under the slider counts bars when a chart exists
	// (the music's own unit, per DESIGN.md invariant 11 - a
	// tempo change shows up as uneven tick spacing rather than
	// being hidden), and the readout at the right end is clock
	// time, because "how long is it" is a clock question. Same
	// split a DAW makes: ruler in bars, transport in minutes.
	import type { MixerBar } from "./types";

	interface Props {
		playhead: number;
		totalDuration: number;
		timeline: MixerBar[];
		onSeek: (time: number) => void;
	}

	let { playhead, totalDuration, timeline, onSeek }: Props = $props();

	// While the playhead is animating every frame via
	// requestAnimationFrame (see Index.svelte's tick()), that
	// same value feeding the slider would fight a live drag -
	// the thumb would visibly snap back toward wherever
	// playback actually is, a frame behind the finger. Track
	// the drag separately and only report the real playhead
	// when nobody is holding the slider.
	let dragging = $state(false);
	let dragValue = $state(0);

	const displayValue = $derived(dragging ? dragValue : playhead);
	const hasChart = $derived(timeline.length > 0);
	const span = $derived(Math.max(totalDuration, 0.1));

	function clock(seconds: number): string {
		const whole = Math.max(0, Math.floor(seconds));
		const m = Math.floor(whole / 60);
		const s = whole % 60;
		return `${m}:${s.toString().padStart(2, "0")}`;
	}

	// Bar and beat when a chart exists, seconds otherwise.
	// Beat is 1-based, matching how a chord chart is read.
	const positionLabel = $derived.by((): string => {
		if (!hasChart) return `${displayValue.toFixed(1)}s`;
		const bar =
			timeline.find((b) => displayValue >= b.start && displayValue < b.end) ??
			timeline[timeline.length - 1];
		const beat =
			Math.floor(((displayValue - bar.start) / (bar.end - bar.start)) * bar.beats) + 1;
		return `Bar ${bar.bar}, beat ${beat}`;
	});

	const clockLabel = $derived(`${clock(displayValue)} / ${clock(totalDuration)}`);

	// Ruler ticks. With a chart: one per bar at BAR_TICK_EVERY
	// (4 - the usual phrase length, so ticks land where the
	// music's own sections tend to start), numbered every
	// BAR_LABEL_EVERY (8) so the numbers don't crowd on a long
	// song. Bar 1 is always ticked and numbered so the ruler
	// has a visible origin. Without a chart: every 30s, numbered
	// every 60s - plain time, since there's no bar to count.
	const BAR_TICK_EVERY = 4;
	const BAR_LABEL_EVERY = 8;
	const TIME_TICK_EVERY = 30;
	const TIME_LABEL_EVERY = 60;

	interface Tick {
		at: number;
		label: string | null;
	}

	const ticks = $derived.by((): Tick[] => {
		if (hasChart) {
			return timeline
				.filter((b) => b.bar === 1 || b.bar % BAR_TICK_EVERY === 0)
				.map((b) => ({
					at: b.start,
					label:
						b.bar === 1 || b.bar % BAR_LABEL_EVERY === 0 ? String(b.bar) : null
				}));
		}
		const out: Tick[] = [];
		for (let t = 0; t < totalDuration; t += TIME_TICK_EVERY) {
			out.push({ at: t, label: t % TIME_LABEL_EVERY === 0 ? clock(t) : null });
		}
		return out;
	});

	function pct(seconds: number): number {
		return (seconds / span) * 100;
	}

	function handlePointerDown(): void {
		dragging = true;
		dragValue = playhead;
	}

	function handleInput(event: Event): void {
		dragValue = Number((event.target as HTMLInputElement).value);
	}

	function handleChange(event: Event): void {
		const value = Number((event.target as HTMLInputElement).value);
		dragging = false;
		onSeek(value);
	}
</script>

<div class="seek-bar">
	<div class="seek-track">
		<input
			type="range"
			class="seek-input"
			min="0"
			max={span}
			step="0.1"
			value={displayValue}
			onpointerdown={handlePointerDown}
			oninput={handleInput}
			onchange={handleChange}
			aria-label="Seek"
		/>
		<!-- The ruler sits under the slider, positioned in
		     percent of the same span the slider uses, so a tick
		     and the thumb agree on where any given second is.
		     Absolute positioning inside a relative track means
		     it costs no layout height beyond its own line. -->
		<div class="seek-ruler" aria-hidden="true">
			{#each ticks as tick (tick.at)}
				<div class="tick" class:labelled={tick.label !== null} style="left: {pct(tick.at)}%">
					{#if tick.label !== null}
						<span class="tick-label">{tick.label}</span>
					{/if}
				</div>
			{/each}
		</div>
	</div>
	<span class="seek-readout">
		<span class="seek-position">{positionLabel}</span>
		<span class="seek-sep">&middot;</span>
		<span class="seek-clock">{clockLabel}</span>
	</span>
</div>

<style>
	.seek-bar {
		display: flex;
		align-items: flex-start;
		gap: 10px;
		margin-bottom: 6px;
	}
	.seek-track {
		flex: 1;
		min-width: 0;
		position: relative;
		/* Room below the slider for the ruler's tick + label
		   line, so the row's own height is stable whether or
		   not any tick happens to carry a number. */
		padding-bottom: 16px;
	}
	.seek-input {
		width: 100%;
		display: block;
		margin: 0;
	}
	.seek-ruler {
		position: absolute;
		left: 0;
		right: 0;
		bottom: 0;
		height: 16px;
		pointer-events: none;
	}
	.tick {
		position: absolute;
		top: 0;
		width: 1px;
		height: 5px;
		background: var(--body-text-color-subdued);
		opacity: 0.6;
		/* Centre the 1px line on its exact position rather than
		   hanging it off the right of it. */
		transform: translateX(-0.5px);
	}
	.tick.labelled {
		height: 7px;
		opacity: 0.9;
	}
	.tick-label {
		position: absolute;
		top: 7px;
		left: 50%;
		transform: translateX(-50%);
		font-size: 10px;
		line-height: 1;
		color: var(--body-text-color-subdued);
		white-space: nowrap;
	}
	.seek-readout {
		font-size: 12px;
		color: var(--body-text-color-subdued);
		white-space: nowrap;
		display: flex;
		align-items: center;
		gap: 6px;
		/* Aligns the readout with the slider thumb's row, not
		   the ruler line under it. */
		padding-top: 2px;
	}
	.seek-position {
		min-width: 92px;
		text-align: right;
	}
	.seek-sep {
		opacity: 0.5;
	}
	.seek-clock {
		font-variant-numeric: tabular-nums;
	}
</style>