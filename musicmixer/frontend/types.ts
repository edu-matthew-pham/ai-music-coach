export interface MixerLayer {
	name: string;
	level: number;
	colour: string;
	wav: string;
}

export interface MixerBar {
	bar: number;
	name: string;
	start: number;
	end: number;
	words: string;
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
// illegible), the key's scale, one chord-tones overlay per
// distinct chord the chart uses (every place it occurs),
// and one beginner shape per distinct chord (one concrete
// place to put the hand - missing for a chord this
// instrument has no standard shape for, in which case the
// panel falls back to the matching chords entry). Python
// guarantees all four share one coordinate system per
// instrument, so no size or offset is sent here.
export interface MixerDiagrams {
	structure: Record<string, string>;
	scale: Record<string, string>;
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