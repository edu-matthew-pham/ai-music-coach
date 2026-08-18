// Word-label placement for the Notes panel.
//
// A word label belongs to a note, and starts out one row
// below that note's pitch. Whenever two labels' notes are
// close in both time and pitch - the same pitch in a round,
// a few rows apart in a partner song, a third apart on a
// generated harmony line - the labels land on the same line
// at overlapping x positions and print on top of each other.
//
// Earlier fixes each checked one specific shape (is the row
// below occupied by a note? are two notes at exactly the
// same pitch?) and each one left the next collision uncovered.
// This asks the actual question instead: does this label's
// TEXT overlap another label's TEXT? Standard lane assignment
// over rendered label geometry - it doesn't know or care what
// pitch, tune or layer a label came from, so it covers every
// one of those cases the same way, plus any that haven't come
// up yet.
//
// Pure functions, no Svelte, no DOM: testable on their own,
// and the panel only supplies the numbers it already has.

export interface LabelInput {
	// A stable id, so a caller can find its own label's result.
	id: string;
	// Where the label wants to sit, in pixels: horizontally
	// centred at x, on the line at y (SVG text baseline).
	x: number;
	y: number;
	// The word itself - width is estimated from it.
	text: string;
	// Lower sorts first when two labels compete for the same
	// spot; ties broken by x. Lets a caller say "your own part
	// keeps the top line" without this module knowing what a
	// part is.
	priority: number;
}

export interface LabelPlacement {
	id: string;
	x: number;
	y: number;
	// How many lines down from where it asked to be. 0 means
	// it sat exactly where it wanted.
	lane: number;
}

export interface LaneOptions {
	// Vertical distance between lanes, in pixels - the label
	// font's line height, already scaled if the font is.
	lineHeight: number;
	// Average glyph width in pixels for width estimation,
	// already scaled if the font is. ~0.55em is a fair figure
	// for the sans-serif faces this panel uses; a caller can
	// tighten or loosen it if a real font measures differently.
	glyphWidth: number;
	// Minimum horizontal gap between two labels on the same
	// line before they are considered to overlap.
	gap: number;
	// If given, no label may be placed at a y greater than
	// this - a page's own bottom edge, so a label that has to
	// drop several lanes never leaves the visible area. Once
	// the floor is reached, the label stays there even if it
	// still overlaps: crowded-but-visible beats invisible.
	floorY?: number;
	// How many lanes a label may drop before giving up and
	// staying where it is. Guards against a genuinely dense
	// stretch pushing labels arbitrarily far down.
	maxLanes?: number;
}

export function estimateWidth(text: string, glyphWidth: number): number {
	return text.length * glyphWidth;
}

// Assign each label a lane so that no two labels on the same
// line horizontally overlap. Labels are placed in priority
// order (then left to right), and each takes the first lane
// where it clears everything already placed. A label that
// would be pushed past floorY (or past maxLanes) stops at the
// last legal lane rather than disappearing.
export function assignLanes(
	labels: LabelInput[],
	options: LaneOptions
): LabelPlacement[] {
	const { lineHeight, glyphWidth, gap, floorY, maxLanes = 6 } = options;

	const ordered = [...labels].sort(
		(a, b) => a.priority - b.priority || a.x - b.x
	);

	// Everything placed so far, as horizontal spans per (base
	// y, lane) line. Two labels are on the same line when their
	// base y matches to the pixel and their lane matches - a
	// label that asked for a different starting y is a
	// different line even at lane 0, so labels under notes on
	// different pitch rows never falsely count as competing.
	const placed: Array<{ y: number; left: number; right: number }> = [];

	const results: LabelPlacement[] = [];

	function collidesAt(candidateY: number, left: number, right: number): boolean {
		return placed.some(
			(other) =>
				Math.abs(other.y - candidateY) < lineHeight * 0.5 &&
				other.left < right + gap &&
				other.right > left - gap
		);
	}

	for (const label of ordered) {
		const half = estimateWidth(label.text, glyphWidth) / 2;
		const left = label.x - half;
		const right = label.x + half;

		// The label's own wanted line, clamped to the floor
		// before anything else - a label whose note sits at the
		// very bottom of the page asks for a y past the floor,
		// and must be pulled up onto it first or the floor check
		// inside the loop below fires on lane 0 before any
		// collision is ever looked at (a real bug, found by
		// running this on a real page: two labels both past the
		// floor were each clamped to it and never compared).
		const baseY = floorY !== undefined ? Math.min(label.y, floorY) : label.y;

		// Try lanes in the order: wanted line, then one down,
		// then one UP, then two down, two up... Downward is the
		// natural direction (below the note), but a label already
		// on the floor has no room below and must be allowed to
		// climb - upward lanes sit inside the note's own box
		// area, which is at least always on the page.
		let chosen = 0;
		let chosenY = baseY;

		for (let step = 0; step < maxLanes; step++) {
			const candidates: number[] = step === 0 ? [0] : [step, -step];

			let found = false;

			for (const lane of candidates) {
				const candidateY = baseY + lane * lineHeight;

				if (floorY !== undefined && candidateY > floorY) continue;

				if (!collidesAt(candidateY, left, right)) {
					chosen = lane;
					chosenY = candidateY;
					found = true;
					break;
				}
			}

			if (found) break;
		}

		placed.push({ y: chosenY, left, right });
		results.push({ id: label.id, x: label.x, y: chosenY, lane: chosen });
	}

	return results;
}
