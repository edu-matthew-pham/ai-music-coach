// essentia.js ships no type declarations for its dist
// paths, which are the paths we must import (the es builds,
// with the WASM embedded inline - see micPitch.svelte.ts
// for why). Declared here as any: the surface we use is
// four calls (arrayToVector, vectorToArray,
// PitchYinProbabilistic, and the vectors' delete()), all
// checked against the shipped source, not guessed.

declare module "essentia.js/dist/essentia.js-core.es.js" {
	const Essentia: any;
	export default Essentia;
}

declare module "essentia.js/dist/essentia-wasm.es.js" {
	export const EssentiaWASM: any;
}
