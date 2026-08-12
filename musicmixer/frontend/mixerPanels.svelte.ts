// mixerPanels.svelte.ts
//
// Which panels are showing.
//
// A group jam on a big screen wants different things
// visible than one person practising alone at a laptop -
// rather than build one fixed layout, each panel can be
// shown or hidden independently. This is deliberately
// separate from mixerEngine.svelte.ts: visibility knows
// nothing about audio, and every panel that reads it is
// just displaying a slice of the engine's state, not
// touching playback.
//
// Adding a new panel later - note boxes, an instrument
// diagram - means adding one more entry here and one new
// component, not redesigning this or the engine.
//
// Module-scoped for the same reason everything else
// persistent is: Gradio tears the component down and
// rebuilds it on every event round trip, and a toggle
// someone chose should not silently revert because an
// unrelated click happened to trigger a remount.

export const panels: Record<string, boolean> = $state({
	strip: true,
	faders: true,
	notes: false,
	lyrics: false,
	instruments: false
});

// Which layers show inside the note view. Separate from
// panels above: this isn't "is the note view visible" but
// "which voices does it draw" - melody only by default,
// since showing all four at once is what crowded the box
// labels together in the first place. Kept module-scoped
// for the same remount-survival reason as everything else
// here.
export const noteLayers: Record<string, boolean> = $state({
	Melody: true,
	"Harmony above": false,
	"Harmony below": false,
	Bass: false
});

// Whether the note view shows a dimmed preview of the next
// phrase below the current one - lives here rather than as
// component state for the usual reason: it should survive
// a remount rather than silently reverting.
export const showNextPreview = $state({ value: false });

// Below (full width each, one under the other) or side by
// side (half width each). Only meaningful once a preview is
// showing at all, which is why it stays tucked next to that
// toggle rather than being its own separate control.
export const previewSideBySide = $state({ value: false });

// Two ways to show the same words - pills that light up one
// at a time, or a flowing sentence where the sung words
// change colour as they pass. Showing both at once was the
// same information twice; this is one or the other, not a
// combination.
export const lyricsSentenceStyle = $state({ value: false });

// Whether the Notes panel's per-note word labels show
// alongside the Lyrics panel. Kept as its own toggle rather
// than forced off when Lyrics is on: redundancy between the
// two isn't automatically a problem (SingStar shows both),
// so the choice is left to whoever is looking at the
// screen rather than decided here.
export const notesShowLabels = $state({ value: true });

// The Lyrics panel at its normal size, or enlarged. A long
// phrase or a whole-song view already reads fine small;
// this is for whoever wants the words bigger regardless.
export const lyricsLarge = $state({ value: false });

// Instrument-toggle and layer-toggle (structure not
// included: it isn't a toggle, it's the ground everything
// else stands on).
export const diagramInstruments: Record<string, boolean> = $state({
	Piano: false,
	Guitar: false,
	"Violin, first position": false,
	"Violin, third position": false
});

// The two transparent layers a chosen instrument stacks:
// the key's scale (static for the song) and the current
// bar's chord (changes as the mixer plays). Both sit on
// top of the always-there structure layer, which has no
// toggle of its own. Chord defaults on because it's the
// live one - the scale is available a click away, same as
// everything else here.
export const diagramLayers = $state({
	scale: false,
	chord: true
});

// Whether the Instruments panel sits beside the Mixer
// panel (a row) rather than stacked below it (the default,
// same as every other panel). Only meaningful once both
// are showing at once - a layout choice, not a visibility
// one, so it lives separately from panels above.
export const instrumentsBesideMixer = $state({ value: false });

// How the side-by-side row behaves when the two panels
// don't both fit: drop the Instruments panel to its own
// line below ("wrap"), or let both panels compress to fit
// on one line ("shrink"). Only read when
// instrumentsBesideMixer is on.
export const sideBySideLayout = $state<{ value: "wrap" | "shrink" }>({
	value: "wrap"
});