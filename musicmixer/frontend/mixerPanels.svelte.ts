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

// Whether the note view draws the live sung-pitch line once
// a mic exists. On by default - turning the mic on and then
// seeing nothing would read as broken - but its own toggle,
// since watching the line while sight-reading the boxes is
// exactly the kind of thing one person wants and the next
// finds distracting.
export const showLiveTrace = $state({ value: true });

// Which instrument names exist is Python's to say, not this
// file's: instrument_diagrams.py's INSTRUMENTS list is the
// one home for that, sent every time as the keys of
// diagrams.structure. Hardcoding a matching list of names
// here was a real bug once already - Ukulele was added on
// the Python side, generalized through every drawing
// function, tested end to end, and still never appeared as
// a toggle, because this file kept its own separate copy of
// "what instruments exist" that nothing kept in sync.
//
// Python's own names now carry a size variant too - "Piano,
// 3 octaves", "Guitar, 13 frets", "Violin, first position" -
// a display choice, not a different instrument, the same
// way Violin's two positions always were. diagramInstruments
// is keyed by the instrument family (the part before the
// comma) - one toggle per real instrument the player thinks
// about, not one per size variant. diagramVariant remembers
// which size is currently chosen for each family; the two
// together give the actual key to look up in Python's data
// (family + ", " + variant), reconstructed in
// InstrumentPanel rather than duplicated here.
//
// So this file only remembers what Python's data genuinely
// cannot tell us: which instruments should start ticked and
// which size each should start at (both UX choices, not
// facts about the instrument), and whatever the player has
// actually chosen since. Families and variants both arrive
// lazily, through ensureInstrumentToggle and
// ensureInstrumentVariant, called once per name the first
// time InstrumentPanel sees it in real data.
const DEFAULT_ON_INSTRUMENTS = new Set(["Piano", "Guitar", "Ukulele"]);

// The fuller size for Piano/Guitar/Ukulele, first position
// for Violin (not the fuller option there - a beginner
// starts in first position, and third is the thing to grow
// into, not the default view). A family with no entry here
// falls back to whichever variant it saw first.
const DEFAULT_VARIANTS: Record<string, string> = {
	Piano: "3 octaves",
	Guitar: "13 frets",
	Ukulele: "10 frets",
	Violin: "first position"
};

export const diagramInstruments: Record<string, boolean> = $state({});
export const diagramVariant: Record<string, string> = $state({});

export function ensureInstrumentToggle(name: string): void {
	if (!(name in diagramInstruments)) {
		diagramInstruments[name] = DEFAULT_ON_INSTRUMENTS.has(name);
	}
}

export function ensureInstrumentVariant(family: string, firstSeen: string): void {
	if (!(family in diagramVariant)) {
		diagramVariant[family] = DEFAULT_VARIANTS[family] ?? firstSeen;
	}
}

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