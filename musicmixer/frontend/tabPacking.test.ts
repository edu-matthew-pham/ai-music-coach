import { describe, expect, it } from "vitest";

import { groupByColumn, packByHeight } from "./tabPacking";

describe("packByHeight", () => {
	it("packs uniform lines exactly like the old count would have", () => {
		// 10 lines of 50px, 10px gap, 300px budget:
		// 50+10+50+10+50+10+50+10+50 = 290 -> 5 per column.
		const columnOf = packByHeight(Array(10).fill(50), 300, 10);
		expect(columnOf).toEqual([0, 0, 0, 0, 0, 1, 1, 1, 1, 1]);
	});

	it("gives a wrapped (taller) line its real cost, not an assumed one", () => {
		// The regression this replaces: one line wraps to
		// double height. The count-based budget ignored that
		// and overfilled the column; real heights must not.
		const heights = [50, 100, 50, 50, 50];
		const columnOf = packByHeight(heights, 220, 10);
		// 50+10+100 = 160, +10+50 = 220 fits exactly;
		// the next 50 must start column 1.
		expect(columnOf).toEqual([0, 0, 0, 1, 1]);
	});

	it("a line taller than the whole budget still lands, alone, visible", () => {
		const columnOf = packByHeight([50, 400, 50], 300, 10);
		expect(columnOf).toEqual([0, 1, 2]);
	});

	it("an oversized FIRST line does not create a leading empty column", () => {
		const columnOf = packByHeight([400, 50], 300, 10);
		expect(columnOf).toEqual([0, 1]);
	});

	it("counts the gap only between lines, not before the first", () => {
		// Two 145px lines with a 10px gap = 300 exactly: fits.
		expect(packByHeight([145, 145], 300, 10)).toEqual([0, 0]);
		// One pixel over: wraps.
		expect(packByHeight([145, 146], 300, 10)).toEqual([0, 1]);
	});

	it("returns an empty assignment for no lines", () => {
		expect(packByHeight([], 300, 10)).toEqual([]);
	});
});

describe("per-column reserve for the current line's inflation", () => {
	it("leaves room for the worst inflation among a column's OWN lines", () => {
		// Four 50px lines, 10px gaps, 240px budget: without
		// any reserve all four fit (50+10+50+10+50+10+50=230).
		expect(packByHeight(Array(4).fill(50), 240, 10)).toEqual([0, 0, 0, 0]);

		// Now line 3 grows by 40px when it is the line being
		// sung. Its own column must hold that, so the fourth
		// line moves on: 230 + 40 = 270 > 240.
		const currentHeights = [50, 50, 90, 50];
		expect(packByHeight(Array(4).fill(50), 240, 10, currentHeights))
			.toEqual([0, 0, 0, 1]);
	});

	it("does not charge a column for a different column's inflation", () => {
		// The big inflation is on line 4, which lands in
		// column 1 - column 0 keeps its three lines and is
		// not shrunk by a line it never holds.
		const heights = Array(6).fill(50);
		const currentHeights = [50, 50, 50, 200, 50, 50];
		const columnOf = packByHeight(heights, 190, 10, currentHeights);
		expect(columnOf[0]).toBe(0);
		expect(columnOf[1]).toBe(0);
		expect(columnOf[2]).toBe(0);
		expect(columnOf[3]).not.toBe(0);
	});

	it("treats a line with no recorded current height as not inflating", () => {
		// currentHeights shorter than heights - the missing
		// entries must not be read as a shrink or a NaN.
		expect(packByHeight(Array(4).fill(50), 240, 10, [50, 50]))
			.toEqual([0, 0, 0, 0]);
	});

	it("ignores a current height smaller than the normal one", () => {
		expect(packByHeight(Array(4).fill(50), 240, 10, [10, 10, 10, 10]))
			.toEqual([0, 0, 0, 0]);
	});
});

describe("groupByColumn", () => {
	it("groups items by their assigned column, preserving order", () => {
		expect(groupByColumn(["a", "b", "c", "d"], [0, 0, 1, 1]))
			.toEqual([["a", "b"], ["c", "d"]]);
	});
});
