// targetNotes.test.ts
//
// Real unit-test coverage of a pure function, run via
// vitest. This used to also test run-length boundaries
// (a held run of 3 kept, 4 dropped, etc.) - that logic
// moved to Python (music.py:mark_unsung_holds) once it
// also needed to affect harmony and bass generation, not
// just this file. What's left here is only what this file
// still does: layer filtering, and reading the "*" mark
// Python now sends. The boundary logic itself has its own
// coverage on the Python side.

import { describe, expect, it } from "vitest";
import { targetNotes } from "./targetNotes";
import type { MixerNote } from "./types";

function note(
	start: number,
	layer: string,
	word?: string
): MixerNote {
	return { start, length: 1, midi: 60, layer, colour: "#000", word };
}

describe("targetNotes", () => {

	it("only ever keeps Melody-layer notes", () => {

		const notes = [
			note(0, "Melody", "sing"),
			note(1, "Harmony above", "sing"),
			note(2, "Harmony below", "sing"),
			note(3, "Bass"),
		];

		const kept = targetNotes(notes);

		expect(kept).toHaveLength(1);
		expect(kept[0].layer).toBe("Melody");
	});

	it("keeps a real word", () => {

		const notes = [note(0, "Melody", "word")];

		expect(targetNotes(notes)).toEqual(notes);
	});

	it("keeps a held note Python has confirmed as real singing", () => {

		const notes = [
			note(0, "Melody", "hold"),
			note(1, "Melody", "_"),
		];

		expect(targetNotes(notes)).toHaveLength(2);
	});

	it("drops a held note Python has marked as unconfirmed", () => {

		const notes = [
			note(0, "Melody", "hold"),
			note(1, "Melody", "*"),
			note(2, "Melody", "*"),
			note(3, "Melody", "next"),
		];

		const kept = targetNotes(notes).map((n) => n.word);

		expect(kept).toEqual(["hold", "next"]);
	});

	it("keeps every note when the piece has no lyrics at all", () => {

		const notes = [
			note(0, "Melody"),
			note(1, "Melody"),
			note(2, "Melody"),
		];

		// None of these are "*" - an undefined word is simply
		// not a lyric-bearing note, not an unconfirmed one.
		expect(targetNotes(notes)).toHaveLength(3);
	});

	it("a Bass or Harmony note marked * is still excluded by the layer filter alone", () => {

		// The "*" mark only ever appears on Melody in
		// practice (mixer_data.py never writes a word onto
		// Harmony/Bass), but the layer filter must not
		// depend on that - it should exclude non-Melody
		// notes regardless of their word field.
		const notes = [note(0, "Bass", "*")];

		expect(targetNotes(notes)).toHaveLength(0);
	});
});