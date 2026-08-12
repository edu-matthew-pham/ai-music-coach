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
    "Guitar": ["E2", "A2", "D3", "G3", "B3", "E4"]
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
    "white_height": 170,
    "black_width": 26,
    "black_height": 105,
}

FRETBOARD_LAYOUT = {
    "left": 46,
    "top": 26,
    "fret_width": 52,
    "string_gap": 30,
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


def piano_diagram(key):
    """
    Three octaves of a keyboard with the key's notes
    marked. One octave shows the pattern; three show it
    repeating, which is how a keyboard is actually read -
    a line moves across octaves, and the shape a hand
    finds is the same shape everywhere.

    White and black keys are drawn as they sit, because
    that is how they are found: a player looks for the
    group of two black keys, not for a pitch class.

    The marking is a spot near the front of each key, not
    a filled key. Colouring the keys themselves turns most
    of a keyboard into one block of colour and hides the
    black keys inside it, which is the shape a player is
    actually navigating by.
    """

    home = NOTE_SEMITONES[MAJOR_SCALES[key][0]] % 12
    in_key = semitones_in(key)

    octaves = PIANO_LAYOUT["octaves"]

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

        parts.append(
            f'<rect x="{x}" y="0" width="{white_width}" '
            f'height="{white_height}" fill="#ffffff" '
            f'stroke="{LINE_COLOUR}" stroke-width="1.5"/>'
        )

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

        parts.append(
            f'<rect x="{x}" y="0" width="{black_width}" '
            f'height="{black_height}" fill="#212121" '
            f'stroke="{LINE_COLOUR}" stroke-width="1.5"/>'
        )

        if raised % 12 in in_key:
            parts.append(
                spot(
                    x + black_width / 2,
                    black_height - 22,
                    raised,
                    12
                )
            )

    width = len(white_semitones) * white_width

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {white_height}" '
        f'width="100%" style="max-width:{width}px" '
        f'role="img" aria-label="A keyboard octave with the '
        f'notes of {_escape(describe_key(key))} marked">'
        + "".join(parts) +
        "</svg>"
    )


def fretboard_diagram(key, instrument="Guitar"):
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

    height = top + (len(tuning) - 1) * string_gap + 30
    width = left + FRETS_SHOWN * fret_width + 20

    parts = []

    # The inlaid dots first, behind everything.
    for fret in MARKER_FRETS:
        parts.append(
            f'<circle cx="{left + fret * fret_width - fret_width / 2}" '
            f'cy="{top + (len(tuning) - 1) * string_gap / 2}" '
            f'r="7" fill="#eceff1"/>'
        )

    for fret in range(FRETS_SHOWN + 1):

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
            f'x2="{left + FRETS_SHOWN * fret_width}" y2="{y}" '
            f'stroke="{LINE_COLOUR}" stroke-width="1"/>'
        )

        parts.append(
            f'<text x="{left - 12}" y="{y + 4}" '
            f'text-anchor="end" font-size="12" '
            f'font-family="sans-serif" fill="{LABEL_COLOUR}">'
            f'{_escape(open_string)}</text>'
        )

        for fret in range(FRETS_SHOWN + 1):

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

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'width="100%" style="max-width:{width}px" '
        f'role="img" aria-label="A {_escape(instrument)} neck with '
        f'the notes of {_escape(describe_key(key))} marked">'
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
    """

    start = POSITION_STARTS.get(position)

    if start is None:
        raise KeyError(
            f"'{position}' is not a position this app "
            f"can draw."
        )

    home = NOTE_SEMITONES[MAJOR_SCALES[key][0]] % 12
    in_key = semitones_in(key)

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

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'width="100%" style="max-width:{width}px" '
        f'role="img" aria-label="A violin chart of '
        f'{_escape(describe_key(key))} in '
        f'{_escape(position.lower())}, along the neck">'
        + "".join(parts) +
        "</svg>"
    )


# The mixer overlay's mark, drawn heavier than the scale
# diagram's so a chord tone that is also a scale note is
# still visibly the thing being played right now, not just
# a note that happens to belong to the key.
CHORD_TONE_COLOUR = "#ad1457"


def piano_chord_overlay(key, chord_semitone_set):
    """
    Chord tones only, on a transparent piano, positioned
    exactly as piano_diagram places its marks - same
    PIANO_LAYOUT, so the two stack in register when the
    mixer shows both.

    Nothing outside the chord is drawn: no keys, no scale
    marks. A caller wanting the key underneath draws
    piano_diagram separately and layers this on top.
    """

    octaves = PIANO_LAYOUT["octaves"]
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


def fretboard_chord_overlay(key, chord_semitone_set, instrument="Guitar"):
    """
    Chord tones only, on a transparent fretboard, at the
    same coordinates fretboard_diagram uses - same
    FRETBOARD_LAYOUT, same FRETS_SHOWN, so it stacks in
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
    width = left + FRETS_SHOWN * fret_width + 20

    parts = []

    for index, open_string in enumerate(reversed(tuning)):

        y = top + index * string_gap

        for fret in range(FRETS_SHOWN + 1):

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


def chord_overlay_for(key, instrument, chord_name):
    """
    The chord-tones-only picture of one chord on one
    instrument, positioned to stack exactly on
    diagram_for(key, instrument).

    Empty (no marks, correctly formed SVG) if the chord's
    tones don't overlap the instrument's playable range in
    a way that matters here - there is no such case for a
    12-tone chord vocabulary against these instruments, but
    an unreadable chord name still raises, the same as
    diagram_for would refuse an unreadable key.
    """

    from chords import chord_semitones

    tones = set(chord_semitones(chord_name))

    if instrument == "Piano":
        return piano_chord_overlay(key, tones)

    if instrument.startswith("Violin"):

        position = (
            "Third position" if "third" in instrument
            else "First position"
        )

        return violin_chord_overlay(key, tones, position)

    return fretboard_chord_overlay(key, tones, instrument)


INSTRUMENTS = [
    "Piano",
    "Guitar",
    "Violin, first position",
    "Violin, third position"
]


def diagram_for(key, instrument):
    """
    The picture of a key on one instrument.
    """

    if instrument == "Piano":
        return piano_diagram(key)

    if instrument.startswith("Violin"):

        position = (
            "Third position" if "third" in instrument
            else "First position"
        )

        return violin_chart(key, position)

    return fretboard_diagram(key, instrument)


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