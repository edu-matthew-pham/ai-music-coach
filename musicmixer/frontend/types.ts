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

// Each instrument's scale base (always drawable once a key
// is set) and, per instrument, one transparent chord-tones
// overlay per distinct chord name the chart uses. The two
// stack in the browser - Python guarantees they share one
// coordinate system, so no size or offset is sent here.
export interface MixerDiagrams {
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