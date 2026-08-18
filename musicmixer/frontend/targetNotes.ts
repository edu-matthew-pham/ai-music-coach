// targetNotes.ts
//
// Which notes real-time judging compares a live pitch
// trace against.
//
// This is specifically for vocal practice - the only mode
// that exists today. An instrumental-practice mode (playing
// a part on violin, say, rather than singing it) is parked,
// not built (see the project's parked-proposal note). When
// it exists, it takes the score as written, unfiltered - the
// "*" exclusion below is not something to apply there. So
// this file is written as "vocal-judging mode, always" on
// purpose, not "does this piece happen to have lyrics" -
// those are different questions, and conflating them would
// wrongly apply vocal filtering to a piece someone picked up
// to play on an instrument, lyrics or not.
//
// The classification itself - which held notes are a real,
// confirmed melisma versus an unlyriced gap, almost always
// instrumental - is computed once, in Python
// (music.py:mark_unsung_holds), and arrives already decided:
// an unconfirmed hold's word is "*" instead of "_". This
// file used to re-derive that from run-lengths of its own;
// now it just reads the mark. One rule, one place - the same
// mark also decides which notes harmony and bass leave out,
// so the judging target and the accompaniment can never
// silently disagree about which notes are sung.
//
// mixer_data.py already sends every layer's notes tagged
// with which layer they belong to, and its own docstring
// already states the rule this reads: only Melody carries
// the sung words - the generated harmony and bass lines are
// derived voices, not independently sung parts, so nothing
// in them is ever the target for a live singer.
//
// This is deliberately separate from mixerPanels.svelte.ts's
// noteLayers toggle: which layers are drawn on screen and
// which layer is being judged against are two different
// questions, and hiding the Melody boxes to declutter the
// view must not silently stop judging. So this reads the
// raw notes list straight from Python, not the visibility
// toggles.
//
// A pure function, not module-scoped state - there is
// nothing here that needs to survive a remount, since it is
// recomputed straight from whatever notes the component was
// last given.

import type { MixerNote } from "./types";

// Which layer is the one being sung. An ordinary song has
// a single sung line, always called "Melody"; a song with
// several tunes in it names them itself and reports which
// one the person picked, so the target follows that choice
// rather than a name fixed here. Falling back to "Melody"
// keeps every ordinary song judging exactly as before.
const DEFAULT_TARGET_LAYER = "Melody";

// What Python marks a held note as once a run of them stops
// reading as a real, confirmed melisma - see
// mark_unsung_holds in music.py for the actual rule and why
// it lives there rather than here.
const UNSUNG_HOLD = "*";

export function targetNotes(
	notes: MixerNote[],
	part?: string | null
): MixerNote[] {

	const target = part || DEFAULT_TARGET_LAYER;

	return notes.filter(
		(note) => note.layer === target && note.word !== UNSUNG_HOLD
	);
}