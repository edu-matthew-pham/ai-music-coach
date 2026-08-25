// Pinned against the REAL This Love phrases_by_part output
// (exported by mixer_data from the actual uploaded file),
// which has two separate holes in Voice 2's own phrase
// list - an early one (before its first sung entry) and a
// later, mid-song one (73.3-96.0s) - the exact shape needed
// to catch a "only the first gap ever gets filled" bug.

import { describe, expect, it } from "vitest";

import { columnItems, currentPhraseIndex, type PhraseLike } from "./columnItems";
import fixtureData from "./this-love-parts.fixture.json";

const fixture = fixtureData as {
	phrasesByPart: Record<string, PhraseLike[]>;
	parts: string[];
};

const voice2 = fixture.phrasesByPart["Voice 2"];
const voice1 = fixture.phrasesByPart["Voice 1"];

describe("currentPhraseIndex", () => {
	it("finds the phrase the playhead is inside", () => {
		expect(currentPhraseIndex(voice2, 45)).toBe(3); // "this love has taken..."
	});

	it("finds the upcoming phrase when the playhead is in a hole", () => {
		// 30s sits in Voice 2's early hole (20.5-40.4).
		expect(currentPhraseIndex(voice2, 30)).toBe(3);
	});

	it("falls back to the last phrase once playhead is past everything", () => {
		expect(currentPhraseIndex(voice2, 999)).toBe(voice2.length - 1);
	});
});

describe("columnItems - Voice 2's real holes", () => {
	it("fills the early hole before Voice 2's first sung phrase", () => {
		const { items } = columnItems(voice2, 25);
		const gap = items.find((i) => i.kind === "gap");
		expect(gap).toBeDefined();
		expect(gap!.start).toBeCloseTo(20.5, 1);
		expect(gap!.end).toBeCloseTo(40.4, 1);
	});

	it("also fills the LATER, separate hole - not just the first one", () => {
		// Regression pin for exactly the shape of bug a
		// single-gap implementation would have: watching
		// past 73.3s, the 73.3-96.0s hole must still appear
		// as its own gap item, not be silently absent
		// because an earlier gap already got handled once.
		const { items } = columnItems(voice2, 85);
		const gaps = items.filter((i) => i.kind === "gap");
		expect(gaps.length).toBeGreaterThan(0);
		const midSongGap = gaps.find(
			(g) => g.kind === "gap" && Math.abs(g.start - 73.3) < 0.2
		);
		expect(midSongGap).toBeDefined();
	});

	it("orders gaps and phrases correctly across a full pass from the start", () => {
		const { items } = columnItems(voice2, 0);
		const kinds = items.map((i) => i.kind);
		// (rest), (rest), (rest) are real phrases (Voice 2's
		// own gap-pages from mixer_data), then a real hole,
		// then the first sung phrase.
		expect(kinds[0]).toBe("phrase");
		expect(kinds).toContain("gap");
		// Every item must be in non-decreasing time order.
		const starts = items.map((i) => i.start);
		for (let k = 1; k < starts.length; k++) {
			expect(starts[k]).toBeGreaterThanOrEqual(starts[k - 1] - 1e-6);
		}
	});

	it("never produces a zero-length or inverted gap", () => {
		for (const playhead of [0, 15, 25, 45, 65, 85, 100, 115, 999]) {
			const { items } = columnItems(voice2, playhead);
			for (const item of items) {
				if (item.kind === "gap") {
					expect(item.end).toBeGreaterThan(item.start);
				}
			}
		}
	});
});

describe("columnItems - a tune with no holes at all", () => {
	it("produces no gap items when the phrase list is already contiguous", () => {
		// Voice 1 covers the whole song with its own pages
		// (including its own rest pages) - no other-voice
		// hole should ever appear for it.
		const { items } = columnItems(voice1, 45);
		expect(items.every((i) => i.kind === "phrase")).toBe(true);
	});
});

describe("columnItems - edge cases", () => {
	it("returns nothing for an empty phrase list", () => {
		const { items, current } = columnItems([], 10);
		expect(items).toEqual([]);
		expect(current).toBeNull();
	});

	it("current always points at the phrase actually returned by currentPhraseIndex", () => {
		for (const playhead of [0, 25, 45, 85, 999]) {
			const { current } = columnItems(voice2, playhead);
			const expectedIndex = currentPhraseIndex(voice2, playhead);
			expect(current).toBe(
				expectedIndex >= 0 ? voice2[expectedIndex] : null
			);
		}
	});
});