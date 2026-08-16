# instrument_diagrams.py

"""
Where the notes of a key sit on an instrument.

A singer working out a line by ear often wants to find it
on something with frets or keys. These draw the key onto
three instruments: every note is shown, and the seven that
belong to the key are marked. Showing only the seven would
hide what a wrong note looks like, which is half of what a
diagram is for.

Nothing here holds state. Each function takes a key name
and returns a picture of it, so a change to the key box
draws a new diagram rather than updating an old one.

The pictures are SVG, built as text. Drawing them with a
plotting library would mean an image per key per
instrument and a figure to close; a fretboard is a few
rectangles and circles, and text is cheaper.
"""

from harmony import MAJOR_SCALES, RELATIVE_MINORS
from notes import NOTE_SEMITONES, SHARP_NAMES


# Flat keys spell their black notes with flats, sharp keys
# with sharps. The same sound either way; the diagram
# should agree with the boxes rather than teach a second
# name for the note the player is reading.
FLAT_NAMES = [
    "C", "Db", "D", "Eb", "E", "F",
    "Gb", "G", "Ab", "A", "Bb", "B"
]

FLAT_KEYS = {"F", "Bb", "Eb", "Ab", "Db", "Gb", "Cb"}


# The colours the app already uses for its voices, so a
# diagram sits beside the pictures without introducing a
# third palette.
IN_KEY_COLOUR = "#2e7d32"
HOME_COLOUR = "#e65100"
OFF_KEY_COLOUR = "#c8c8c8"
LINE_COLOUR = "#37474f"
LABEL_COLOUR = "#555555"


# How each string is tuned, lowest string first, as note
# names with octaves. Guitar sounds an octave below what it
# reads, which matters for nothing here: the diagram is
# about which finger position gives which note name.
STRING_TUNINGS = {
    "Guitar": ["E2", "A2", "D3", "G3", "B3", "E4"],

    # Standard re-entrant tuning: the G string is not the
    # lowest pitch (it sits between C and E), so this list is
    # not pitch-ordered the way the guitar's is - it is
    # physical string order instead, chosen so the shared
    # drawing code's reversed() places G at the top and A at
    # the bottom, the standard way a ukulele chart is drawn.
    # Nothing downstream needs the list to be pitch-sorted;
    # the drawing only ever uses list order for placement.
    "Ukulele": ["A4", "E4", "C4", "G4"],
}

# The violin's strings, lowest first, and where each hand
# position's frame begins. The stored number is one
# semitone below where the first finger's low placement
# falls, the way the nut sits one below the low first
# finger in first position.
#
# In third position the hand has shifted so the first
# finger lands where the third finger was: five semitones
# above the open string, a perfect fourth. The frame
# therefore starts at four. Writing five here was an
# off-by-one that put the whole hand a semitone sharp.
VIOLIN_STRINGS = ["G3", "D4", "A4", "E5"]

POSITION_STARTS = {
    "First position": 0,
    "Third position": 4
}

# How far above its frame a hand reaches: four fingers
# covering roughly seven semitones.
POSITION_REACH = 7

# The most fingers a hand has.
FINGERS = 4


# Layout numbers, named once so a chord overlay can find
# the exact same spot the key diagram marked. Duplicating
# these as separate literals in an overlay function would
# let the two drift apart pixel by pixel; sharing the one
# dict is what keeps a transparent overlay actually
# transparent-in-register rather than merely see-through.
PIANO_LAYOUT = {
    "octaves": 3,
    "white_width": 44,
    "white_height": 196,
    "black_width": 26,
    "black_height": 121,
}

FRETBOARD_LAYOUT = {
    "left": 46,
    "top": 26,
    "fret_width": 52,
    "string_gap": 28,
}

VIOLIN_LAYOUT = {
    "left": 46,
    "top": 26,
    "semitone_width": 60,
    "string_gap": 42,
}


def fingering_for(open_string, key, frame):
    """
    Which finger takes which note, on one string.

    The fingers are ordinal, not spaced: within a position
    the four fingers take the next four notes of the key
    in order, whatever the gaps between them happen to be.
    A key with a half step early in the hand and one with
    a whole step there use the same four fingers - they
    just sit differently, which is the whole of what a
    hand shape is.

    Mapping semitone distance to a finger instead - one
    finger per tone, with a low and a high placement each
    - stamps the same number on two notes whenever the key
    puts scale notes a half step apart inside the hand,
    and then never reaches the fourth finger at all. That
    is a model of a hand with four fixed places rather
    than four fingers.

    The open string is not here: it needs no finger, so it
    belongs to every position and is drawn at the nut
    whatever the hand is doing.
    """

    in_key = semitones_in(key)

    reachable = [
        step
        for step in range(frame + 1, frame + POSITION_REACH + 1)
        if _note_at(open_string, step) in in_key
    ]

    return [
        (step, finger)
        for finger, step in enumerate(reachable[:FINGERS], start=1)
    ]

FRETS_SHOWN = 12

# The dots inlaid on a guitar neck, which is how players
# find their place without counting.
MARKER_FRETS = {3, 5, 7, 9}


def semitones_in(key):
    """
    The seven semitone classes a key contains.

    Held as numbers rather than names so that a diagram can
    ask "is this position in the key" without knowing which
    dialect either side is spelled in.
    """

    scale = MAJOR_SCALES.get(key)

    if scale is None:
        raise KeyError(
            f"'{key}' is not a key this app knows."
        )

    return {NOTE_SEMITONES[note] % 12 for note in scale}


def name_for(semitone, key):
    """
    What to call a semitone in a given key's dialect.
    """

    if key in FLAT_KEYS:
        return FLAT_NAMES[semitone % 12]

    return SHARP_NAMES[semitone % 12]


def describe_key(key):
    """
    The key written the way the app names it elsewhere.
    """

    minor = RELATIVE_MINORS.get(key)

    if minor:
        return f"{key} major / {minor} minor"

    return key


def _note_at(open_string, fret):
    """
    The semitone sounded by a string stopped at a fret.
    """

    letter = open_string[:-1]
    octave = int(open_string[-1])

    return (NOTE_SEMITONES[letter] + octave * 12 + fret) % 12


def _escape(text):
    """
    Text safe to put inside an SVG element.
    """

    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _colour_for(semitone, key, home):
    """
    How a position is marked: home, in the key, or outside.
    """

    if semitone == home:
        return HOME_COLOUR

    if semitone in semitones_in(key):
        return IN_KEY_COLOUR

    return OFF_KEY_COLOUR


def piano_structure(octaves=None):
    """
    The keyboard on its own, no key involved - the mixer's
    always-there background layer. Same picture whatever
    key is chosen, because a keyboard's keys don't move.

    octaves is a display choice (a compact two-octave
    keyboard for a quick glance, three for the full
    pattern), not a fact about the instrument - defaults to
    PIANO_LAYOUT's own setting when not given.
    """

    parts, width, height = _piano_structure_parts(octaves)

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'width="100%" style="max-width:{width}px" '
        f'role="img" aria-label="A keyboard, '
        f'{octaves or PIANO_LAYOUT["octaves"]} octaves">'
        + "".join(parts) +
        "</svg>"
    )


def piano_scale_overlay(key, octaves=None):
    """
    Just the key's in-key marks, transparent background,
    positioned exactly as piano_diagram places them - for
    stacking on piano_structure as the mixer's Scale layer.
    """

    _, width, height = _piano_structure_parts(octaves)
    parts = _piano_scale_parts(key, octaves)

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'width="100%" style="max-width:{width}px" '
        f'role="img" aria-label="The notes of '
        f'{_escape(describe_key(key))} highlighted on a '
        f'keyboard">'
        + "".join(parts) +
        "</svg>"
    )


def piano_diagram(key, octaves=None):
    """
    A keyboard with the key's notes marked. One octave
    shows the pattern; more show it repeating, which is
    how a keyboard is actually read - a line moves across
    octaves, and the shape a hand finds is the same shape
    everywhere.

    White and black keys are drawn as they sit, because
    that is how they are found: a player looks for the
    group of two black keys, not for a pitch class.

    The marking is a spot near the front of each key, not
    a filled key. Colouring the keys themselves turns most
    of a keyboard into one block of colour and hides the
    black keys inside it, which is the shape a player is
    actually navigating by.

    Built from piano_structure and piano_scale_overlay so
    the standalone diagram and the mixer's separately
    toggleable layers can never draw the keyboard two
    different ways.
    """

    structure_parts, width, height = _piano_structure_parts(octaves)
    scale_parts = _piano_scale_parts(key, octaves)

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'width="100%" style="max-width:{width}px" '
        f'role="img" aria-label="A keyboard octave with the '
        f'notes of {_escape(describe_key(key))} marked">'
        + "".join(structure_parts) + "".join(scale_parts) +
        "</svg>"
    )


def _piano_structure_parts(octaves=None):
    """
    The keyboard itself: white and black keys, nothing
    marked on them. Key-independent - however many octaves
    are shown look the same whatever key is chosen - so
    this is the part of the picture that never needs to
    change or be toggled off.

    octaves defaults to PIANO_LAYOUT's own setting; a
    caller wanting a compact keyboard passes a smaller
    number.
    """

    octaves = octaves or PIANO_LAYOUT["octaves"]

    white_semitones = [
        semitone + octave * 12
        for octave in range(octaves)
        for semitone in [0, 2, 4, 5, 7, 9, 11]
    ]

    black_after = {
        semitone + octave * 12: raised + octave * 12
        for octave in range(octaves)
        for semitone, raised in
        {0: 1, 2: 3, 5: 6, 7: 8, 9: 10}.items()
    }

    white_width = PIANO_LAYOUT["white_width"]
    white_height = PIANO_LAYOUT["white_height"]
    black_width = PIANO_LAYOUT["black_width"]
    black_height = PIANO_LAYOUT["black_height"]

    parts = []

    for index in range(len(white_semitones)):

        x = index * white_width

        parts.append(
            f'<rect x="{x}" y="0" width="{white_width}" '
            f'height="{white_height}" fill="#ffffff" '
            f'stroke="{LINE_COLOUR}" stroke-width="1.5"/>'
        )

    for index, semitone in enumerate(white_semitones):

        raised = black_after.get(semitone)

        if raised is None:
            continue

        x = (index + 1) * white_width - black_width / 2

        parts.append(
            f'<rect x="{x}" y="0" width="{black_width}" '
            f'height="{black_height}" fill="#212121" '
            f'stroke="{LINE_COLOUR}" stroke-width="1.5"/>'
        )

    width = len(white_semitones) * white_width

    return parts, width, white_height


def _piano_scale_parts(key, octaves=None):
    """
    Just the in-key marks a piano_diagram draws on top of
    its keys - no keyboard underneath. What the mixer's
    Scale layer shows, stacked on the always-visible
    structure from _piano_structure_parts.
    """

    home = NOTE_SEMITONES[MAJOR_SCALES[key][0]] % 12
    in_key = semitones_in(key)

    octaves = octaves or PIANO_LAYOUT["octaves"]

    white_semitones = [
        semitone + octave * 12
        for octave in range(octaves)
        for semitone in [0, 2, 4, 5, 7, 9, 11]
    ]

    black_after = {
        semitone + octave * 12: raised + octave * 12
        for octave in range(octaves)
        for semitone, raised in
        {0: 1, 2: 3, 5: 6, 7: 8, 9: 10}.items()
    }

    white_width = PIANO_LAYOUT["white_width"]
    white_height = PIANO_LAYOUT["white_height"]
    black_width = PIANO_LAYOUT["black_width"]
    black_height = PIANO_LAYOUT["black_height"]

    parts = []

    def spot(x, y, semitone, radius):
        """
        The mark on a key that is in the key.
        """

        colour = (
            HOME_COLOUR if semitone % 12 == home
            else IN_KEY_COLOUR
        )

        return (
            f'<circle cx="{x}" cy="{y}" r="{radius}" '
            f'fill="{colour}"/>'
            f'<text x="{x}" y="{y + 4}" text-anchor="middle" '
            f'font-size="11" font-family="sans-serif" '
            f'fill="#ffffff">'
            f'{_escape(name_for(semitone, key))}</text>'
        )

    for index, semitone in enumerate(white_semitones):

        x = index * white_width

        if semitone % 12 in in_key:
            parts.append(
                spot(
                    x + white_width / 2,
                    white_height - 28,
                    semitone,
                    14
                )
            )

    # Black keys second, so they sit over the white ones.
    for index, semitone in enumerate(white_semitones):

        raised = black_after.get(semitone)

        if raised is None:
            continue

        x = (index + 1) * white_width - black_width / 2

        if raised % 12 in in_key:
            parts.append(
                spot(
                    x + black_width / 2,
                    black_height - 22,
                    raised,
                    12
                )
            )

    return parts


def fretboard_structure(instrument="Guitar", frets_shown=FRETS_SHOWN):
    """
    The neck itself - nut, frets, strings, fret numbers,
    inlay dots - with nothing marked on it. Key-independent:
    a fretboard is the same physical object whatever key is
    chosen, so this is the mixer's always-there background
    for a Guitar or similar string instrument.
    """

    parts, width, height = _fretboard_structure_parts(instrument, frets_shown)

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'width="100%" style="max-width:{width}px" '
        f'role="img" aria-label="A {_escape(instrument)} neck">'
        + "".join(parts) +
        "</svg>"
    )


def fretboard_scale_overlay(key, instrument="Guitar", frets_shown=FRETS_SHOWN):
    """
    Just the key's marks - every fretted position, coloured
    home/in-key/off-key - transparent background, positioned
    exactly as fretboard_diagram places them. The mixer's
    Scale layer, stacked on fretboard_structure.
    """

    _, width, height = _fretboard_structure_parts(instrument, frets_shown)
    parts = _fretboard_scale_parts(key, instrument, frets_shown)

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'width="100%" style="max-width:{width}px" '
        f'role="img" aria-label="The notes of '
        f'{_escape(describe_key(key))} highlighted on a '
        f'{_escape(instrument)} neck">'
        + "".join(parts) +
        "</svg>"
    )


def fretboard_diagram(key, instrument="Guitar", frets_shown=FRETS_SHOWN):
    """
    A fingerboard with every position marked.

    Positions outside the key are drawn faintly rather than
    left out: a player needs to see the note they should
    not play as much as the ones they should, and an empty
    space says nothing about why it is empty.

    The violin has no frets. The diagram still divides the
    neck into semitones, which is where the fingers go; the
    lines are a ruler, not a promise that anything stops
    the string there.

    Built from fretboard_structure and
    fretboard_scale_overlay so the standalone diagram and
    the mixer's separately toggleable layers can never draw
    the neck two different ways.
    """

    structure_parts, width, height = _fretboard_structure_parts(
        instrument, frets_shown
    )
    scale_parts = _fretboard_scale_parts(key, instrument, frets_shown)

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'width="100%" style="max-width:{width}px" '
        f'role="img" aria-label="A {_escape(instrument)} neck with '
        f'the notes of {_escape(describe_key(key))} marked">'
        + "".join(structure_parts) + "".join(scale_parts) +
        "</svg>"
    )


def _fretboard_structure_parts(instrument="Guitar", frets_shown=FRETS_SHOWN):
    """
    Nut, frets, strings, fret numbers, inlay dots - no key
    involved, nothing marked. Raises for an instrument this
    app cannot draw, same as the diagram functions do.

    frets_shown is a display choice (a compact neck for a
    quick glance, the full neck for anything further up),
    not a fact about the instrument - the same fretboard,
    shown shorter or longer.
    """

    tuning = STRING_TUNINGS.get(instrument)

    if tuning is None:
        raise KeyError(
            f"'{instrument}' is not an instrument this "
            f"app can draw."
        )

    left = FRETBOARD_LAYOUT["left"]
    top = FRETBOARD_LAYOUT["top"]
    fret_width = FRETBOARD_LAYOUT["fret_width"]
    string_gap = FRETBOARD_LAYOUT["string_gap"]

    height = top + (len(tuning) - 1) * string_gap + 30
    width = left + frets_shown * fret_width + 20

    parts = []

    # The inlaid dots first, behind everything.
    for fret in MARKER_FRETS:

        if fret > frets_shown:
            continue

        parts.append(
            f'<circle cx="{left + fret * fret_width - fret_width / 2}" '
            f'cy="{top + (len(tuning) - 1) * string_gap / 2}" '
            f'r="7" fill="#eceff1"/>'
        )

    for fret in range(frets_shown + 1):

        x = left + fret * fret_width

        # The nut is the thick line at the top of the neck.
        thickness = 4 if fret == 0 else 1

        parts.append(
            f'<line x1="{x}" y1="{top}" x2="{x}" '
            f'y2="{top + (len(tuning) - 1) * string_gap}" '
            f'stroke="{LINE_COLOUR}" stroke-width="{thickness}"/>'
        )

        if fret:
            parts.append(
                f'<text x="{x - fret_width / 2}" y="{height - 8}" '
                f'text-anchor="middle" font-size="11" '
                f'font-family="sans-serif" fill="{LABEL_COLOUR}">'
                f'{fret}</text>'
            )

    # Strings run left to right, lowest drawn at the bottom
    # the way a player looking down at the neck sees them.
    for index, open_string in enumerate(reversed(tuning)):

        y = top + index * string_gap

        parts.append(
            f'<line x1="{left}" y1="{y}" '
            f'x2="{left + frets_shown * fret_width}" y2="{y}" '
            f'stroke="{LINE_COLOUR}" stroke-width="1"/>'
        )

        parts.append(
            f'<text x="{left - 12}" y="{y + 4}" '
            f'text-anchor="end" font-size="12" '
            f'font-family="sans-serif" fill="{LABEL_COLOUR}">'
            f'{_escape(open_string)}</text>'
        )

    return parts, width, height


def _fretboard_scale_parts(key, instrument="Guitar", frets_shown=FRETS_SHOWN):
    """
    Just the marks fretboard_diagram draws on top of the
    neck - every fretted position, coloured home/in-key/
    off-key - no neck underneath. What the mixer's Scale
    layer shows, stacked on _fretboard_structure_parts.
    """

    tuning = STRING_TUNINGS.get(instrument)

    if tuning is None:
        raise KeyError(
            f"'{instrument}' is not an instrument this "
            f"app can draw."
        )

    home = NOTE_SEMITONES[MAJOR_SCALES[key][0]] % 12

    left = FRETBOARD_LAYOUT["left"]
    top = FRETBOARD_LAYOUT["top"]
    fret_width = FRETBOARD_LAYOUT["fret_width"]
    string_gap = FRETBOARD_LAYOUT["string_gap"]

    parts = []

    for index, open_string in enumerate(reversed(tuning)):

        y = top + index * string_gap

        for fret in range(frets_shown + 1):

            semitone = _note_at(open_string, fret)

            colour = _colour_for(semitone, key, home)

            # An open string sits on the nut; a stopped note
            # sits between its fret and the one before.
            x = (
                left if fret == 0
                else left + fret * fret_width - fret_width / 2
            )

            in_key = semitone in semitones_in(key)

            parts.append(
                f'<circle cx="{x}" cy="{y}" '
                f'r="{11 if in_key else 8}" fill="{colour}" '
                f'stroke="#ffffff" stroke-width="1.5"/>'
            )

            if in_key:
                parts.append(
                    f'<text x="{x}" y="{y + 4}" '
                    f'text-anchor="middle" font-size="10" '
                    f'font-family="sans-serif" fill="#ffffff">'
                    f'{_escape(name_for(semitone, key))}</text>'
                )

    return parts


def violin_structure(position="First position"):
    """
    The nut, the semitone ruler, and the strings - nothing
    fingered. Key-independent: the neck and the hand frame
    a position defines don't move with the key, only which
    of its marked points light up does. The mixer's
    always-there background for a violin chart.
    """

    parts, width, height = _violin_structure_parts(position)

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'width="100%" style="max-width:{width}px" '
        f'role="img" aria-label="A violin neck in '
        f'{_escape(position.lower())}">'
        + "".join(parts) +
        "</svg>"
    )


def violin_scale_overlay(key, position="First position"):
    """
    Just the key's finger marks, transparent background,
    positioned exactly as violin_chart places them - for
    stacking on violin_structure as the mixer's Scale
    layer.
    """

    _, width, height = _violin_structure_parts(position)
    parts = _violin_scale_parts(key, position)

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'width="100%" style="max-width:{width}px" '
        f'role="img" aria-label="The notes of '
        f'{_escape(describe_key(key))} highlighted on a '
        f'violin chart in {_escape(position.lower())}">'
        + "".join(parts) +
        "</svg>"
    )


def violin_chart(key, position="First position"):
    """
    A fingering chart laid along the neck.

    Horizontal like the guitar's, strings as lines with the
    lowest at the bottom, and the ruler underneath counting
    semitones from the open string - so the two position
    charts share one map of the neck, and third position
    visibly sits further along it than first.

    Each mark is a finger number, which is what a violinist
    reads, with the note name small beside it. Placement is
    proportional to semitones, so the half-step pairs that
    make one key's hand shape differ from another's show as
    geometry.

    The open string is drawn at the nut in every position:
    it needs no finger, so no shift takes it away. What a
    shifted hand loses is the nut itself - its first finger
    starts five semitones up, where the third finger was.

    Only the key's notes are drawn, on a faint semitone
    ruler: this is a picture of a hand shape, not a map of
    every destination the way the guitar's is.

    Built from violin_structure and violin_scale_overlay so
    the standalone chart and the mixer's separately
    toggleable layers can never draw the neck two different
    ways.
    """

    structure_parts, width, height = _violin_structure_parts(position)
    scale_parts = _violin_scale_parts(key, position)

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'width="100%" style="max-width:{width}px" '
        f'role="img" aria-label="A violin chart of '
        f'{_escape(describe_key(key))} in '
        f'{_escape(position.lower())}, along the neck">'
        + "".join(structure_parts) + "".join(scale_parts) +
        "</svg>"
    )


def _violin_structure_parts(position="First position"):
    """
    The nut, the semitone ruler, and the strings - no key
    involved, nothing fingered. Raises for an unknown
    position, same as violin_chart does.
    """

    start = POSITION_STARTS.get(position)

    if start is None:
        raise KeyError(
            f"'{position}' is not a position this app "
            f"can draw."
        )

    furthest = start + POSITION_REACH

    left = VIOLIN_LAYOUT["left"]
    top = VIOLIN_LAYOUT["top"]
    semitone_width = VIOLIN_LAYOUT["semitone_width"]
    string_gap = VIOLIN_LAYOUT["string_gap"]

    height = top + (len(VIOLIN_STRINGS) - 1) * string_gap + 44
    width = left + furthest * semitone_width + 30

    parts = []

    strings_bottom = top + (len(VIOLIN_STRINGS) - 1) * string_gap

    # The nut.
    parts.append(
        f'<line x1="{left}" y1="{top - 8}" x2="{left}" '
        f'y2="{strings_bottom + 8}" '
        f'stroke="{LINE_COLOUR}" stroke-width="5"/>'
    )

    # The semitone ruler: faint lines, counted underneath.
    for step in range(1, furthest + 1):

        x = left + step * semitone_width

        parts.append(
            f'<line x1="{x}" y1="{top - 4}" x2="{x}" '
            f'y2="{strings_bottom + 4}" '
            f'stroke="#eceff1" stroke-width="1"/>'
        )

        parts.append(
            f'<text x="{x}" y="{height - 8}" '
            f'text-anchor="middle" font-size="11" '
            f'font-family="sans-serif" fill="{LABEL_COLOUR}">'
            f'{step}</text>'
        )

    # Strings left to right along the neck, lowest at the
    # bottom the way a player looking down sees them.
    for index, open_string in enumerate(reversed(VIOLIN_STRINGS)):

        y = top + index * string_gap

        parts.append(
            f'<line x1="{left}" y1="{y}" '
            f'x2="{left + furthest * semitone_width}" y2="{y}" '
            f'stroke="{LINE_COLOUR}" stroke-width="1.5"/>'
        )

        parts.append(
            f'<text x="{left - 12}" y="{y + 4}" '
            f'text-anchor="end" font-size="12" '
            f'font-family="sans-serif" fill="{LABEL_COLOUR}">'
            f'{_escape(open_string)}</text>'
        )

    return parts, width, height


def _violin_scale_parts(key, position="First position"):
    """
    Just the finger marks violin_chart draws on top of the
    neck - no ruler or strings underneath. What the mixer's
    Scale layer shows, stacked on
    _violin_structure_parts.
    """

    start = POSITION_STARTS.get(position)

    if start is None:
        raise KeyError(
            f"'{position}' is not a position this app "
            f"can draw."
        )

    home = NOTE_SEMITONES[MAJOR_SCALES[key][0]] % 12
    in_key = semitones_in(key)

    left = VIOLIN_LAYOUT["left"]
    top = VIOLIN_LAYOUT["top"]
    semitone_width = VIOLIN_LAYOUT["semitone_width"]
    string_gap = VIOLIN_LAYOUT["string_gap"]

    parts = []

    for index, open_string in enumerate(reversed(VIOLIN_STRINGS)):

        y = top + index * string_gap

        def mark(step, finger):
            """
            One finger's place on this string, if in key.
            """

            semitone = _note_at(open_string, step)

            if semitone not in in_key:
                return

            x = left + step * semitone_width

            colour = (
                HOME_COLOUR if semitone == home
                else IN_KEY_COLOUR
            )

            parts.append(
                f'<circle cx="{x}" cy="{y}" r="12" '
                f'fill="{colour}" stroke="#ffffff" '
                f'stroke-width="1.5"/>'
            )

            parts.append(
                f'<text x="{x}" y="{y + 4}" '
                f'text-anchor="middle" font-size="12" '
                f'font-family="sans-serif" fill="#ffffff">'
                f'{finger}</text>'
            )

            parts.append(
                f'<text x="{x + 15}" y="{y - 9}" '
                f'text-anchor="start" font-size="9" '
                f'font-family="sans-serif" '
                f'fill="{LABEL_COLOUR}">'
                f'{_escape(name_for(semitone, key))}</text>'
            )

        # The open string, in every position.
        mark(0, 0)

        for step, finger in fingering_for(open_string, key, start):
            mark(step, finger)

    return parts


def _violin_scale_parts_both(key):
    """
    The Scale layer's marks for both hand positions at once:
    a note reachable from only one position gets a plain
    fill in that position's colour, a note reachable from
    both gets the split fill - and either way the ring stays
    green or orange, exactly as the single-position layer
    already means it. Checked against real fingering_for
    output for all 12 keys: every one produces at least some
    overlap, so the split mark is never a dead code path.
    """

    home = NOTE_SEMITONES[MAJOR_SCALES[key][0]] % 12
    in_key = semitones_in(key)

    left = VIOLIN_LAYOUT["left"]
    top = VIOLIN_LAYOUT["top"]
    semitone_width = VIOLIN_LAYOUT["semitone_width"]
    string_gap = VIOLIN_LAYOUT["string_gap"]

    parts = []

    for index, open_string in enumerate(reversed(VIOLIN_STRINGS)):

        y = top + index * string_gap

        first_map = {0: 0}
        first_map.update(
            fingering_for(
                open_string, key, POSITION_STARTS["First position"]
            )
        )

        third_map = {0: 0}
        third_map.update(
            fingering_for(
                open_string, key, POSITION_STARTS["Third position"]
            )
        )

        for step in sorted(set(first_map) | set(third_map)):

            semitone = _note_at(open_string, step)

            if semitone not in in_key:
                continue

            in_first = step in first_map
            in_third = step in third_map

            label = None

            if in_first and not in_third:
                label = first_map[step]
            elif in_third and not in_first:
                label = third_map[step]

            x = left + step * semitone_width
            ring_colour = HOME_COLOUR if semitone == home else IN_KEY_COLOUR

            parts.append(
                _dual_position_dot(
                    x, y, in_first, in_third, ring_colour, label
                )
            )

            parts.append(
                f'<text x="{x + 15}" y="{y - 9}" '
                f'text-anchor="start" font-size="9" '
                f'font-family="sans-serif" '
                f'fill="{LABEL_COLOUR}">'
                f'{_escape(name_for(semitone, key))}</text>'
            )

    return parts


def violin_scale_overlay_both(key):
    """
    The Scale layer for "Violin, both positions" - both hand
    positions' finger marks on one transparent chart, stacked
    on violin_structure("Third position"): third position's
    own reach already spans semitones 0 through 11, exactly
    what combining first (0-7) and third (4-11) needs, so no
    new width or ruler logic was required - the structure
    layer for "both" is literally identical to third
    position's own.
    """

    _, width, height = _violin_structure_parts("Third position")
    parts = _violin_scale_parts_both(key)

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'width="100%" style="max-width:{width}px" '
        f'role="img" aria-label="The notes of '
        f'{_escape(describe_key(key))} highlighted on a '
        f'violin chart across both hand positions">'
        + "".join(parts) +
        "</svg>"
    )


def violin_chart_both(key):
    """
    The standalone combined chart - structure plus both
    positions' scale marks - the "both positions" equivalent
    of violin_chart.
    """

    structure_parts, width, height = _violin_structure_parts(
        "Third position"
    )
    scale_parts = _violin_scale_parts_both(key)

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'width="100%" style="max-width:{width}px" '
        f'role="img" aria-label="A violin chart of '
        f'{_escape(describe_key(key))} across both hand '
        f'positions, along the neck">'
        + "".join(structure_parts) + "".join(scale_parts) +
        "</svg>"
    )


# The mixer overlay's mark, drawn heavier than the scale
# diagram's so a chord tone that is also a scale note is
# still visibly the thing being played right now, not just
# a note that happens to belong to the key.
CHORD_TONE_COLOUR = "#ad1457"

# The played-shape overlay's own colours, distinct from
# every other layer on purpose: Scale, Chord notes and
# Chord shape are independent layers that can all be on at
# once (all the places a chord's notes fall, plus the one
# beginner voicing, useful together for finding
# accompaniment or an arpeggio beyond the fixed shape) - if
# any two layers shared a colour, a mark from one would sit
# invisibly on top of a matching mark from the other,
# exactly where the distinction matters most. Purple is the
# one hue nothing else on this picture already uses: green
# and orange belong to Scale, magenta to Chord notes, and
# piano's own left hand gets a further distinction from its
# right, since a two-handed shape has that to say too.
SHAPE_COLOUR = "#6a1b9a"
LEFT_HAND_COLOUR = "#1565c0"
RIGHT_HAND_COLOUR = SHAPE_COLOUR

# The second hand position's own colour, for the dual-
# position display (guitar and ukulele's higher barre shape,
# violin's third position). Teal is the one hue left in the
# app's palette once green, orange, magenta, purple and blue
# are already spoken for. A note reachable from both
# positions gets a split mark, half SHAPE_COLOUR and half
# this one - not a third colour, which would throw away the
# information of which two positions are overlapping.
HIGHER_SHAPE_COLOUR = "#00838f"


def piano_chord_overlay(key, chord_semitone_set, octaves=None):
    """
    Chord tones only, on a transparent piano, positioned
    exactly as piano_diagram places its marks - same
    PIANO_LAYOUT, so the two stack in register when the
    mixer shows both.

    Nothing outside the chord is drawn: no keys, no scale
    marks. A caller wanting the key underneath draws
    piano_diagram separately and layers this on top.
    """

    octaves = octaves or PIANO_LAYOUT["octaves"]
    white_width = PIANO_LAYOUT["white_width"]
    white_height = PIANO_LAYOUT["white_height"]
    black_width = PIANO_LAYOUT["black_width"]
    black_height = PIANO_LAYOUT["black_height"]

    white_semitones = [
        semitone + octave * 12
        for octave in range(octaves)
        for semitone in [0, 2, 4, 5, 7, 9, 11]
    ]

    black_after = {
        semitone + octave * 12: raised + octave * 12
        for octave in range(octaves)
        for semitone, raised in
        {0: 1, 2: 3, 5: 6, 7: 8, 9: 10}.items()
    }

    parts = []

    def spot(x, y, semitone, radius):
        return (
            f'<circle cx="{x}" cy="{y}" r="{radius}" '
            f'fill="{CHORD_TONE_COLOUR}"/>'
            f'<text x="{x}" y="{y + 4}" text-anchor="middle" '
            f'font-size="11" font-family="sans-serif" '
            f'fill="#ffffff">'
            f'{_escape(name_for(semitone, key))}</text>'
        )

    for index, semitone in enumerate(white_semitones):

        if semitone % 12 not in chord_semitone_set:
            continue

        x = index * white_width

        parts.append(
            spot(x + white_width / 2, white_height - 28, semitone, 14)
        )

    for index, semitone in enumerate(white_semitones):

        raised = black_after.get(semitone)

        if raised is None or raised % 12 not in chord_semitone_set:
            continue

        x = (index + 1) * white_width - black_width / 2

        parts.append(
            spot(x + black_width / 2, black_height - 22, raised, 12)
        )

    width = len(white_semitones) * white_width

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {white_height}" '
        f'width="100%" style="max-width:{width}px" '
        f'role="img" aria-label="The chord tones highlighted '
        f'on a keyboard">'
        + "".join(parts) +
        "</svg>"
    )


def fretboard_chord_overlay(key, chord_semitone_set, instrument="Guitar",
                             frets_shown=FRETS_SHOWN):
    """
    Chord tones only, on a transparent fretboard, at the
    same coordinates fretboard_diagram uses - same
    FRETBOARD_LAYOUT, same frets_shown, so it stacks in
    register.
    """

    tuning = STRING_TUNINGS.get(instrument)

    if tuning is None:
        raise KeyError(
            f"'{instrument}' is not an instrument this "
            f"app can draw."
        )

    left = FRETBOARD_LAYOUT["left"]
    top = FRETBOARD_LAYOUT["top"]
    fret_width = FRETBOARD_LAYOUT["fret_width"]
    string_gap = FRETBOARD_LAYOUT["string_gap"]

    height = top + (len(tuning) - 1) * string_gap + 30
    width = left + frets_shown * fret_width + 20

    parts = []

    for index, open_string in enumerate(reversed(tuning)):

        y = top + index * string_gap

        for fret in range(frets_shown + 1):

            semitone = _note_at(open_string, fret)

            if semitone not in chord_semitone_set:
                continue

            x = (
                left if fret == 0
                else left + fret * fret_width - fret_width / 2
            )

            parts.append(
                f'<circle cx="{x}" cy="{y}" r="11" '
                f'fill="{CHORD_TONE_COLOUR}" '
                f'stroke="#ffffff" stroke-width="1.5"/>'
                f'<text x="{x}" y="{y + 4}" '
                f'text-anchor="middle" font-size="10" '
                f'font-family="sans-serif" fill="#ffffff">'
                f'{_escape(name_for(semitone, key))}</text>'
            )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'width="100%" style="max-width:{width}px" '
        f'role="img" aria-label="The chord tones highlighted '
        f'on a {_escape(instrument)} neck">'
        + "".join(parts) +
        "</svg>"
    )


def violin_chord_overlay(key, chord_semitone_set, position="First position"):
    """
    Chord tones only, on a transparent violin chart, at the
    same coordinates violin_chart uses - same VIOLIN_LAYOUT
    and the same fingering_for hand shape, so it stacks in
    register and only marks fingers the hand actually plays
    in this position.
    """

    start = POSITION_STARTS.get(position)

    if start is None:
        raise KeyError(
            f"'{position}' is not a position this app "
            f"can draw."
        )

    left = VIOLIN_LAYOUT["left"]
    top = VIOLIN_LAYOUT["top"]
    semitone_width = VIOLIN_LAYOUT["semitone_width"]
    string_gap = VIOLIN_LAYOUT["string_gap"]

    furthest = start + POSITION_REACH
    height = top + (len(VIOLIN_STRINGS) - 1) * string_gap + 44
    width = left + furthest * semitone_width + 30

    parts = []

    for index, open_string in enumerate(reversed(VIOLIN_STRINGS)):

        y = top + index * string_gap

        def mark(step, finger):

            semitone = _note_at(open_string, step)

            if semitone not in chord_semitone_set:
                return

            x = left + step * semitone_width

            parts.append(
                f'<circle cx="{x}" cy="{y}" r="12" '
                f'fill="{CHORD_TONE_COLOUR}" '
                f'stroke="#ffffff" stroke-width="1.5"/>'
                f'<text x="{x}" y="{y + 4}" '
                f'text-anchor="middle" font-size="12" '
                f'font-family="sans-serif" fill="#ffffff">'
                f'{finger}</text>'
                f'<text x="{x + 15}" y="{y - 9}" '
                f'text-anchor="start" font-size="9" '
                f'font-family="sans-serif" fill="{LABEL_COLOUR}">'
                f'{_escape(name_for(semitone, key))}</text>'
            )

        mark(0, 0)

        for step, finger in fingering_for(open_string, key, start):
            mark(step, finger)

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'width="100%" style="max-width:{width}px" '
        f'role="img" aria-label="The chord tones highlighted '
        f'on a violin chart in {_escape(position.lower())}">'
        + "".join(parts) +
        "</svg>"
    )


def violin_chord_overlay_both(key, chord_semitone_set):
    """
    The Chord-notes layer for "Violin, both positions" - the
    fill still means position (split where both positions
    reach a chord tone, exactly like Scale), but the ring
    stays CHORD_TONE_COLOUR always, since Chord-notes has
    only the one thing to say - unlike Scale, there is no
    competing home-vs-in-key meaning here to protect. Keeping
    it a fixed colour, distinct from Scale's green/orange
    ring, is what keeps the two layers tellable apart when
    both are toggled on together.
    """

    left = VIOLIN_LAYOUT["left"]
    top = VIOLIN_LAYOUT["top"]
    semitone_width = VIOLIN_LAYOUT["semitone_width"]
    string_gap = VIOLIN_LAYOUT["string_gap"]

    _, width, height = _violin_structure_parts("Third position")

    parts = []

    for index, open_string in enumerate(reversed(VIOLIN_STRINGS)):

        y = top + index * string_gap

        first_map = {0: 0}
        first_map.update(
            fingering_for(
                open_string, key, POSITION_STARTS["First position"]
            )
        )

        third_map = {0: 0}
        third_map.update(
            fingering_for(
                open_string, key, POSITION_STARTS["Third position"]
            )
        )

        for step in sorted(set(first_map) | set(third_map)):

            semitone = _note_at(open_string, step)

            if semitone not in chord_semitone_set:
                continue

            in_first = step in first_map
            in_third = step in third_map

            label = None

            if in_first and not in_third:
                label = first_map[step]
            elif in_third and not in_first:
                label = third_map[step]

            x = left + step * semitone_width

            parts.append(
                _dual_position_dot(
                    x, y, in_first, in_third, CHORD_TONE_COLOUR, label
                )
            )

            parts.append(
                f'<text x="{x + 15}" y="{y - 9}" '
                f'text-anchor="start" font-size="9" '
                f'font-family="sans-serif" fill="{LABEL_COLOUR}">'
                f'{_escape(name_for(semitone, key))}</text>'
            )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'width="100%" style="max-width:{width}px" '
        f'role="img" aria-label="The chord tones highlighted '
        f'on a violin chart across both hand positions">'
        + "".join(parts) +
        "</svg>"
    )


def _violin_position_for(instrument):
    """
    Which position an "instrument" string like "Violin,
    third position" names, shared by every function that
    dispatches on the INSTRUMENTS list so the parsing
    lives in one place.

    "Violin, both positions" correctly falls through to
    "First position" here - the violin's Chord shape layer
    (a double stop) is only ever a first-position shape (see
    violin_chord_shape_overlay), so shape_overlay_for's
    dispatch needs exactly that value even in "both" mode.
    Structure, Scale and Chord-notes have their own separate
    "both" dispatch (_violin_shows_both) that is checked
    before this function is ever reached for those layers.
    """

    return (
        "Third position" if "third" in instrument
        else "First position"
    )


def _violin_shows_both(instrument):
    """
    Whether "instrument" names the combined-position violin
    entry - "Violin, both positions" - which shows Structure,
    Scale and Chord-notes across both hand positions at once
    rather than just one.
    """

    return "both" in instrument.lower()


def _dual_position_dot(x, y, in_first, in_third, ring_colour,
                        label=None, radius=12):
    """
    One mark on a violin diagram, encoding two independent
    things at once: which hand position(s) reach this note
    (the fill - SHAPE_COLOUR for first position only,
    HIGHER_SHAPE_COLOUR for third only, a split half-and-half
    fill for both, matching the same split style guitar and
    ukulele use for their own higher-position marks) and
    whatever ring_colour is asked to carry separately (Scale
    passes home-vs-in-key; Chord-notes passes its own fixed
    chord-tone colour, since it has only one thing to say).

    label is omitted, not guessed, when the note is reachable
    from both positions and the two positions would give it
    different finger numbers - the same reasoning guitar and
    ukulele's own split marks use.
    """

    if in_first and in_third:
        shape = (
            f'<path d="M{x} {y - radius} A{radius} {radius} 0 0 1 '
            f'{x} {y + radius} Z" fill="{HIGHER_SHAPE_COLOUR}"/>'
            f'<path d="M{x} {y - radius} A{radius} {radius} 0 0 0 '
            f'{x} {y + radius} Z" fill="{SHAPE_COLOUR}"/>'
        )
    else:
        fill = SHAPE_COLOUR if in_first else HIGHER_SHAPE_COLOUR
        shape = f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{fill}"/>'

    ring = (
        f'<circle cx="{x}" cy="{y}" r="{radius}" fill="none" '
        f'stroke="{ring_colour}" stroke-width="2.5"/>'
    )

    text = (
        f'<text x="{x}" y="{y + 4}" text-anchor="middle" '
        f'font-size="12" font-family="sans-serif" '
        f'fill="#ffffff">{label}</text>'
        if label is not None else ""
    )

    return shape + ring + text


def _base_instrument_name(instrument):
    """
    The instrument family an "instrument" string like
    "Piano, 2 octaves" or "Guitar, 8 frets" names, with any
    size variant stripped off - the part STRING_TUNINGS and
    every drawing function actually key on.
    """

    return instrument.split(",")[0]


def _octaves_for(instrument):
    """
    How many octaves a "Piano, N octaves" string asks for -
    a display choice, not a fact about the instrument,
    parsed here once so every dispatcher agrees.
    """

    return 2 if "2" in instrument else PIANO_LAYOUT["octaves"]


def _frets_shown_for(instrument):
    """
    How many frets a "Guitar, N frets" or "Ukulele, N
    frets" string asks for - a display choice, not a fact
    about the instrument, parsed here once so every
    dispatcher agrees.

    Guitar and ukulele don't share one compact/full pair:
    guitar's compact option is 8, checked directly against
    every guitar shape this app draws (major, minor,
    dominant, minor-seventh, all twelve roots) - 8 is the
    actual highest fret any of them uses (the Eb family's
    barre reaches it), and a smaller cutoff would have
    sliced that shape off mid-picture. Ukulele's own shapes
    never pass fret 4, and its short scale means a player is
    less likely to go far up the neck at all, so both its
    options - 6 and 10 - are smaller than guitar's, not the
    same numbers reused out of habit.

    Reads the number straight out of the instrument string
    rather than special-casing each pair here, so Python's
    INSTRUMENTS list stays the one place these numbers are
    decided.
    """

    import re

    match = re.search(r"\d+", instrument)

    return int(match.group()) if match else FRETS_SHOWN


def structure_for(instrument):
    """
    The always-there background picture of one instrument -
    no key involved. The mixer's base layer, drawn once and
    never toggled off.

    instrument may carry a size variant ("Piano, 2 octaves",
    "Guitar, 8 frets") - a display choice parsed out here,
    not a different instrument.
    """

    base = _base_instrument_name(instrument)

    if base == "Piano":
        return piano_structure(_octaves_for(instrument))

    if base.startswith("Violin"):
        if _violin_shows_both(instrument):
            # Structurally identical to third position alone -
            # see violin_scale_overlay_both's docstring for why.
            return violin_structure("Third position")
        return violin_structure(_violin_position_for(instrument))

    return fretboard_structure(base, _frets_shown_for(instrument))


def scale_overlay_for(key, instrument):
    """
    The key's-notes-only picture of one instrument,
    transparent background, positioned to stack exactly on
    structure_for(instrument). The mixer's Scale layer.
    """

    base = _base_instrument_name(instrument)

    if base == "Piano":
        return piano_scale_overlay(key, _octaves_for(instrument))

    if base.startswith("Violin"):
        if _violin_shows_both(instrument):
            return violin_scale_overlay_both(key)
        return violin_scale_overlay(key, _violin_position_for(instrument))

    return fretboard_scale_overlay(key, base, _frets_shown_for(instrument))


# A beginner's shape, not the theory - one concrete place
# to put the hand, rather than every place the chord's
# notes occur. Only the four qualities most beginner charts
# actually use; a quality with no settled standard shape
# reports that honestly rather than guessing one.
#
# True open shapes are hand-written where a beginner
# songbook would show one - these have their own idiosyncratic
# fingerings, not reducible to a movable pattern. Everything
# else uses the standard movable barre shape (E-shape or
# A-shape, whichever needs the lower fret): at fret 0 this
# reduces exactly to the real open E/Em/E7/Em7 and A/Am/A7/
# Am7 chords, and elsewhere it gives the same barre shape a
# guitar teacher would show - a barre chord is not a
# fallback here, it is the standard shape, and drawing it
# honestly shows the difficulty that is really there.
#
# Each entry is (fret, finger) per string, low E to high e.
# fret is None for a muted string; finger is None for an
# open string.
GUITAR_TRUE_OPENS = {
    ("C", ""): [
        (None, None), (3, 3), (2, 2), (0, None), (1, 1), (0, None)
    ],
    ("D", ""): [
        (None, None), (None, None), (0, None), (2, 1), (3, 3), (2, 2)
    ],
    ("G", ""): [
        (3, 3), (2, 2), (0, None), (0, None), (0, None), (3, 4)
    ],
    ("D", "m"): [
        (None, None), (None, None), (0, None), (2, 2), (3, 3), (1, 1)
    ],
    ("C", "7"): [
        (None, None), (3, 3), (2, 2), (3, 4), (1, 1), (0, None)
    ],
    ("D", "7"): [
        (None, None), (None, None), (0, None), (2, 2), (1, 1), (2, 3)
    ],
    ("G", "7"): [
        (3, 3), (2, 2), (0, None), (0, None), (0, None), (1, 1)
    ],
}

# Fret offset from the barre, low E to high e - None for a
# muted string. At offset 0 (the barre itself, or open when
# the whole shape sits at fret 0) no separate finger is
# drawn for that string; the barre bar or the string itself
# already says it.
GUITAR_E_SHAPE = {
    "": [0, 2, 2, 1, 0, 0],
    "m": [0, 2, 2, 0, 0, 0],
    "7": [0, 2, 0, 1, 0, 0],
    "m7": [0, 2, 0, 0, 0, 0],
}
GUITAR_A_SHAPE = {
    "": [None, 0, 2, 2, 2, 0],
    "m": [None, 0, 2, 2, 1, 0],
    "7": [None, 0, 2, 0, 2, 0],
    "m7": [None, 0, 2, 0, 1, 0],
}


def guitar_shape_frets(root, quality):
    """
    The standard beginner shape for one chord: (fret, finger)
    per string, low E to high e, and the fret a barre bar
    should be drawn at (None where there is no barre - a
    true open shape, or a movable shape sitting at fret 0).

    Returns None if this quality has no standard shape to
    show - invariant 6's choice: a gap here is more honest
    than a guessed fingering.
    """

    if quality not in GUITAR_E_SHAPE:
        return None

    opened = GUITAR_TRUE_OPENS.get((root, quality))

    if opened is not None:
        return opened, None

    root_semitone = NOTE_SEMITONES[root] % 12
    e_fret = (root_semitone - NOTE_SEMITONES["E"]) % 12
    a_fret = (root_semitone - NOTE_SEMITONES["A"]) % 12

    if a_fret < e_fret:
        template, barre = GUITAR_A_SHAPE[quality], a_fret
    else:
        template, barre = GUITAR_E_SHAPE[quality], e_fret

    frets = []

    for offset in template:

        if offset is None:
            frets.append((None, None))
            continue

        fret = offset + barre

        if fret == 0:
            frets.append((0, None))
        elif fret == barre and barre > 0:
            frets.append((fret, 1))
        else:
            frets.append((fret, None))

    return frets, (barre if barre > 0 else None)


def _apply_guitar_template(template, barre):
    """
    Turn one movable template (E-shape or A-shape) plus a
    barre fret into the same (fret, finger) per string shape
    guitar_shape_frets returns - shared by both the lower
    and the higher position, so the two can never drift into
    different fingering conventions.
    """

    frets = []

    for offset in template:

        if offset is None:
            frets.append((None, None))
            continue

        fret = offset + barre

        if fret == 0:
            frets.append((0, None))
        elif fret == barre and barre > 0:
            frets.append((fret, 1))
        else:
            frets.append((fret, None))

    return frets


def guitar_shape_frets_higher(root, quality):
    """
    The second natural hand position for one chord: whichever
    of the E-shape or A-shape barre guitar_shape_frets did
    NOT use as the lower position - the shape it has always
    computed internally and discarded.

    Returns this movable position even where guitar_shape_frets
    shows a true open shape instead of a barre for the lower
    position (C, D, G and their sevenths): the open shape is a
    hand-picked substitute for the low barre, not a different
    chord, so the movable barre position it stands in for is
    still a genuine higher-position alternative to show.

    None where guitar_shape_frets would also return None - a
    quality with no standard shape has no higher position
    either.

    Checked against every root/quality combination this app
    draws (48 total): the gap between this and the lower
    position is always at least 3 frets, and the highest fret
    this ever needs is 13 (the Eb/Ab family) - this is why the
    guitar entry in INSTRUMENTS was widened to 13 frets.
    """

    if quality not in GUITAR_E_SHAPE:
        return None

    root_semitone = NOTE_SEMITONES[root] % 12
    e_fret = (root_semitone - NOTE_SEMITONES["E"]) % 12
    a_fret = (root_semitone - NOTE_SEMITONES["A"]) % 12

    if a_fret < e_fret:
        template, barre = GUITAR_E_SHAPE[quality], e_fret
    else:
        template, barre = GUITAR_A_SHAPE[quality], a_fret

    frets = _apply_guitar_template(template, barre)

    return frets, (barre if barre > 0 else None)


# Standard ukulele chord shapes, fret per string in tuning
# order (matching STRING_TUNINGS["Ukulele"]: A, E, C, G) -
# not the G/C/E/A order a chart displays them in, which is
# the reverse. Getting this backwards would silently swap
# which string each fret lands on, since the drawing code
# below indexes this list the same way it indexes guitar's -
# by tuning order, not display order - and ukulele's tuning
# list is deliberately not in display order to begin with
# (chosen so the shared reversed()-based layout puts G at
# the top and A at the bottom, the standard way a ukulele
# chart is drawn).
#
# Ukulele is not a transposed guitar - a different tuning
# means genuinely different shapes, not the same fingering
# moved around - so this is its own table, not guitar's
# reused or adapted.
#
# Every entry here is checked against chord_semitones before
# being trusted: every fretted or open note belongs to the
# chord, and the root is present. That check is real
# evidence the shape plays the right chord; it is not
# evidence this is the one standard fingering a given teacher
# would show, since ukulele - four strings, no single settled
# CAGED-style system the way guitar has - does not have one
# universally agreed shape per chord the way some guitar
# chords do. Only the seven natural-note roots are covered
# for the same reason: confidence in a shape actually being
# standard practice, not just correct, matters here, and
# that confidence runs out at the accidentals.
UKULELE_SHAPES = {
    ("C", ""): [3, 0, 0, 0],
    ("D", ""): [0, 2, 2, 2],
    ("E", ""): [2, 4, 4, 4],
    ("F", ""): [0, 1, 0, 2],
    ("G", ""): [2, 3, 2, 0],
    ("A", ""): [0, 0, 1, 2],
    ("B", ""): [2, 2, 3, 4],
    ("C", "m"): [3, 3, 3, 0],
    ("D", "m"): [0, 1, 2, 2],
    ("E", "m"): [2, 3, 4, 0],
    ("F", "m"): [3, 1, 0, 1],
    ("G", "m"): [1, 3, 2, 0],
    ("A", "m"): [0, 0, 0, 2],
    ("B", "m"): [2, 2, 2, 4],
    # The five accidental roots, added after Bb was reported
    # missing and it turned out the right fix wasn't a
    # computed fallback (see BUILDNOTES.md) but real
    # fingerings, hand-verified against chord_semitones the
    # same way as the seven above. Sourced against
    # ukulele-chords.com's own diagrams and cross-checked
    # note-for-note, not just trusted from the page.
    #
    # Db minor is the one exception: its own real chart shape
    # ("1,1,0,x" - the A string deliberately not played) needs
    # a muted string, which this table's plain fret-per-string
    # format has no way to express. Given a genuine choice
    # here, a fully-fretted, chord-tone-correct shape
    # ([4,4,4,6], the B-minor closed shape slid up two frets)
    # was kept instead of quietly quoting a shape this format
    # can't actually represent. Muted-string support would be
    # a real change to the finger-assignment and drawing code,
    # not a table edit - flagged, not built here.
    ("Db", ""): [4, 1, 1, 1],
    ("Db", "m"): [4, 4, 4, 6],
    ("Eb", ""): [1, 3, 3, 3],
    ("Eb", "m"): [1, 2, 3, 3],
    ("Gb", ""): [1, 2, 1, 3],
    ("Gb", "m"): [0, 2, 1, 2],
    ("Ab", ""): [3, 4, 3, 5],
    ("Ab", "m"): [2, 4, 3, 4],
    ("Bb", ""): [1, 1, 2, 3],
    ("Bb", "m"): [1, 1, 1, 3],
}


# B and Bm are ukulele's only fully closed shapes in
# UKULELE_SHAPES - no open strings - which means they can be
# slid by a constant number of frets to land on any other
# root, the same idea as a guitar barre, just with no actual
# barre finger needed since ukulele only has four strings.
# Used below for the "higher position" (second hand shape)
# feature only - every root's own PRIMARY shape is now a real,
# hand-verified fingering in UKULELE_SHAPES above, not a
# computed slide of this anchor. An earlier version of this
# file used the same slide to fill in the primary table's
# gaps (Db, Eb, Gb, Ab, Bb); real reference fingerings turned
# out to be lower and more idiomatic than what the slide
# produced (Gb, for one, has a genuine 1-2-1-3 shape at frets
# 1-3, not the slide's fret 9-11 barre) - see BUILDNOTES.md.
_UKULELE_CLOSED_ANCHOR = {"": [2, 2, 3, 4], "m": [2, 2, 2, 4]}


def ukulele_shape_frets(root, quality):
    """
    The standard shape for one chord on ukulele: (fret,
    finger) per string in tuning order (A, E, C, G) - None
    for a quality this table does not cover. Every root of
    every quality this app supports (major, minor) now has a
    real, hand-verified entry.

    Finger numbers are only given where they are genuinely
    certain: open (no finger needed) and barre (two or more
    strings pressed by the same finger at the same fret,
    which is finger 1 by near-universal convention wherever
    it happens). Every other fretted note is a plain,
    correctly positioned mark with no finger claimed - the
    fret position is verified against the chord's actual
    tones; which finger a teacher would choose for it is
    not, and guessing one would be presenting a guess as
    settled fact.
    """

    frets = UKULELE_SHAPES.get((root, quality))

    if frets is None:
        return None

    fretted = [fret for fret in frets if fret > 0]
    barre_fret = next(
        (fret for fret in fretted if fretted.count(fret) > 1), None
    )

    result = []

    for fret in frets:

        if fret == 0:
            result.append((0, None))
        elif fret == barre_fret:
            result.append((fret, 1))
        else:
            result.append((fret, None))

    return result, barre_fret


# Only the roots whose shifted shape lands within ukulele's
# own 10-fret full range, and excluding B/Bm itself (shift 0
# - that root IS the anchor shape already, nothing "higher"
# to show). G and A need frets 12 and 14, past where a
# soprano neck is comfortably playable at all - not a
# limitation to raise the fret count for, since there is no
# realistic melody position up there for the chord shape to
# serve. C and Cm are kept despite the higher shape's lowest
# fret landing on the primary shape's own fret - overlap is
# not a defect here, it is exactly what the dual-colour mark
# exists to show honestly.
_UKULELE_HIGHER_ROOTS = {"C", "D", "E", "F"}


def ukulele_shape_frets_higher(root, quality):
    """
    The second hand position for one ukulele chord: the B or
    Bm closed shape, shifted up the neck to this root. None
    for any root/quality this app has not verified fits the
    instrument's real playable range (see
    _UKULELE_HIGHER_ROOTS) or for a quality with no closed
    anchor shape to shift.
    """

    if root not in _UKULELE_HIGHER_ROOTS:
        return None

    if quality not in _UKULELE_CLOSED_ANCHOR:
        return None

    shift = (NOTE_SEMITONES[root] - NOTE_SEMITONES["B"]) % 12
    frets = [fret + shift for fret in _UKULELE_CLOSED_ANCHOR[quality]]

    barre_fret = next(
        (fret for fret in frets if frets.count(fret) > 1), None
    )

    result = [
        (fret, 1) if fret == barre_fret else (fret, None)
        for fret in frets
    ]

    return result, barre_fret


def piano_shape_for(root, quality):
    """
    A beginner's two-hand voicing for one chord: left hand
    plays the root and its fifth (fingers 5 and 1), right
    hand plays the triad in root position (fingers 1, 3, 5).
    Fixed octaves throughout, so every chord's shape sits in
    the same place on the keyboard - a beginner is learning
    one hand shape at a time, not chasing it up and down.

    Returns None for a quality with no triad to build a
    right-hand shape from - there is currently no such
    quality among the ten this app supports, but the check
    stays so a future quality fails safely rather than
    silently.

    Semitones only, not octaves: the caller places both
    hands at whatever fixed octave the drawing uses, the
    same way chord_overlay_for's own callers already do.
    """

    from chords import CHORD_QUALITIES

    triad = CHORD_QUALITIES.get(quality)

    if triad is None or len(triad) < 3:
        return None

    root_semitone = NOTE_SEMITONES[root] % 12

    left_hand = [
        (root_semitone, 5),
        ((root_semitone + triad[2]) % 12, 1),
    ]

    right_hand = [
        (root_semitone, 1),
        ((root_semitone + triad[1]) % 12, 3),
        ((root_semitone + triad[2]) % 12, 5),
    ]

    return left_hand, right_hand


def chord_overlay_for(key, instrument, chord_name):
    """
    The chord-tones-only picture of one chord on one
    instrument, positioned to stack exactly on
    diagram_for(key, instrument) - and on structure_for and
    scale_overlay_for, all three sharing one coordinate
    system per (key, instrument).

    Empty (no marks, correctly formed SVG) if the chord's
    tones don't overlap the instrument's playable range in
    a way that matters here - there is no such case for a
    12-tone chord vocabulary against these instruments, but
    an unreadable chord name still raises, the same as
    diagram_for would refuse an unreadable key.
    """

    from chords import chord_semitones

    tones = set(chord_semitones(chord_name))

    base = _base_instrument_name(instrument)

    if base == "Piano":
        return piano_chord_overlay(key, tones, _octaves_for(instrument))

    if base.startswith("Violin"):
        if _violin_shows_both(instrument):
            return violin_chord_overlay_both(key, tones)
        return violin_chord_overlay(
            key, tones, _violin_position_for(instrument)
        )

    return fretboard_chord_overlay(
        key, tones, base, _frets_shown_for(instrument)
    )


def piano_chord_shape_overlay(key, chord_name, octaves=None):
    """
    A beginner's two-hand voicing for one chord, transparent
    background, positioned to stack on piano_structure the
    same way piano_scale_overlay and piano_chord_overlay do.
    Left hand one octave, right hand the next - the same
    fixed layout every chord uses, so the shape someone
    learns for one chord is the shape they find again for
    the next. Fits within the compact two-octave keyboard
    exactly as well as the full one, since two octaves is
    exactly what both hands need.

    Returns None if piano_shape_for has no voicing for this
    chord's quality - the caller falls back to the
    all-positions chord overlay, the same way a quality
    guitar_shape_frets cannot draw falls back on guitar.
    """

    from chords import split_chord

    root, quality = split_chord(chord_name)

    shape = piano_shape_for(root, quality)

    if shape is None:
        return None

    left_hand, right_hand = shape

    octaves = octaves or PIANO_LAYOUT["octaves"]

    _, width, height = _piano_structure_parts(octaves)
    white_height = PIANO_LAYOUT["white_height"]

    white_semitones = [
        semitone + octave * 12
        for octave in range(octaves)
        for semitone in [0, 2, 4, 5, 7, 9, 11]
    ]

    black_after = {
        semitone + octave * 12: raised + octave * 12
        for octave in range(octaves)
        for semitone, raised in
        {0: 1, 2: 3, 5: 6, 7: 8, 9: 10}.items()
    }

    white_width = PIANO_LAYOUT["white_width"]
    black_width = PIANO_LAYOUT["black_width"]
    black_height = PIANO_LAYOUT["black_height"]

    parts = []

    def spot(semitone, finger, colour):

        white_index = None

        for index, white_semitone in enumerate(white_semitones):

            if white_semitone == semitone:
                white_index = index
                break

        if white_index is not None:

            x = white_index * white_width + white_width / 2
            y = white_height - 28
            radius = 14

        else:

            white_index = None

            for index, white_semitone in enumerate(white_semitones):
                if black_after.get(white_semitone) == semitone:
                    white_index = index
                    break

            if white_index is None:
                return

            x = (white_index + 1) * white_width
            y = black_height - 22
            radius = 12

        parts.append(
            f'<circle cx="{x}" cy="{y}" r="{radius}" '
            f'fill="{colour}"/>'
            f'<text x="{x}" y="{y + 4}" text-anchor="middle" '
            f'font-size="11" font-family="sans-serif" '
            f'fill="#ffffff">{finger}</text>'
        )

    for semitone, finger in left_hand:
        spot(semitone, finger, LEFT_HAND_COLOUR)

    for semitone, finger in right_hand:
        spot(semitone + 12, finger, RIGHT_HAND_COLOUR)

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'width="100%" style="max-width:{width}px" '
        f'role="img" aria-label="A beginner two-hand shape '
        f'for {_escape(chord_name)}">'
        + "".join(parts) +
        "</svg>"
    )


def _fret_dot(x, y, fret, finger, colour):
    """
    One fretted mark, single colour - unchanged shape from
    before the dual-position work, just pulled out so both
    the single- and dual-position drawing paths share one
    definition of what a mark looks like.
    """

    label = finger if finger is not None else "\u2022"

    return (
        f'<circle cx="{x}" cy="{y}" r="11" '
        f'fill="{colour}" '
        f'stroke="#ffffff" stroke-width="1.5"/>'
        f'<text x="{x}" y="{y + 4}" '
        f'text-anchor="middle" font-size="11" '
        f'font-family="sans-serif" fill="#ffffff">'
        f'{label}</text>'
    )


def _split_fret_dot(x, y, colour_a, colour_b):
    """
    A note reachable from both hand positions: half
    colour_a, half colour_b, no finger number - the two
    positions may want different fingers here, and showing
    one would misrepresent the other. The split itself is
    what says "both", the same way the marking sample agreed
    on: a third blended colour would throw away which two
    positions are overlapping.
    """

    return (
        f'<path d="M{x} {y - 11} A11 11 0 0 1 {x} {y + 11} Z" '
        f'fill="{colour_b}"/>'
        f'<path d="M{x} {y - 11} A11 11 0 0 0 {x} {y + 11} Z" '
        f'fill="{colour_a}"/>'
        f'<circle cx="{x}" cy="{y}" r="11" fill="none" '
        f'stroke="#ffffff" stroke-width="1.5"/>'
    )


def _shows_both_positions(instrument, frets_shown):
    """
    Whether the wide (full) view is active for an instrument
    that has a genuine second hand position to show -
    guitar's 13-fret view or ukulele's 10-fret view. The
    compact view (8 or 6 frets) always shows the lower
    position only, unchanged from before this work.
    """

    if instrument == "Guitar":
        return frets_shown == 13

    if instrument == "Ukulele":
        return frets_shown == 10

    return False


def fretted_chord_shape_overlay(key, chord_name, instrument="Guitar",
                                 frets_shown=FRETS_SHOWN):
    """
    A beginner's standard shape for one chord, transparent
    background, positioned to stack on fretboard_structure
    the same way fretboard_scale_overlay and
    fretboard_chord_overlay do. Works for any fretted,
    strummed instrument this app knows a shape table for -
    currently guitar and ukulele, each with its own table,
    since a different tuning means genuinely different
    shapes, not the same fingering moved to a different
    instrument.

    In the wide (full) view, also draws the higher hand
    position alongside the lower one, in HIGHER_SHAPE_COLOUR,
    with a split mark wherever a string's fret coincides in
    both positions. The compact view is unaffected - same
    single-colour, single-position drawing as before this
    was added.

    Returns None if that instrument's table has no standard
    shape for this chord's quality or root - the caller
    falls back to the all-positions chord overlay.

    A shape needing a fret past frets_shown still draws at
    its real fret position, which can land past the visible
    neck in the compact view - known, not hidden or auto-
    corrected: the honest answer to "the shape needs more
    room than this view shows" is to widen the view, which
    the toggle is right there for.
    """

    from chords import split_chord

    root, quality = split_chord(chord_name)

    if instrument == "Ukulele":
        shaped = ukulele_shape_frets(root, quality)
        higher_shaped = ukulele_shape_frets_higher(root, quality)
    else:
        shaped = guitar_shape_frets(root, quality)
        higher_shaped = guitar_shape_frets_higher(root, quality)

    if shaped is None:
        return None

    frets, barre = shaped

    show_both = _shows_both_positions(instrument, frets_shown)
    higher_frets = higher_shaped[0] if (
        show_both and higher_shaped is not None
    ) else None

    tuning = STRING_TUNINGS.get(instrument)

    if tuning is None:
        raise KeyError(
            f"'{instrument}' is not an instrument this "
            f"app can draw."
        )

    _, width, height = _fretboard_structure_parts(instrument, frets_shown)

    left = FRETBOARD_LAYOUT["left"]
    top = FRETBOARD_LAYOUT["top"]
    fret_width = FRETBOARD_LAYOUT["fret_width"]
    string_gap = FRETBOARD_LAYOUT["string_gap"]

    parts = []

    for tuning_index in range(len(tuning)):

        # frets is in tuning order, matching STRING_TUNINGS
        # itself; the structure layer draws tuning's last
        # string at the top (see _fretboard_structure_parts),
        # so the same reversal applies here to land on the
        # same row.
        string_index = len(tuning) - 1 - tuning_index
        fret, finger = frets[string_index]

        y = top + tuning_index * string_gap

        higher_fret = higher_finger = None

        if higher_frets is not None:
            higher_fret, higher_finger = higher_frets[string_index]

        if fret is None:
            parts.append(
                f'<text x="{left - 26}" y="{y + 4}" '
                f'text-anchor="middle" font-size="12" '
                f'font-weight="700" font-family="sans-serif" '
                f'fill="{SHAPE_COLOUR}">X</text>'
            )
        elif fret == 0:
            parts.append(
                f'<text x="{left - 26}" y="{y + 4}" '
                f'text-anchor="middle" font-size="12" '
                f'font-weight="700" font-family="sans-serif" '
                f'fill="{SHAPE_COLOUR}">O</text>'
            )
        else:
            x = left + fret * fret_width - fret_width / 2

            if higher_fret is not None and higher_fret == fret:
                parts.append(_split_fret_dot(
                    x, y, SHAPE_COLOUR, HIGHER_SHAPE_COLOUR
                ))
                higher_fret = None
            else:
                parts.append(
                    _fret_dot(x, y, fret, finger, SHAPE_COLOUR)
                )

        if higher_fret is not None and higher_fret > 0:
            hx = left + higher_fret * fret_width - fret_width / 2
            parts.append(
                _fret_dot(
                    hx, y, higher_fret, higher_finger,
                    HIGHER_SHAPE_COLOUR
                )
            )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'width="100%" style="max-width:{width}px" '
        f'role="img" aria-label="A beginner shape for '
        f'{_escape(chord_name)} on a {_escape(instrument)} '
        f'neck">'
        + "".join(parts) +
        "</svg>"
    )


# How far up a string a beginner double stop reaches - low
# first position, not stretched toward where the hand would
# shift. Matches the "stay low, favour an open string"
# convention a real double stop follows.
VIOLIN_SHAPE_MAX_FRET = 4


def _fret_for(open_string, target_semitone, max_fret):
    """
    The lowest fret on one string that sounds a given
    semitone, within reach - or None if it doesn't occur
    that low.
    """

    for fret in range(max_fret + 1):
        if _note_at(open_string, fret) == target_semitone:
            return fret

    return None


def violin_shape_strings(root, quality):
    """
    A beginner double stop for one chord: two adjacent
    strings, together sounding the root and either the
    third or the fifth. A double stop is the violin's own
    way of playing a chord - not a bass note alone, which
    is an ensemble bassist's job rather than a soloist's,
    and not a full three-note chord, which is a real
    technique but a harder reach than a beginner double
    stop needs.

    Root is always included, on whichever of the two
    strings reaches it - a chord without its root does not
    read as that chord. Preference order among the pairs
    that work: more open strings first (an open string
    rings clearer and costs no reach at all), a third over
    a fifth (a third says whether the chord is major or
    minor; a fifth alone does not), then the lower total
    reach.

    Returns (low_string_index, low_fret, high_string_index,
    high_fret) - indices into VIOLIN_STRINGS - or None if no
    adjacent pair reaches a chord tone within
    VIOLIN_SHAPE_MAX_FRET of the open string.
    """

    from chords import CHORD_QUALITIES

    triad = CHORD_QUALITIES.get(quality)

    if triad is None or len(triad) < 3:
        return None

    root_semitone = NOTE_SEMITONES[root] % 12
    third = (root_semitone + triad[1]) % 12
    fifth = (root_semitone + triad[2]) % 12

    best = None
    best_score = None

    for pair in range(len(VIOLIN_STRINGS) - 1):

        low_string = VIOLIN_STRINGS[pair]
        high_string = VIOLIN_STRINGS[pair + 1]

        candidates = []

        # The root on the lower string, the third or fifth
        # above it on the higher string.
        low_root_fret = _fret_for(
            low_string, root_semitone, VIOLIN_SHAPE_MAX_FRET
        )

        if low_root_fret is not None:
            for degree, target in (("third", third), ("fifth", fifth)):

                high_fret = _fret_for(
                    high_string, target, VIOLIN_SHAPE_MAX_FRET
                )

                if high_fret is not None:
                    candidates.append((low_root_fret, high_fret, degree))

        # The root on the higher string, the third or fifth
        # below it on the lower string.
        high_root_fret = _fret_for(
            high_string, root_semitone, VIOLIN_SHAPE_MAX_FRET
        )

        if high_root_fret is not None:
            for degree, target in (("third", third), ("fifth", fifth)):

                low_fret = _fret_for(
                    low_string, target, VIOLIN_SHAPE_MAX_FRET
                )

                if low_fret is not None:
                    candidates.append((low_fret, high_root_fret, degree))

        for low_fret, high_fret, degree in candidates:

            openness = (low_fret == 0) + (high_fret == 0)

            score = (
                -openness,
                0 if degree == "third" else 1,
                low_fret + high_fret,
                pair,
            )

            if best_score is None or score < best_score:
                best_score = score
                best = (pair, low_fret, pair + 1, high_fret)

    return best


def violin_chord_shape_overlay(key, chord_name, position="First position"):
    """
    A beginner double stop for one chord, transparent
    background, positioned to stack on violin_structure the
    same way violin_scale_overlay and violin_chord_overlay
    do.

    Only drawn in first position - a double stop here is a
    beginner's low, open-string-favouring shape, not
    something this picture also teaches further up the
    neck, so third position has no shape of its own and the
    caller falls back to chord_overlay_for there.

    Returns None if no adjacent string pair reaches a chord
    tone within reach - the same honest gap
    guitar_shape_frets leaves for a quality with no standard
    shape.
    """

    if position != "First position":
        return None

    from chords import split_chord

    root, quality = split_chord(chord_name)

    shaped = violin_shape_strings(root, quality)

    if shaped is None:
        return None

    low_index, low_fret, high_index, high_fret = shaped

    _, width, height = _violin_structure_parts(position)

    left = VIOLIN_LAYOUT["left"]
    top = VIOLIN_LAYOUT["top"]
    semitone_width = VIOLIN_LAYOUT["semitone_width"]
    string_gap = VIOLIN_LAYOUT["string_gap"]

    parts = []

    def mark(string_index, fret):

        # VIOLIN_STRINGS is low to high; the structure draws
        # the lowest string at the bottom, so the same
        # reversal applies here to land on the same row.
        row = len(VIOLIN_STRINGS) - 1 - string_index
        y = top + row * string_gap
        x = left + fret * semitone_width

        semitone = _note_at(VIOLIN_STRINGS[string_index], fret)
        label = name_for(semitone, key)

        parts.append(
            f'<circle cx="{x}" cy="{y}" r="12" '
            f'fill="{SHAPE_COLOUR}" stroke="#ffffff" '
            f'stroke-width="1.5"/>'
            f'<text x="{x}" y="{y + 4}" text-anchor="middle" '
            f'font-size="10" font-family="sans-serif" '
            f'fill="#ffffff">{_escape(label)}</text>'
        )

    mark(low_index, low_fret)
    mark(high_index, high_fret)

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'width="100%" style="max-width:{width}px" '
        f'role="img" aria-label="A beginner double stop for '
        f'{_escape(chord_name)} on violin">'
        + "".join(parts) +
        "</svg>"
    )


def shape_overlay_for(key, instrument, chord_name):
    """
    The beginner-shape picture of one chord on one
    instrument - one concrete place to put the hand, not
    every place the chord's notes occur. None where no
    standard shape exists: a rare quality or accidental root
    on guitar or ukulele, third position on violin (a double
    stop is a first-position shape here), or a chord no
    adjacent violin string pair can reach. The caller falls
    back to chord_overlay_for.
    """

    base = _base_instrument_name(instrument)

    if base == "Piano":
        return piano_chord_shape_overlay(
            key, chord_name, _octaves_for(instrument)
        )

    if base.startswith("Violin"):
        return violin_chord_shape_overlay(
            key, chord_name, _violin_position_for(instrument)
        )

    return fretted_chord_shape_overlay(
        key, chord_name, base, _frets_shown_for(instrument)
    )


INSTRUMENTS = [
    "Piano, 2 octaves",
    "Piano, 3 octaves",
    "Guitar, 8 frets",
    "Guitar, 13 frets",
    "Ukulele, 6 frets",
    "Ukulele, 10 frets",
    "Violin, first position",
    "Violin, both positions"
]


def diagram_for(key, instrument):
    """
    The picture of a key on one instrument.
    """

    base = _base_instrument_name(instrument)

    if base == "Piano":
        return piano_diagram(key, _octaves_for(instrument))

    if base.startswith("Violin"):
        if _violin_shows_both(instrument):
            return violin_chart_both(key)
        return violin_chart(key, _violin_position_for(instrument))

    return fretboard_diagram(key, base, _frets_shown_for(instrument))


def show_instruments(key, chosen):
    """
    Diagrams for however many instruments are wanted.

    Several at once, because they answer different halves
    of one question: where a note sits under the hand, and
    where it sits on the page. A violinist reading both
    position charts together sees the shift; a singer with
    the piano beside them sees the same seven notes twice.

    The key comes from the key box every time this runs,
    so changing the key redraws every picture rather than
    leaving one of them showing the key that used to be
    chosen.
    """

    if not key or key not in MAJOR_SCALES:
        return (
            "<p>Choose a key to see where its notes sit.</p>"
        )

    if isinstance(chosen, str):
        chosen = [chosen]

    wanted = [
        instrument for instrument in INSTRUMENTS
        if instrument in (chosen or [])
    ]

    if not wanted:
        return (
            "<p>Choose an instrument to see where the "
            "notes of the key sit on it.</p>"
        )

    scale = MAJOR_SCALES[key]

    parts = [
        f"<p><strong>{_escape(describe_key(key))}</strong>: "
        f"{_escape(' '.join(scale))}. "
        f"Home is marked apart.</p>"
    ]

    for instrument in wanted:

        if instrument.startswith("Violin"):
            explained = (
                "Numbers are fingers, nought the open "
                "string; the ruler counts semitones from "
                "it. Fingers drawn close sit a half step "
                "apart."
            )

        else:
            explained = (
                "The greyed positions are the notes "
                "outside the key."
            )

        parts.append(
            f"<h4 style='margin:18px 0 4px'>"
            f"{_escape(instrument)}</h4>"
            f"<p style='margin:0 0 6px;font-size:0.9em;"
            f"color:{LABEL_COLOUR}'>{explained}</p>"
            + diagram_for(key, instrument)
        )

    return "".join(parts)


def show_instrument(key, instrument):
    """
    One instrument's diagram, with a line saying what it
    is. Kept for a single choice; show_instruments is the
    one the interface uses.
    """

    return show_instruments(key, [instrument])