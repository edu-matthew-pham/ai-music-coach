export interface MixerLayer {
	name: string;
	level: number;
	colour: string;
	wav: string;
}

export interface MixerBarChord {
	name: string;
	beat_in_bar: number;
	carried: boolean;
}

export interface MixerBar {
	bar: number;
	start: number;
	end: number;
	beats: number;
	chords: MixerBarChord[];
	words: string;
	key: string;
}

export interface MixerNote {
	start: number;
	length: number;
	midi: number;
	layer: string;
	colour: string;
	word?: string;
}

export interface MixerPhrase {
	start: number;
	end: number;
	label: string;
}

// Four layers per instrument, meant to be stacked: the
// always-there structure (keys/frets/strings, not a
// toggle - a picture of marks with nothing under them is
// illegible), the notes of every distinct key the piece
// actually uses (one chord-tones overlay per distinct chord
// the chart uses (every place it occurs), and one beginner
// shape per distinct chord (one concrete place to put the
// hand - missing for a chord this instrument has no
// standard shape for, in which case the panel falls back to
// the matching chords entry). Python guarantees all four
// share one coordinate system per instrument, so no size or
// offset is sent here.
//
// scale is keyed by musical key name first (most pieces use
// only one, so this is a one-entry object in the ordinary
// case), then by instrument - a modulating piece's Scale
// layer has to show the right key's notes on both sides of
// the change, not the opening key for the whole song. Which
// key applies at a given moment comes from that bar's own
// `key` field on the timeline, the same way its current
// chord already does.
export interface MixerDiagrams {
	structure: Record<string, string>;
	scale: Record<string, Record<string, string>>;
	chords: Record<string, Record<string, string>>;
	shapes: Record<string, Record<string, string>>;
}

export interface MixerValue {
	layers: MixerLayer[];
	timeline: MixerBar[];
	notes: MixerNote[];
	phrases: MixerPhrase[];
	diagrams: MixerDiagrams;
	loop_start: number | null;
	loop_end: number | null;
}

export interface MusicMixerProps {
	value: MixerValue;
}

export interface MusicMixerEvents {
	change: never;
	input: never;
}