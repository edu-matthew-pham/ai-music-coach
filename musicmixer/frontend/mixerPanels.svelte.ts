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

// Phrases is its own toggle, split out from Notes: jumping
// to a phrase is navigation, useful with or without the
// pitch-box view showing, so it should not be tied to that
// view's own toggle. Defaults are chosen so a freshly built
// mixer already looks like a working practice view - chart,
// phrases, words, faders, the live chord diagram - with the
// pitch-box display (Notes) as the one opt-in extra, since
// that one is the most likely to be unfamiliar at a glance.
export const panels: Record<string, boolean> = $state({
	strip: true,
	faders: true,
	phrases: true,
	notes: false,
	lyrics: true,
	instruments: true
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

// Whether the Notes panel's per-note word labels show
// alongside the Lyrics panel. Kept as its own toggle rather
// than forced off when Lyrics is on: redundancy between the
// two isn't automatically a problem (SingStar shows both),
// so the choice is left to whoever is looking at the
// screen rather than decided here.
export const notesShowLabels = $state({ value: true });

// Instrument-toggle and layer-toggle (structure not
// included: it isn't a toggle, it's the ground everything
// else stands on). Piano and Guitar default on, since a
// default-on Instruments panel showing nothing but "choose
// an instrument" would look broken rather than helpful.
export const diagramInstruments: Record<string, boolean> = $state({
	Piano: true,
	Guitar: true,
	"Violin, first position": false,
	"Violin, third position": false
});

// The three transparent layers a chosen instrument can
// stack, all independently on or off: the key's scale
// (static for the song), every place the current chord's
// notes occur, and one beginner voicing for it. All three
// at once is a real, useful combination - seeing every
// chord-tone position alongside the one fixed shape helps
// with an arpeggio or a right-hand accompaniment that goes
// beyond the shape itself. Each sits on top of the
// always-there structure layer, which has no toggle of its
// own. Chord shape defaults on, the other two off: the
// beginner voicing is the thing most people want first, and
// the theory-heavier views (every position, the whole
// scale) are opt-in extras once that's familiar.
export const diagramLayers = $state({
	scale: false,
	chordNotes: false,
	chordShape: true
});

// Whether the instrument panel shows a dimmed preview of
// the upcoming chord below the current one - the same idea
// as the Notes panel's next-phrase preview, for seeing a
// change coming before it arrives rather than reacting to
// it after the fact.
export const previewNextChord = $state({ value: false });

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