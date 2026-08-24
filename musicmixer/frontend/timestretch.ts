// timestretch.ts
//
// Offline time-stretch of one mono layer, pitch preserved.
// Pure samples-in samples-out so it runs and is tested in
// Node (vitest) without an AudioContext - the engine wraps
// the result in an AudioBuffer, this file never touches
// Web Audio.
//
// Two traps, both found by measurement against real layer
// audio (session-notes-timestretch-stage1.md), both handled
// here so no caller can forget them:
//
// 1. SoundTouch silently assumes 44100 Hz. Our layers are
//    8kHz; left unset, its WSOLA windows come out ~5x too
//    long in real time and it duplicates transients
//    wholesale - a 200-click metronome came back as 271
//    clicks ticking at roughly the ORIGINAL tempo. The
//    setParameters call below is not optional.
// 2. SoundTouch never flushes its tail - about a second of
//    song stays buffered at the end with no flush API in
//    the JS port. Padding the input with silence and
//    trimming the output to the exact expected length is
//    the standard workaround, and makes the output length
//    sample-exact, which the engine's time arithmetic then
//    relies on.

import { SoundTouch, SimpleFilter } from "soundtouchjs";

// How much silence to append so the real tail gets pushed
// through SoundTouch's internal buffering. Measured shortfall
// was ~1.3s of output; 2s clears it with margin.
const FLUSH_PAD_SECONDS = 2;

// soundtouchjs works in interleaved stereo frames; this
// mimics its own WebAudioBufferSource contract for a mono
// array, so the engine-side code shape matches the library's
// documented usage exactly.
function monoSource(samples: Float32Array) {
	return {
		extract(target: Float32Array, numFrames: number, position: number): number {
			const available = Math.max(
				0,
				Math.min(numFrames, samples.length - position)
			);
			for (let i = 0; i < available; i++) {
				target[i * 2] = samples[position + i];
				target[i * 2 + 1] = samples[position + i];
			}
			return available;
		},
	};
}

// tempo is the playback rate as a fraction of full speed:
// 0.75 plays at 75% (longer output), 1.5 at 150% (shorter).
// The caller never passes 1 - at full speed the engine plays
// the original decoded buffers untouched (a true bypass, not
// a stretch by 1.0).
export function stretchSamples(
	samples: Float32Array,
	tempo: number,
	sampleRate: number
): Float32Array<ArrayBuffer> {
	const expected = Math.round(samples.length / tempo);

	const padded = new Float32Array(
		samples.length + sampleRate * FLUSH_PAD_SECONDS
	);
	padded.set(samples);

	const soundTouch = new SoundTouch();
	// Trap 1: the real sample rate, or transients duplicate.
	// Zeros keep the library's own automatic window lengths,
	// now computed at the right rate; 8 is its default
	// overlap in ms.
	soundTouch.stretch.setParameters(sampleRate, 0, 0, 8);
	soundTouch.tempo = tempo;

	const filter = new SimpleFilter(monoSource(padded), soundTouch);

	// Trap 2: sized to the exact expected length; everything
	// past it is the silence pad coming back out, dropped.
	const out = new Float32Array(expected);
	const block = new Float32Array(8192 * 2);
	let written = 0;
	let frames: number;
	while ((frames = filter.extract(block, 8192)) > 0) {
		const take = Math.min(frames, expected - written);
		for (let i = 0; i < take; i++) out[written + i] = block[i * 2];
		written += take;
		if (written >= expected) break;
	}
	return out;
}
