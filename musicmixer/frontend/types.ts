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

export interface MixerValue {
	layers: MixerLayer[];
	timeline: MixerBar[];
	notes: MixerNote[];
	phrases: MixerPhrase[];
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