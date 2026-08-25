// The chord-display rules, pinned against the REAL Mulan
// timeline (exported by mixer_data from the actual fixture
// file, not hand-invented bars). Mulan is the song that
// motivated the syncopation rules: chords land half a beat
// before the bar line in over twenty bars.

import { describe, expect, it } from "vitest";

import {
	allEvents,
	chordEvents,
	inCurrentBar,
	isSounding,
	soundingChordTime,
	chordTime
} from "./chordEvents";
import type { MixerBar } from "./types";
import fixtureData from "./mulan-timeline.fixture.json";

const fixture = fixtureData as {
	timeline: MixerBar[];
	phrases: { start: number; end: number; label: string }[];
};

const timeline = fixture.timeline;
const wholeSong = { start: 0, end: timeline[timeline.length - 1].end };

const bar = (n: number) => timeline[n - 1];

// Mulan bar 3 holds the motivating case: G lands at beat
// 3.5, and bar 4 opens with its carried repeat.
const syncopatedG = () => {
	const source = bar(3).chords.find(
		(c) => c.name === "G" && !c.carried
	)!;
	return chordTime(bar(3), source);
};

describe("printing", () => {
	it("prints carried chords faded instead of dropping them", () => {
		const events = chordEvents(timeline, wholeSong);
		expect(events.some((e) => e.type === "chord" && e.carried)).toBe(true);
	});

	it("suppresses the carried repeat right after a syncopation", () => {
		// Bar 4 opens with G carried, half a beat after the
		// real G - that repeat must not print.
		const events = chordEvents(timeline, wholeSong);
		const inBar4 = events.filter(
			(e) => e.type === "chord" && e.barStart >= bar(4).start - 1e-9
				&& e.time < bar(4).end && e.time >= bar(4).start
		);
		expect(inBar4.map((e) => e.type === "chord" && e.carried)).not.toContain(true);
	});

	it("still prints a genuinely held chord's repeat", () => {
		// Bar 1 opens Em (real, beat 0). Bar 2 carries it a
		// FULL BAR later, at its own beat 0 - nowhere near a
		// syncopation, and must print, faded.
		const events = chordEvents(timeline, wholeSong);
		const em = events.find(
			(e) => e.type === "chord" && e.carried && e.name === "Em"
			&& Math.abs(e.time - bar(2).start) < 1e-6
		);
		expect(em).toBeDefined();
	});

	it("keeps a genuinely held repeat's own bar span, not extended", () => {
		// Bar 2's carried Em is printed on its own terms -
		// its barEnd must stay bar 2's own end, unlike the
		// syncopated case where the REAL chord's span grows
		// to swallow the next bar.
		const events = chordEvents(timeline, wholeSong);
		const em = events.find(
			(e) => e.type === "chord" && e.carried && e.name === "Em"
			&& Math.abs(e.time - bar(2).start) < 1e-6
		)!;
		expect(em.barEnd).toBeCloseTo(bar(2).end, 6);
	});
});

describe("bar adoption of a syncopated chord", () => {
	it("extends the syncopated chord's bar span over the adopting bar", () => {
		const events = chordEvents(timeline, wholeSong);
		const g = events.find(
			(e) => e.type === "chord" && Math.abs(e.time - syncopatedG()) < 1e-9
		)!;
		expect(g.barEnd).toBeCloseTo(bar(4).end, 6);
	});

	it("keeps the chord bar-highlighted while the playhead is in the adopting bar", () => {
		const events = chordEvents(timeline, wholeSong);
		const g = events.find(
			(e) => e.type === "chord" && Math.abs(e.time - syncopatedG()) < 1e-9
		)!;
		const midBar4 = (bar(4).start + bar(4).end) / 2;
		expect(inCurrentBar(g, midBar4)).toBe(true);
	});

	it("adopts across a phrase boundary: the real chord in one line, the repeat in the next", () => {
		// Split the song at bar 4's start - the syncopated G
		// lives in the first window, its suppressed repeat
		// in the second. The extension must still land.
		const firstLine = { start: 0, end: bar(4).start };
		const events = chordEvents(timeline, firstLine);
		const g = events.find(
			(e) => e.type === "chord" && Math.abs(e.time - syncopatedG()) < 1e-9
		)!;
		expect(g.barEnd).toBeCloseTo(bar(4).end, 6);
	});
});

describe("the ring (sounding chord)", () => {
	it("stays on the syncopated chord through the adopting bar", () => {
		const midBar4Opening = bar(4).start + 0.1;
		const sounding = soundingChordTime(timeline, midBar4Opening);
		expect(sounding).toBeCloseTo(syncopatedG(), 6);
	});

	it("never points at a suppressed, invisible repeat", () => {
		// At every probe point across the first 8 bars, the
		// sounding time must correspond to an event that
		// chordEvents actually returns.
		const events = allEvents(timeline, wholeSong);
		for (let t = 0.05; t < bar(8).end; t += 0.25) {
			const sounding = soundingChordTime(timeline, t);
			if (sounding === null) continue;
			const visible = events.some((e) => isSounding(e, sounding));
			expect(visible, `at t=${t.toFixed(2)}s`).toBe(true);
		}
	});

	it("travels to a held chord's printed faded repeat", () => {
		// Bar 2's carried Em (printed, not suppressed) - the
		// ring must move onto it once its own time arrives,
		// not stay pinned to bar 1's original onset.
		const emRepeat = bar(2).start;
		const sounding = soundingChordTime(timeline, emRepeat + 0.01);
		expect(sounding).toBeCloseTo(emRepeat, 6);
	});

	it("moves to the next real chord when it arrives", () => {
		const d = bar(4).chords.find((c) => c.name === "D" && !c.carried)!;
		const dTime = chordTime(bar(4), d);
		const sounding = soundingChordTime(timeline, dTime + 0.01);
		expect(sounding).toBeCloseTo(dTime, 6);
	});
});