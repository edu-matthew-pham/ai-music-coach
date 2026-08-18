import { describe, expect, it } from "vitest";
import { assignLanes, type LabelInput } from "./labelLanes";

const opts = { lineHeight: 10, glyphWidth: 5, gap: 2 };

function place(labels: LabelInput[], extra = {}) {
	const out = assignLanes(labels, { ...opts, ...extra });
	return Object.fromEntries(out.map((p) => [p.id, p]));
}

describe("assignLanes", () => {
	it("leaves a lone label exactly where it asked to be", () => {
		const r = place([{ id: "a", x: 50, y: 100, text: "word", priority: 0 }]);
		expect(r.a.lane).toBe(0);
		expect(r.a.y).toBe(100);
	});

	it("leaves two labels far apart on the same line alone", () => {
		const r = place([
			{ id: "a", x: 20, y: 100, text: "one", priority: 0 },
			{ id: "b", x: 200, y: 100, text: "two", priority: 0 }
		]);
		expect(r.a.lane).toBe(0);
		expect(r.b.lane).toBe(0);
	});

	it("drops the second of two overlapping labels one line", () => {
		// The round's own case: two tunes' words at the same
		// pitch and moment - same y, overlapping x.
		const r = place([
			{ id: "dream", x: 100, y: 100, text: "dream.", priority: 0 },
			{ id: "mer", x: 104, y: 100, text: "mer-", priority: 1 }
		]);
		expect(r.dream.lane).toBe(0);
		expect(r.mer.lane).toBe(1);
		expect(r.mer.y).toBe(110);
	});

	it("handles labels under DIFFERENT pitches that still collide", () => {
		// A partner song: two tunes a few rows apart whose
		// labels, one row below each note, land on adjacent
		// lines but the lower note's label wants the line the
		// upper note's label already dropped into. Only the
		// text geometry matters, not which pitch each came from.
		const r = place([
			{ id: "upper", x: 100, y: 100, text: "how", priority: 0 },
			{ id: "upper2", x: 106, y: 100, text: "they", priority: 0 },
			{ id: "lower", x: 100, y: 110, text: "re", priority: 1 }
		]);
		// upper2 collides with upper on line 100 -> lane 1 (y 110)
		expect(r.upper2.lane).toBe(1);
		// lower asked for y 110, which upper2 now occupies -> drops
		expect(r.lower.lane).toBe(1);
		expect(r.lower.y).toBe(120);
	});

	it("does not treat labels on genuinely different lines as competing", () => {
		// Two labels asking for well-separated y's, overlapping in
		// x - fine, they are on different lines already.
		const r = place([
			{ id: "a", x: 100, y: 100, text: "one", priority: 0 },
			{ id: "b", x: 100, y: 130, text: "two", priority: 0 }
		]);
		expect(r.a.lane).toBe(0);
		expect(r.b.lane).toBe(0);
	});

	it("keeps the higher-priority label on the top line", () => {
		// "Your part's word goes first" - priority, not order
		// given, decides who keeps lane 0.
		const r = place([
			{ id: "other", x: 100, y: 100, text: "mer-", priority: 1 },
			{ id: "mine", x: 102, y: 100, text: "dream.", priority: 0 }
		]);
		expect(r.mine.lane).toBe(0);
		expect(r.other.lane).toBe(1);
	});

	it("puts three colliding labels on three distinct lines", () => {
		// Search alternates down, then up, so the third label
		// climbs rather than dropping two - tighter around the
		// note. The property that matters is three distinct
		// lines with the top-priority one on its own wanted line.
		const r = place([
			{ id: "a", x: 100, y: 100, text: "aaa", priority: 0 },
			{ id: "b", x: 100, y: 100, text: "bbb", priority: 1 },
			{ id: "c", x: 100, y: 100, text: "ccc", priority: 2 }
		]);
		expect(r.a.lane).toBe(0);
		expect(new Set([r.a.y, r.b.y, r.c.y]).size).toBe(3);
	});

	it("never places a label past the floor, and still separates them", () => {
		// The screenshot bug: a note at the very bottom of the
		// page has no room below it. Its overlapping partner
		// must still be visible AND not printed on top of it -
		// with no room down, it climbs instead.
		const r = place(
			[
				{ id: "dream", x: 100, y: 200, text: "dream.", priority: 0 },
				{ id: "mer", x: 104, y: 200, text: "mer-", priority: 1 }
			],
			{ floorY: 206 }
		);
		expect(r.dream.y).toBe(200);
		expect(r.mer.y).toBeLessThanOrEqual(206);
		expect(r.mer.y).not.toBe(r.dream.y);
	});

	it("pulls a label that asked for a y past the floor up onto it first", () => {
		// The exact real-page failure: both labels wanted y=210
		// on a page whose floor is 206. Both must land on-page,
		// and must not share a line.
		const r = place(
			[
				{ id: "dream", x: 250, y: 210, text: "dream.", priority: 0 },
				{ id: "mer", x: 264, y: 210, text: "mer-", priority: 2 }
			],
			{ floorY: 206 }
		);
		expect(r.dream.y).toBeLessThanOrEqual(206);
		expect(r.mer.y).toBeLessThanOrEqual(206);
		expect(r.mer.y).not.toBe(r.dream.y);
	});

	it("climbs when there is no room below", () => {
		const r = place(
			[
				{ id: "a", x: 100, y: 200, text: "aaa", priority: 0 },
				{ id: "b", x: 100, y: 200, text: "bbb", priority: 1 }
			],
			{ floorY: 200 }
		);
		expect(r.a.lane).toBe(0);
		expect(r.b.lane).toBe(-1);
		expect(r.b.y).toBe(190);
	});

	it("separates labels of a harmony a third away with no box collision", () => {
		// The case the round never produces: two tunes at
		// DIFFERENT pitches close enough that only their labels
		// crowd. Rows are 14px apart, labels sit 10px below
		// their row and are ~9px tall - so a label under row N
		// and one under row N-1 land 4px apart vertically with
		// overlapping x. No pitch is shared, no box is split;
		// only the text collides, and it must still be found.
		const r = place(
			[
				{ id: "melody", x: 100, y: 110, text: "life", priority: 0 },
				{ id: "third", x: 102, y: 124, text: "but", priority: 1 }
			],
			{ lineHeight: 9, glyphWidth: 5, gap: 2 }
		);
		expect(r.melody.y).toBe(110);
		// 124 is within one lineHeight of 110+9=119? No: 124-110=14
		// > 9*0.5, so they are NOT on the same line and both stay.
		// The real crowding case is when the offset makes them
		// land closer than half a line apart:
		const r2 = place(
			[
				{ id: "melody", x: 100, y: 110, text: "life", priority: 0 },
				{ id: "third", x: 102, y: 113, text: "but", priority: 1 }
			],
			{ lineHeight: 9, glyphWidth: 5, gap: 2 }
		);
		expect(r2.melody.y).toBe(110);
		expect(r2.third.y).not.toBe(113);
		expect(Math.abs(r2.third.y - r2.melody.y)).toBeGreaterThanOrEqual(9);
	});

	it("respects maxLanes rather than searching forever", () => {
		const labels: LabelInput[] = [];
		for (let i = 0; i < 10; i++) {
			labels.push({ id: `l${i}`, x: 100, y: 100, text: "same", priority: i });
		}
		const out = assignLanes(labels, { ...opts, maxLanes: 3 });
		for (const p of out) expect(Math.abs(p.lane)).toBeLessThan(3);
	});
});