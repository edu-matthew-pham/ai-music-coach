import { describe, expect, it } from "vitest";
import { noteSegments, overlappingPartners } from "./noteSegments";
import type { MixerNote } from "./types";

const PARTS = ["Voice 1", "Voice 2", "Voice 3"];

function note(layer: string, start: number, length: number, midi = 62, word?: string): MixerNote {
	return { layer, start, length, midi, colour: "#000", word };
}

describe("overlappingPartners", () => {
	it("is empty for a single-tune song", () => {
		const a = note("Melody", 0, 1);
		expect(overlappingPartners(a, [a, note("Melody", 0, 1)], [])).toEqual([]);
	});

	it("ignores the note itself and same-tune neighbours", () => {
		// An ordinary repeated note in one tune is not a
		// collision - it must draw as two plain boxes.
		const a = note("Voice 1", 0, 1);
		const b = note("Voice 1", 0, 1);
		expect(overlappingPartners(a, [a, b], PARTS)).toEqual([]);
	});

	it("ignores a different tune at a different pitch", () => {
		const a = note("Voice 1", 0, 1, 62);
		const b = note("Voice 2", 0, 1, 64);
		expect(overlappingPartners(a, [a, b], PARTS)).toEqual([]);
	});

	it("ignores a derived layer even at the same pitch", () => {
		// Harmony/bass are not "parts" - only sung tunes split.
		const a = note("Voice 1", 0, 1, 62);
		const h = note("Harmony above", 0, 1, 62);
		expect(overlappingPartners(a, [a, h], PARTS)).toEqual([]);
	});

	it("finds a different tune at the same pitch overlapping in time", () => {
		const a = note("Voice 1", 0, 2, 62);
		const b = note("Voice 2", 1, 1, 62);
		expect(overlappingPartners(a, [a, b], PARTS)).toEqual([b]);
	});

	it("does not count touching-but-not-overlapping notes", () => {
		const a = note("Voice 1", 0, 1, 62);
		const b = note("Voice 2", 1, 1, 62);
		expect(overlappingPartners(a, [a, b], PARTS)).toEqual([]);
	});
});

describe("noteSegments", () => {
	it("returns one full-height slice for a note with no partners", () => {
		const a = note("Voice 1", 0, 3);
		expect(noteSegments(a, [], PARTS)).toEqual([
			{ segStart: 0, segEnd: 3, bandIndex: 0, bandCount: 1 }
		]);
	});

	it("splits only the overlapping slice of a long note (partners fully inside)", () => {
		// The round's "dream." case: a held note with three
		// short syllables landing inside it. Full height before
		// the first arrives; split only while each is present.
		const dream = note("Voice 1", 0, 3);
		const partners = [
			note("Voice 2", 1.5, 0.5),
			note("Voice 2", 2.0, 0.5),
			note("Voice 2", 2.5, 0.5)
		];
		const segs = noteSegments(dream, partners, PARTS);
		expect(segs[0]).toEqual({ segStart: 0, segEnd: 1.5, bandIndex: 0, bandCount: 1 });
		for (const s of segs.slice(1)) {
			expect(s.bandCount).toBe(2);
			expect(s.bandIndex).toBe(0);
		}
		expect(segs.at(-1)!.segEnd).toBe(3);
	});

	it("handles a partner that straddles the note's START", () => {
		// Not covered by the round: a short note from another
		// tune that begins before this one and overlaps only
		// its opening. The split slice must begin at THIS
		// note's start (not before it), and full height must
		// resume once the partner has ended.
		const long = note("Voice 1", 2, 3);
		const early = note("Voice 2", 1, 2); // 1..3, overlaps 2..3
		const segs = noteSegments(long, [early], PARTS);
		expect(segs).toEqual([
			{ segStart: 2, segEnd: 3, bandIndex: 0, bandCount: 2 },
			{ segStart: 3, segEnd: 5, bandIndex: 0, bandCount: 1 }
		]);
	});

	it("handles a partner that straddles the note's END", () => {
		const long = note("Voice 1", 0, 3);
		const late = note("Voice 2", 2, 2); // 2..4, overlaps 2..3
		const segs = noteSegments(long, [late], PARTS);
		expect(segs).toEqual([
			{ segStart: 0, segEnd: 2, bandIndex: 0, bandCount: 1 },
			{ segStart: 2, segEnd: 3, bandIndex: 0, bandCount: 2 }
		]);
	});

	it("handles a partner that covers the note entirely", () => {
		// The short note is the one being drawn; the long one
		// spans right past both its edges. One slice, split.
		const short = note("Voice 2", 1, 1);
		const long = note("Voice 1", 0, 3);
		expect(noteSegments(short, [long], PARTS)).toEqual([
			{ segStart: 1, segEnd: 2, bandIndex: 1, bandCount: 2 }
		]);
	});

	it("keeps each tune in a stable band across slices", () => {
		// Voice 3 present for part of the note, Voice 2 for
		// another part: Voice 1 must stay in band 0 throughout,
		// and each partner in the band its part order gives it,
		// not whichever slot is free at the moment.
		const long = note("Voice 1", 0, 4);
		const v2 = note("Voice 2", 0, 2);
		const v3 = note("Voice 3", 3, 1);
		const segs = noteSegments(long, [v2, v3], PARTS);
		for (const s of segs) expect(s.bandIndex).toBe(0);
		// v3's own view of the same moment: it is band 1 (of 2)
		// since only Voice 1 and Voice 3 are present at 3..4.
		expect(noteSegments(v3, [long], PARTS)).toEqual([
			{ segStart: 3, segEnd: 4, bandIndex: 1, bandCount: 2 }
		]);
	});

	it("divides three ways when three tunes overlap at once", () => {
		const a = note("Voice 1", 0, 2);
		const b = note("Voice 2", 0, 2);
		const c = note("Voice 3", 0, 2);
		expect(noteSegments(a, [b, c], PARTS)).toEqual([
			{ segStart: 0, segEnd: 2, bandIndex: 0, bandCount: 3 }
		]);
		expect(noteSegments(c, [a, b], PARTS)[0].bandIndex).toBe(2);
	});
});
