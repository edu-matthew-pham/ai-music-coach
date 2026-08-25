// chordEvents.ts
//
// The chord and bar-line events the Lyrics panel prints
// above its words, and the highlight decisions made over
// them. Extracted from LyricsPanel.svelte after two real
// bugs shipped in a row (a syncopated chord going grey at
// the bar line; the ring vanishing onto a suppressed,
// invisible repeat) that were each "verified" by reading
// the code rather than running it - inline in a component,
// this logic could only be checked by building the whole
// app and looking. As a plain module it runs under vitest
// against the real Mulan timeline, the same way
// targetNotes.ts is tested.
//
// The rules, as agreed on real songs:
// - Every bar prints its chord. A carried entry (the same
//   chord still sounding when a later bar opens) prints
//   faded rather than being dropped, so a bar is never
//   chord-blind and paired mode losing a line does not
//   lose the current chord.
// - EXCEPT a carried repeat right after a syncopation:
//   a chord that landed within the last beat before the
//   bar line was just printed, and its echo half a beat
//   later is noise. The adopting bar instead extends the
//   syncopated chord's own bar span, so it stays
//   bar-highlighted through the bar it anticipated.
// - The single chord actually sounding right now carries
//   a ring. It sits on the latest VISIBLE instance: an
//   ordinary held chord's ring travels bar to bar with
//   its printed faded repeats; a suppressed repeat is
//   skipped exactly as it is skipped in print, so the
//   ring stays on the syncopated chord itself and never
//   points at nothing.

import type { MixerBar } from "./types";

export type RhythmEvent =
	| {
		time: number;
		type: "chord";
		name: string;
		carried: boolean;
		barStart: number;
		barEnd: number;
	}
	| { time: number; type: "bar"; barStart: number; barEnd: number };

export interface PhraseWindow {
	start: number;
	end: number;
}

// A chord's real position in seconds - the same
// beat_in_bar/bar.beats fraction ChordStrip and the Notes
// panel already use.
export function chordTime(
	bar: MixerBar,
	chord: MixerBar["chords"][number]
): number {
	return bar.start + (chord.beat_in_bar / bar.beats) * (bar.end - bar.start);
}

// A carried repeat is suppressed when the real change was
// itself a syncopation into this bar - landed within the
// last beat before the bar line. One predicate, shared by
// the printing and the ring, so what is highlighted can
// never disagree with what is on screen.
export function repeatSuppressed(
	barStart: number,
	lastRealOnset: number | null,
	lastRealBeatSeconds: number
): boolean {
	return (
		lastRealOnset !== null &&
		barStart - lastRealOnset <= lastRealBeatSeconds + 1e-6
	);
}

export function chordEvents(
	timeline: MixerBar[],
	phrase: PhraseWindow | null
): RhythmEvent[] {
	if (!phrase) return [];
	const found: RhythmEvent[] = [];
	let lastRealOnset: number | null = null;
	let lastRealBeatSeconds = 0;
	let lastRealEvent: (RhythmEvent & { type: "chord" }) | null = null;
	for (const bar of timeline) {
		const beatSeconds = (bar.end - bar.start) / bar.beats;
		for (const chord of bar.chords) {
			const time = chordTime(bar, chord);
			if (!chord.carried) {
				lastRealOnset = time;
				lastRealBeatSeconds = beatSeconds;
				lastRealEvent = null;
			}
			if (
				chord.carried &&
				repeatSuppressed(bar.start, lastRealOnset, lastRealBeatSeconds)
			) {
				// The bar adopts the syncopated chord: with its
				// repeat suppressed, the real chord's own bar
				// span stretches over this bar. The real chord
				// is tracked by reference, not assumed to be
				// the last thing pushed - "last pushed" was the
				// first shipped version of this, and it silently
				// failed whenever the real chord and the
				// suppressed repeat fell in different phrase
				// windows (a line-ending syncopation, the most
				// common kind), or when anything else had been
				// pushed in between.
				if (lastRealEvent) {
					lastRealEvent.barEnd = bar.end;
				}
				continue;
			}
			if (bar.start >= phrase.end || bar.end <= phrase.start) continue;
			if (time < phrase.start || time >= phrase.end) continue;
			const event: RhythmEvent & { type: "chord" } = {
				time, type: "chord", name: chord.name,
				carried: chord.carried,
				barStart: bar.start, barEnd: bar.end
			};
			if (!chord.carried) {
				lastRealEvent = event;
			}
			found.push(event);
		}
	}
	return found;
}

export function barEvents(
	timeline: MixerBar[],
	phrase: PhraseWindow | null
): RhythmEvent[] {
	if (!phrase) return [];
	const found: RhythmEvent[] = [];
	for (const bar of timeline) {
		if (bar.start >= phrase.start && bar.start < phrase.end) {
			found.push({
				time: bar.start, type: "bar",
				barStart: bar.start, barEnd: bar.end
			});
		}
	}
	return found;
}

export function allEvents(
	timeline: MixerBar[],
	phrase: PhraseWindow | null
): RhythmEvent[] {
	return [...barEvents(timeline, phrase), ...chordEvents(timeline, phrase)]
		.sort((a, b) => a.time - b.time);
}

// Everything belonging to the bar the playhead is inside
// lights up, and resets the moment the next bar opens.
export function inCurrentBar(event: RhythmEvent, playhead: number): boolean {
	return event.barStart <= playhead && playhead < event.barEnd;
}

// The single chord sounding right now: the latest visible
// chord instance at or before the playhead.
export function soundingChordTime(
	timeline: MixerBar[],
	playhead: number
): number | null {
	let latest: number | null = null;
	let lastRealOnset: number | null = null;
	let lastRealBeatSeconds = 0;
	for (const bar of timeline) {
		if (bar.start > playhead) break;
		const beatSeconds = (bar.end - bar.start) / bar.beats;
		for (const chord of bar.chords) {
			const time = chordTime(bar, chord);
			if (!chord.carried) {
				lastRealOnset = time;
				lastRealBeatSeconds = beatSeconds;
			}
			if (
				chord.carried &&
				repeatSuppressed(bar.start, lastRealOnset, lastRealBeatSeconds)
			) {
				continue;
			}
			if (time <= playhead && (latest === null || time > latest)) {
				latest = time;
			}
		}
	}
	return latest;
}

export function isSounding(
	event: RhythmEvent,
	sounding: number | null
): boolean {
	return (
		event.type === "chord" &&
		sounding !== null &&
		Math.abs(event.time - sounding) < 1e-9
	);
}
