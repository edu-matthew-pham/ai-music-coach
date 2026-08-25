// columnItems.ts
//
// Which items a parts-mode column renders: its own phrases,
// interleaved with "gap" markers wherever its own phrase
// list has a hole - a stretch another voice sings through.
// The chart is shared across voices (one chart per song),
// so a gap is not silence for the chord display even when
// it is silence for this tune's own words; the gap item is
// what LyricsPanel fills with a lead-in-style chord line.
//
// Extracted after a real report ("Voice 2 has no chords
// mid-song, past a key change") turned out, on inspection,
// to be a long unbroken chord line being mistaken for
// nothing - but that this needed inspection at all, rather
// than a test answering it in a second, is the actual
// problem. Pure function, no Svelte reactivity, tested
// against real phrases_by_part output (This Love, which has
// both an early hole and a later, separate one - the case
// that would have caught a "only the first gap" bug).

export interface PhraseLike {
	start: number;
	end: number;
	label: string;
}

export type ColumnItem<P extends PhraseLike> =
	| { kind: "phrase"; phrase: P; start: number }
	| { kind: "gap"; start: number; end: number };

export interface ColumnItemsResult<P extends PhraseLike> {
	items: ColumnItem<P>[];
	current: P | null;
}

// Which phrase the playhead is in (or about to reach, if
// currently in a hole) - the same "first phrase whose end
// is still ahead" rule the single-tune path uses, falling
// back to the last phrase once the playhead is past
// everything.
export function currentPhraseIndex<P extends PhraseLike>(
	phrases: P[],
	playhead: number
): number {
	if (!phrases.length) return -1;
	const found = phrases.findIndex((phrase) => playhead < phrase.end);
	return found === -1 ? phrases.length - 1 : found;
}

export function columnItems<P extends PhraseLike>(
	phrases: P[],
	playhead: number
): ColumnItemsResult<P> {
	const foundIndex = currentPhraseIndex(phrases, playhead);
	const current = foundIndex >= 0 ? phrases[foundIndex] : null;

	if (foundIndex < 0) return { items: [], current: null };

	// If the playhead is currently sitting in a hole before
	// the found phrase, the gap in front of it starts at
	// wherever this tune's own last phrase before now ended
	// (0 if none yet) - not at the found phrase's own start,
	// which would skip the hole entirely.
	let previousEnd: number | null = playhead < phrases[foundIndex].start
		? phrases.reduce(
			(last, phrase) => (
				phrase.end <= playhead && phrase.end > last ? phrase.end : last
			), 0
		)
		: null;

	const items: ColumnItem<P>[] = [];

	for (const phrase of phrases.slice(foundIndex)) {
		if (previousEnd !== null && phrase.start - previousEnd > 1e-6) {
			items.push({ kind: "gap", start: previousEnd, end: phrase.start });
		}
		items.push({ kind: "phrase", phrase, start: phrase.start });
		previousEnd = phrase.end;
	}

	return { items, current };
}
