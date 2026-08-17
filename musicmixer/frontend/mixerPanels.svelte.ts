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
// view's own toggle. Notes now defaults on: it shares a row
// with Lyrics (see Index.svelte's lyrics-and-notes), and an
// empty 70%-wide gap where Notes would be is a worse default
// than the panel itself - the "opt-in extra" reasoning that
// justified starting it off no longer applies once Lyrics
// alone can't fill that space on its own.
export const panels: Record<string, boolean> = $state({
	strip: true,
	faders: true,
	phrases: true,
	notes: true,
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

// Shifts where the melody notes DRAW in the Notes panel, in
// octaves (-1, 0, or 1) - display only, never touches the
// underlying pitch data, playback, or anything Generate
// Playback built. A baritone singing a genuine octave below
// written pitch has a correct, on-pitch line that still
// sits 12 rows away from the target notes with nothing
// wrong; this closes that gap by moving the target to where
// the voice naturally sits, not by moving the voice.
// Deliberately does NOT shift the live trace or dot - those
// already show the true pitch, and shifting both would
// leave the same 12-row gap, just relocated.
export const notesOctaveShift = $state<{ value: -1 | 0 | 1 }>({ value: 0 });

// Whether the Notes panel draws chord names, timing-aware,
// above the note boxes - and whether the Lyrics panel draws
// them above the syllable each one actually lands on. Two
// separate toggles, not one shared switch: someone reading
// notes and someone reading lyrics-only want this
// independently, the same reasoning as notesShowLabels
// above. Both default on since a chord appearing at its
// real timing (not eyeballed like a printed tab) is the
// point of building this on top of real bar/beat data.
export const notesShowChords = $state({ value: true });
export const lyricsShowChords = $state({ value: true });

// "|" at every bar boundary in the Lyrics panel, whether or
// not a chord happens to start there - "| G" and "|" alone
// are both valid, per-bar landmarks rather than a rhythm
// trace. Fine-grained timing (individual beats, the sung
// line) is the Notes panel's job already; this stays coarse
// on purpose rather than duplicating it.
export const lyricsShowBars = $state({ value: true });

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

// How many upcoming chords the instrument panel shows in a
// row beneath each instrument's current chord - drawn
// smaller than the current one, full opacity, chord name
// under each. Replaces an earlier single "next chord"
// preview that duplicated the whole diagram at full size
// under a fade: a faded full-size copy read as broken, not
// as a preview, and cost as much height as the real thing.
// 0 turns the row off. Default 2: enough warning to move a
// hand, without the row growing wider than the diagram
// above it on the compact instruments.
export const previewChordCount = $state<{ value: 0 | 1 | 2 | 3 }>({ value: 2 });

// Per-family display scale for the instrument diagrams,
// a multiplier on the panel's base height (see
// InstrumentPanel's BASE_HEIGHT). The panel already draws
// every diagram at one fixed height and lets width follow
// each instrument's own aspect ratio - this is that one
// number, per instrument, in the player's hands: a guitar
// read from a couch across a room can be dialled up without
// the piano beside it moving. Keyed by family the same way
// diagramInstruments is; ensureInstrumentScale seeds each
// family at 1 the first time InstrumentPanel sees it.
export const diagramScale: Record<string, number> = $state({});

export function ensureInstrumentScale(family: string): void {
	if (!(family in diagramScale)) {
		diagramScale[family] = 1;
	}
}

// Whether the fader panel is open. It is a modal now, not
// a panel in the page flow: levels get set between takes,
// not watched during one, so it costs no layout space
// while closed and opening it moves nothing underneath -
// an in-flow panel expanding was exactly what pushed the
// instrument diagrams around. panels.faders (above) says
// whether the Mix button exists at all; this says whether
// the sheet it opens is showing. Module-scoped so a remount
// mid-edit does not slam it shut.
export const mixerOpen = $state({ value: false });

// A global text-size control for the chart strip's chord and
// word labels and the phrase buttons - things read together,
// in the same glance, while singing, so one shared knob keeps
// them in step with each other. Lyrics and Notes used to share
// this too, but each earns its own dedicated control below:
// they're each a large enough panel with their own reading
// distance and content density (Lyrics is prose that wraps,
// Notes is a dense pitch grid) that tying them to the chart
// strip's own scale, or to each other's, was the wrong amount
// of coupling - "granular" was the explicit ask. Same discrete
// +/- pattern throughout, for the same reason: a slider needs
// pointer precision a remote or a couch-distance tap doesn't
// reliably give.
export const readScale = $state({ value: 1 });

export const READ_SCALE_MIN = 0.8;
export const READ_SCALE_MAX = 1.8;
export const READ_SCALE_STEP = 0.1;

export function setReadScale(next: number): void {
	const clamped = Math.min(READ_SCALE_MAX, Math.max(READ_SCALE_MIN, next));
	readScale.value = Math.round(clamped * 10) / 10;
}

// Lyrics' own scale, independent of readScale above and of
// Notes' below - each panel is read on its own terms.
export const lyricsScale = $state({ value: 1 });

// Notes' own scale - separate range from the other two: its
// content (pitch boxes, chord names, syllables all packed into
// one SVG grid) is denser than a line of lyric text or a chart
// bar, so it has more headroom to shrink before anything
// overlaps, and less before an enlarged grid needs to scroll
// further to see the same number of notes.
export const notesScale = $state({ value: 1 });

export const PANEL_SCALE_MIN = 0.7;
export const PANEL_SCALE_MAX = 2;
export const PANEL_SCALE_STEP = 0.1;

export function setLyricsScale(next: number): void {
	const clamped = Math.min(PANEL_SCALE_MAX, Math.max(PANEL_SCALE_MIN, next));
	lyricsScale.value = Math.round(clamped * 10) / 10;
}

export function setNotesScale(next: number): void {
	const clamped = Math.min(PANEL_SCALE_MAX, Math.max(PANEL_SCALE_MIN, next));
	notesScale.value = Math.round(clamped * 10) / 10;
}

// Three named views, not two presets plus an implicit
// default. "Tab" and "SingStar" are fixed layouts for jam
// sessions and solo mic practice respectively - each a
// preset over the panels record below. "Custom" is the
// free-toggle view: the six panel checkboxes only make sense
// there, since in Tab or SingStar the preset already owns
// `panels` and a stray checkbox click would silently fight
// it without changing the button label.
//
// Opens in "tab" - jam sessions (multiple people reading
// lyrics/chords off one screen, no mic) are the more common
// case than Custom's everything-on layout, per the person's
// own steer. savedPanels/savedLyricsScale/savedNotesScale
// hold whatever Custom was last set up as, so returning to
// Custom restores exactly that rather than some fixed
// default - someone who had Instruments off already
// shouldn't have it switched back on by leaving Tab view.
export const viewPreset = $state<{ value: "tab" | "singstar" | "custom" }>({
	value: "custom"
});

let savedPanels: Record<string, boolean> = { ...panels };
let savedLyricsScale: number = lyricsScale.value;
let savedNotesScale: number = notesScale.value;

const TAB_PANELS: Record<string, boolean> = {
	strip: false,
	faders: true,
	phrases: true,
	notes: false,
	lyrics: true,
	instruments: false
};

const SINGSTAR_PANELS: Record<string, boolean> = {
	strip: false,
	// Phrases now stays on here too (was off) - the same
	// click-to-jump strip Tab view already gets. SingStar's
	// own layout (Notes above, a compact two-line Lyrics
	// strip below) has no built-in way to jump around a song;
	// Phrases is exactly the navigation piece that was
	// missing, and it costs nothing extra to wire in since it
	// already renders generically off this one flag,
	// independent of which view preset is active.
	phrases: true,
	faders: true,
	notes: true,
	// Lyrics now stays on here (was off) - not beside Notes
	// the ordinary way, but as a compact strip stacked below
	// it (see Index.svelte's singstar branch): the pitch view
	// carries the singing, and a small current-plus-upcoming
	// line with its chords underneath lets a hand on an
	// instrument follow along at the same time, without
	// competing with the pitch view for the eye's attention
	// the way a side-by-side 30/70 split would.
	lyrics: true,
	instruments: false
};

// SingStar's own default text sizes - only two or three short
// lyric lines are ever on screen there (see LyricsPanel's
// singstar case), and Notes only has one phrase's worth of
// pitch boxes to show at a time in that layout, so both get
// room to run larger than the other modes default to without
// crowding. Notes isn't shown in Tab view at all, so it has
// no equivalent default to set there.
//
// Both Tab's and SingStar's defaults are now width-aware
// rather than one fixed number: the same 130%/200%/140% that
// suit a TV across a room are too large on a phone or tablet
// held closer. Three bands, not a continuous formula - a
// discrete choice is easier to reason about and to check by
// eye on a real device than a computed curve would be.
// PHONE_MAX/TABLET_MAX are container width in CSS pixels, the
// same measurement Index.svelte's own `narrow` breakpoint
// (600px) already uses for NARROW_BREAKPOINT - PHONE_MAX is
// deliberately the same 600 so the two don't quietly disagree
// about where "phone" ends.
const PHONE_MAX = 600;
const TABLET_MAX = 1100;

type ScaleBand = "phone" | "tablet" | "tv";

function scaleBand(width: number): ScaleBand {
	if (width < PHONE_MAX) return "phone";
	if (width < TABLET_MAX) return "tablet";
	return "tv";
}

// The tablet-band numbers are a first guess, not yet checked
// against a real tablet the way the phone and TV ends were
// reasoned from the app's own stated distances (couch-remote
// TV viewing; a phone held close) - worth a look on a real
// device before trusting them further.
const TAB_LYRICS_SCALE: Record<ScaleBand, number> = {
	phone: 1.0,
	tablet: 1.15,
	tv: 1.3
};
const SINGSTAR_LYRICS_SCALE: Record<ScaleBand, number> = {
	phone: 1.3,
	tablet: 1.6,
	tv: 2.0
};
const SINGSTAR_NOTES_SCALE: Record<ScaleBand, number> = {
	phone: 1.0,
	tablet: 1.2,
	tv: 1.4
};

// The three buttons are a radio group now, not toggles - the
// active one no longer means "press again to leave". Custom
// is the explicit third choice, reached by pressing its own
// button, the same as Tab or SingStar.
//
// `width` picks the scale band for Tab/SingStar's own default
// - ignored when entering Custom, since Custom restores
// whatever scale was last saved rather than setting one fresh.
// Every call site passes the real, currently-measured width
// except the one at module load below, where nothing has been
// measured yet and window.innerWidth stands in as the nearest
// available guess.
export function applyPreset(name: "tab" | "singstar" | "custom", width: number): void {
	if (viewPreset.value === name) return;

	// Leaving Custom is the one moment worth remembering: its
	// layout and both scales are whatever the player set up
	// freely, and nothing else captures that automatically.
	// Leaving Tab or SingStar for another preset has nothing
	// of its own worth saving - Tab and SingStar always reset
	// to their own fixed defaults on entry regardless.
	if (viewPreset.value === "custom") {
		savedPanels = { ...panels };
		savedLyricsScale = lyricsScale.value;
		savedNotesScale = notesScale.value;
	}

	if (name === "custom") {
		Object.assign(panels, savedPanels);
		lyricsScale.value = savedLyricsScale;
		notesScale.value = savedNotesScale;
	} else {
		Object.assign(panels, name === "tab" ? TAB_PANELS : SINGSTAR_PANELS);
		const band = scaleBand(width);
		if (name === "tab") {
			lyricsScale.value = TAB_LYRICS_SCALE[band];
		} else {
			lyricsScale.value = SINGSTAR_LYRICS_SCALE[band];
			notesScale.value = SINGSTAR_NOTES_SCALE[band];
		}
	}

	viewPreset.value = name;
}

// Jam sessions (Tab) are the more common case per the
// person's own steer, so that's the landing view - applied
// here, once, at module load, through the same function a
// button press uses. window.innerWidth stands in for the
// mixer's own container width, which Index.svelte cannot
// measure this early (nothing has mounted yet): a real
// mismatch is possible if the mixer sits in a narrow Gradio
// column on a wide window, but this is a one-time default the
// +/- controls can always correct, not a value anything else
// depends on staying right.
applyPreset("tab", typeof window !== "undefined" ? window.innerWidth : 1280);