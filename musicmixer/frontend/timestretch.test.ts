// timestretch.test.ts
//
// Pins the stage-1 measurements (session-notes-timestretch-
// stage1.md) as regressions. Each test is one of the real
// failure shapes found there: transient duplication from the
// wrong sample rate, the unflushed tail, and the two things
// that must survive a stretch - pitch and click count.

import { describe, it, expect } from "vitest";
import { stretchSamples } from "./timestretch";

const SR = 8000;

// A click train like the app's own metronome: short loud
// ticks on a steady grid over silence. The signal that
// exposed the sample-rate trap - clicks either survive
// one-for-one at the new spacing, or WSOLA is misconfigured.
function clickTrain(clicks: number, spacingSeconds: number): Float32Array {
	const out = new Float32Array(Math.ceil(clicks * spacingSeconds * SR));
	const width = Math.floor(0.01 * SR);
	for (let c = 0; c < clicks; c++) {
		const at = Math.floor(c * spacingSeconds * SR);
		for (let i = 0; i < width; i++) out[at + i] = Math.sin(i * 1.2) * 0.9;
	}
	return out;
}

function onsets(x: Float32Array, threshold = 0.05): number[] {
	const found: number[] = [];
	const gap = Math.floor(0.05 * SR);
	let last = -gap;
	for (let i = 1; i < x.length; i++) {
		if (Math.abs(x[i]) > threshold && Math.abs(x[i - 1]) <= threshold) {
			if (i - last > gap) {
				found.push(i / SR);
				last = i;
			}
		}
	}
	return found;
}

function sine(frequency: number, seconds: number): Float32Array {
	const out = new Float32Array(Math.floor(seconds * SR));
	for (let i = 0; i < out.length; i++)
		out[i] = Math.sin((2 * Math.PI * frequency * i) / SR) * 0.5;
	return out;
}

// Dominant frequency by counting rising zero crossings -
// crude, but exact enough for "same note or not" on a clean
// sine, with no FFT dependency.
function dominantFrequency(x: Float32Array): number {
	let crossings = 0;
	for (let i = 1; i < x.length; i++) {
		if (x[i - 1] <= 0 && x[i] > 0) crossings++;
	}
	return crossings / (x.length / SR);
}

describe("stretchSamples", () => {
	it("output length is sample-exact (the unflushed-tail trap)", () => {
		const input = clickTrain(40, 0.25);
		expect(stretchSamples(input, 0.75, SR).length).toBe(
			Math.round(input.length / 0.75)
		);
		expect(stretchSamples(input, 1.5, SR).length).toBe(
			Math.round(input.length / 1.5)
		);
	});

	it("keeps every click, at the stretched spacing (the sample-rate trap)", () => {
		const input = clickTrain(40, 0.25);
		const out = stretchSamples(input, 0.75, SR);

		const found = onsets(out);
		// The misconfigured run produced ~35% EXTRA clicks at
		// the original spacing. Allow the tail-most click to
		// sit in rounding, nothing more.
		expect(found.length).toBeGreaterThanOrEqual(39);
		expect(found.length).toBeLessThanOrEqual(41);

		const spacings: number[] = [];
		for (let i = 1; i < found.length; i++)
			spacings.push(found[i] - found[i - 1]);
		spacings.sort((a, b) => a - b);
		const median = spacings[Math.floor(spacings.length / 2)];
		// 0.25s spacing at 75% speed is 0.333s; the wrong-rate
		// failure held the ORIGINAL 0.25s.
		expect(median).toBeGreaterThan(0.31);
		expect(median).toBeLessThan(0.36);
	});

	it("every click lands where songTime / tempo says, within WSOLA wobble", () => {
		const input = clickTrain(40, 0.25);
		const out = stretchSamples(input, 0.75, SR);
		const original = onsets(input);
		const stretched = onsets(out);
		const n = Math.min(original.length, stretched.length);
		for (let i = 0; i < n; i++) {
			// Stage 1 measured worst-case 38ms on real audio;
			// 60ms here leaves room for the synthetic signal
			// without letting a real misalignment through.
			expect(Math.abs(stretched[i] - original[i] / 0.75)).toBeLessThan(0.06);
		}
	});

	it("preserves pitch while changing duration", () => {
		const input = sine(220, 4);
		const out = stretchSamples(input, 0.75, SR);
		// Well under a semitone (220Hz -> 233Hz); the judging
		// threshold downstream is 50 cents.
		expect(Math.abs(dominantFrequency(out) - 220)).toBeLessThan(4);
	});
});
