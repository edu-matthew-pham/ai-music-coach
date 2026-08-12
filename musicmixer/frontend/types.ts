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

// Three layers per instrument, meant to be stacked: the
// always-there structure (keys/frets/strings, not a
// toggle - a picture of marks with nothing under them is
// illegible), the key's scale, and one chord-tones overlay
// per distinct chord the chart uses. Python guarantees all
// three share one coordinate system per instrument, so no
// size or offset is sent here.
export interface MixerDiagrams {
	structure: Record<string, string>;
	scale: Record<string, string>;
	chords: Record<string, Record<string, string>>;
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