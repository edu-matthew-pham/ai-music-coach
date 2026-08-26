// tabPacking.ts
//
// Which lines go in which Tab-view column, packed by their
// REAL rendered heights against the real available screen
// height - not by a count.
//
// The count-based version this replaces divided the screen
// height by ONE sampled "typical" line's height and sliced
// the phrase list into equal-count chunks. Its own comments
// admitted the approximation ("a phrase in different
// wrapping shoes... this reserve narrows that gap, it does
// not claim to close it completely"), and a real regression
// proved it: a first column nearly double the intended
// height, because lines that wrap - or carry denser chord
// rows than the sampled one - silently exceed their assumed
// slot, and nothing clips (deliberately: clipping would cut
// lyrics off).
//
// No browser-native layout does this packing correctly
// either, researched before building rather than assumed:
// CSS multicol was already tried and killed by
// scrollIntoView; flex column-wrap has a documented
// cross-browser container-width bug (Flexbugs #14, open
// csswg-drafts issue "Nobody follows the spec regarding
// intrinsic size of column flex container" - Firefox never
// grows the container); Grid auto-flow column needs a fixed
// row COUNT, the exact thing that's wrong. So the columns
// stay JS-built - real elements the follow can scroll to -
// and only the deciding changes: measured heights in,
// columns out.
//
// Pure function, no DOM: the component measures, this
// packs, vitest checks it.

// Pack items into columns no taller than `budget`, with
// `gap` pixels between adjacent items in a column.
//
// Each line has TWO real heights: the one it renders at
// normally, and the taller one it renders at while it is
// the line being sung (bigger font, which can push it to
// wrap an extra row). Only one line is ever current at a
// time, but the current line MOVES - every line in a column
// eventually has its turn - so a column must be able to
// hold its own lines at their normal heights PLUS enough
// room for whichever of them inflates the most.
//
// Reserving per column, from that column's own lines, is
// what makes this tight rather than merely safe: packing
// every line at its big height would also never overflow,
// but would leave every column permanently roomier than it
// needs to be. The earlier version reserved a single
// number sampled from whichever line happened to be current
// when the measurement ran - which under-reserved whenever
// a longer line's turn came later.
//
// Returns, for each item, the index of the column it lands
// in - a shape the component can turn into phrase groups
// without this module knowing what a phrase is.
export function packByHeight(
	heights: number[],
	budget: number,
	gap: number,
	currentHeights: number[] = []
): number[] {
	const columnOf: number[] = [];

	const inflationOf = (i: number): number =>
		Math.max(0, (currentHeights[i] ?? heights[i]) - heights[i]);

	let column = 0;
	let used = 0;
	let linesInColumn = 0;
	let reserve = 0;

	for (let i = 0; i < heights.length; i++) {
		const height = heights[i];
		const needed = linesInColumn > 0 ? gap + height : height;
		const nextReserve = Math.max(reserve, inflationOf(i));

		if (linesInColumn > 0 && used + needed + nextReserve > budget) {
			column += 1;
			used = height;
			linesInColumn = 1;
			reserve = inflationOf(i);
		} else {
			// A line taller than the whole budget still gets
			// placed (alone, in its own column when it isn't
			// the first) - the standing rule is "never
			// silently cut lyrics off", so an oversized line
			// overflows visibly rather than vanishing.
			used += needed;
			linesInColumn += 1;
			reserve = nextReserve;
		}

		columnOf.push(column);
	}

	return columnOf;
}

// Group any list by a columnOf assignment from packByHeight.
export function groupByColumn<T>(items: T[], columnOf: number[]): T[][] {
	const columns: T[][] = [];
	items.forEach((item, i) => {
		const column = columnOf[i] ?? 0;
		while (columns.length <= column) columns.push([]);
		columns[column].push(item);
	});
	return columns;
}
