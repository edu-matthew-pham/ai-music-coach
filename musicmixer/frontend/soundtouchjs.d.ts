// soundtouchjs ships no type declarations. Same treatment
// as essentia.d.ts beside this file: declared minimally for
// the surface timestretch.ts actually uses - SoundTouch's
// tempo and its stretch's setParameters, and SimpleFilter's
// extract loop. Anything beyond that is deliberately not
// declared, so a new call site has to come back here and
// state what it relies on.
declare module "soundtouchjs" {
	export class SoundTouch {
		tempo: number;
		stretch: {
			setParameters(
				sampleRate: number,
				sequenceMs: number,
				seekWindowMs: number,
				overlapMs: number
			): void;
		};
	}

	export class SimpleFilter {
		constructor(
			source: {
				extract(
					target: Float32Array,
					numFrames: number,
					position: number
				): number;
			},
			soundTouch: SoundTouch
		);
		extract(target: Float32Array, numFrames: number): number;
	}
}
