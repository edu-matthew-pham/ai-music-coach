// responsive.ts
//
// The one place container-width breakpoints are named, for
// both JS and CSS. Before this file, the same two numbers
// (600, 1100) existed under three different names in three
// files - Index.svelte's own NARROW_BREAKPOINT, and
// mixerPanels.svelte.ts's PHONE_MAX/TABLET_MAX - with nothing
// stopping any one of them drifting from the others. Now
// there is one number line, named once, imported everywhere
// on the JS side.
//
// CSS cannot import a TS constant, so Index.svelte's
// @container rules on .mixer carry their own copy of NARROW_MAX
// and MEDIUM_MAX - search for them there. The two copies must
// be kept equal by hand; each site says so in a comment
// pointing at the other.
//
// "narrow/medium/wide" names the CONTAINER's own inline size,
// not the device or the browser window. The mixer can be
// narrow inside a wide browser window - a Gradio column, an
// embed, a page laid out beside something else - so every
// measurement here is the mixer's own measured width, never
// window.innerWidth. (The one deliberate exception is the
// very first paint, before anything has been measured - see
// mixerPanels.svelte.ts's module-load call, which still has
// nothing else to go on.)

export type Band = "narrow" | "medium" | "wide";

// Keep in sync with the @container breakpoints in
// Index.svelte's <style> block.
export const NARROW_MAX = 600;
export const MEDIUM_MAX = 1100;

export function bandFor(width: number): Band {
	if (width < NARROW_MAX) return "narrow";
	if (width < MEDIUM_MAX) return "medium";
	return "wide";
}

// Svelte context key for the reactive size band. A module-
// level symbol rather than a plain string, so it can never
// collide with some other component's own context key by
// accident - two different symbols are never equal even if
// created with the same description.
export const SIZE_CONTEXT_KEY = Symbol("mixer-size-band");

// Shape stored in context: a GETTER, not a plain value.
// Svelte 5's context is not itself reactive - setContext just
// stores whatever value you hand it, once, at the moment
// it's called. Storing `size` as a plain value would freeze
// it at whatever containerWidth happened to be on first
// render. A getter keeps re-reading Index.svelte's own live
// $derived every time a consumer accesses `.band`, which is
// what lets a consumer's own `$derived(ctx.band)` stay
// correct as the container is resized - the consumer's
// derived tracks whatever reactive state the getter itself
// reads, the same way any other derived does.
export interface SizeContext {
	readonly band: Band;
}
