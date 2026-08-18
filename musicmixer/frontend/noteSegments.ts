// Split-box slicing for the Notes panel.
//
// Two DIFFERENT sung tunes landing on the same pitch at
// overlapping times - the exact shape a partner song's
// harmonised moments produce, or a short syllable of one
// tune briefly grazing a long held note of another - need
// a way to tell the two apart rather than one box winning
// by drawing last. Same idea as the violin's split-position
// marks, but sliced by TIME, not by whole note: a first
// version grouped any two notes that ever overlap and
// squashed BOTH to a shared height for their ENTIRE duration,
// which meant a three-beat held note ("dream.") collapsed to
// a quarter of its row for its whole length just because a
// few short eighth notes from an unrelated phrase happened to
// touch the same pitch for an instant - the short notes' own
// words became unreadably thin at the same time. Real bug,
// found from a real screenshot, not guessed at. Each note now
// computes its own segments: full height everywhere nothing
// else is sounding at its pitch, split height only for the
// specific slice of time another tune's note is actually
// there too.
//
// Deliberately cross-tune only: two consecutive notes of the
// SAME tune sitting on the same pitch (an ordinary repeated
// note) are not a collision and must render as two separate,
// ordinary boxes.
//
// Pure functions, no Svelte, no DOM - lifted out of
// NotesPanel.svelte so the slicing can be tested on its own
// with synthetic notes, the same way labelLanes.ts is. The
// panel supplies the notes and which layers count as sung
// tunes; nothing here knows what a pitch row is in pixels.

import type { MixerNote } from "./types";

export interface NoteSegment {
	segStart: number;
	segEnd: number;
	// Which horizontal band of the row this slice draws in,
	// and how many bands the row is divided into for it.
	// bandCount 1 is an ordinary, full-height box.
	bandIndex: number;
	bandCount: number;
}

// The other tunes' notes that share this note's pitch and
// overlap it in time. Empty for anything that isn't a sung
// tune, or when the song has only one tune, so the ordinary
// case pays nothing.
export function overlappingPartners(
	note: MixerNote,
	pageNotes: MixerNote[],
	parts: string[]
): MixerNote[] {
	if (parts.length < 2 || !parts.includes(note.layer)) return [];

	return pageNotes.filter(
		(other) =>
			other !== note &&
			other.layer !== note.layer &&
			parts.includes(other.layer) &&
			other.midi === note.midi &&
			other.start < note.start + note.length &&
			other.start + other.length > note.start
	);
}

// The note's own span cut into slices, each with a fixed set
// of who else is sounding at that pitch during it. A note with
// no partners is one full-height slice.
export function noteSegments(
	note: MixerNote,
	partners: MixerNote[],
	parts: string[]
): NoteSegment[] {
	const noteEnd = note.start + note.length;

	if (!partners.length) {
		return [{ segStart: note.start, segEnd: noteEnd, bandIndex: 0, bandCount: 1 }];
	}

	// Break the note's own span at every point a partner
	// starts or ends within it - each resulting slice has a
	// fixed, unambiguous set of who else is sounding.
	const points = new Set<number>([note.start, noteEnd]);

	for (const partner of partners) {
		const partnerEnd = partner.start + partner.length;
		if (partner.start > note.start && partner.start < noteEnd) {
			points.add(partner.start);
		}
		if (partnerEnd > note.start && partnerEnd < noteEnd) {
			points.add(partnerEnd);
		}
	}

	const bounds = Array.from(points).sort((a, b) => a - b);
	const segments: NoteSegment[] = [];

	for (let i = 0; i < bounds.length - 1; i++) {

		const segStart = bounds[i];
		const segEnd = bounds[i + 1];
		const midpoint = (segStart + segEnd) / 2;

		const active = partners.filter(
			(partner) => partner.start <= midpoint && partner.start + partner.length > midpoint
		);

		// A stable band order (by position in `parts`, the same
		// order the part chooser and the tune layers already
		// use) so the same tune always draws in the same band
		// whenever it is present, rather than jumping around
		// slice to slice.
		const present = [note, ...active].sort(
			(a, b) => parts.indexOf(a.layer) - parts.indexOf(b.layer)
		);

		segments.push({
			segStart,
			segEnd,
			bandIndex: present.indexOf(note),
			bandCount: present.length
		});
	}

	return segments;
}
