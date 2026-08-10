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
# position starts. In first position the first finger sits
# a semitone or two above the nut; in third position the
# hand has shifted so the first finger lands where the
# third finger was, five semitones up. The shift is the
# skill the two charts exist to teach.
VIOLIN_STRINGS = ["G3", "D4", "A4", "E5"]

POSITION_STARTS = {
    "First position": 0,
    "Third position": 5
}

# Which finger stops each semitone above the hand's start.
# Nought is the open string, which only the first position
# has: a shifted hand cannot reach back to the nut.
FINGER_FOR_SEMITONE = {
    0: 0,
    1: 1, 2: 1,
    3: 2, 4: 2,
    5: 3, 6: 3,
    7: 4
}

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
    One octave of a keyboard with the key's notes marked.

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

    white_semitones = [0, 2, 4, 5, 7, 9, 11]
    black_after = {0: 1, 2: 3, 5: 6, 7: 8, 9: 10}

    white_width = 44
    white_height = 170
    black_width = 26
    black_height = 105

    parts = []

    def spot(x, y, semitone, radius):
        """
        The mark on a key that is in the key.
        """

        colour = (
            HOME_COLOUR if semitone == home else IN_KEY_COLOUR
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

        if semitone in in_key:
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

        if raised in in_key:
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

    left = 46
    top = 26
    fret_width = 52
    string_gap = 30

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
    A fingering chart the way violin charts are printed.

    Vertical, nut at the top, the four strings as lines
    read G D A E left to right, and each mark a finger
    number - which is what a violinist reads. The note
    name sits small beside it.

    Vertical placement is proportional to semitones, one
    unit per half step, so fingers that sit close on the
    instrument sit close on the page: the half-step pairs
    that make one key's hand shape differ from another's
    are visible as geometry rather than annotation.

    Only the key's notes are drawn, on a faint semitone
    ruler. A violin chart is a picture of a hand shape,
    not a map of the fingerboard, so the notes outside the
    key would be noise here - unlike the guitar, where
    every fret is a destination worth naming.
    """

    start = POSITION_STARTS.get(position)

    if start is None:
        raise KeyError(
            f"'{position}' is not a position this app "
            f"can draw."
        )

    home = NOTE_SEMITONES[MAJOR_SCALES[key][0]] % 12
    in_key = semitones_in(key)

    top = 40
    left = 60
    string_gap = 78
    semitone_gap = 34

    reach = sorted(FINGER_FOR_SEMITONE)

    height = top + max(reach) * semitone_gap + 40
    width = left + (len(VIOLIN_STRINGS) - 1) * string_gap + 70

    parts = []

    # The nut, drawn only where the hand can touch it.
    if start == 0:
        parts.append(
            f'<line x1="{left - 20}" y1="{top}" '
            f'x2="{left + (len(VIOLIN_STRINGS) - 1) * string_gap + 20}" '
            f'y2="{top}" stroke="{LINE_COLOUR}" '
            f'stroke-width="5"/>'
        )

    # A faint ruler of semitones behind the strings.
    for step in reach[1:]:

        y = top + step * semitone_gap

        parts.append(
            f'<line x1="{left - 14}" y1="{y}" '
            f'x2="{left + (len(VIOLIN_STRINGS) - 1) * string_gap + 14}" '
            f'y2="{y}" stroke="#eceff1" stroke-width="1"/>'
        )

    for index, open_string in enumerate(VIOLIN_STRINGS):

        x = left + index * string_gap

        parts.append(
            f'<line x1="{x}" y1="{top}" x2="{x}" '
            f'y2="{top + max(reach) * semitone_gap}" '
            f'stroke="{LINE_COLOUR}" stroke-width="1.5"/>'
        )

        parts.append(
            f'<text x="{x}" y="{top - 14}" '
            f'text-anchor="middle" font-size="13" '
            f'font-family="sans-serif" fill="{LABEL_COLOUR}">'
            f'{_escape(open_string[:-1])}</text>'
        )

        for step in reach:

            finger = FINGER_FOR_SEMITONE[step]

            # A shifted hand has no open string to play.
            if finger == 0 and start > 0:
                continue

            semitone = _note_at(open_string, start + step)

            if semitone not in in_key:
                continue

            y = top + step * semitone_gap

            colour = (
                HOME_COLOUR if semitone == home
                else IN_KEY_COLOUR
            )

            parts.append(
                f'<circle cx="{x}" cy="{y}" r="13" '
                f'fill="{colour}" stroke="#ffffff" '
                f'stroke-width="1.5"/>'
            )

            parts.append(
                f'<text x="{x}" y="{y + 4}" '
                f'text-anchor="middle" font-size="12" '
                f'font-family="sans-serif" fill="#ffffff">'
                f'{finger}</text>'
            )

            # The open string is named by the letter over
            # it already; a side label there only sits on
            # the nut line.
            if finger:
                parts.append(
                    f'<text x="{x + 20}" y="{y + 4}" '
                    f'text-anchor="start" font-size="10" '
                    f'font-family="sans-serif" '
                    f'fill="{LABEL_COLOUR}">'
                    f'{_escape(name_for(semitone, key))}</text>'
                )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'width="100%" style="max-width:{width}px" '
        f'role="img" aria-label="A violin chart of '
        f'{_escape(describe_key(key))} in '
        f'{_escape(position.lower())}">'
        + "".join(parts) +
        "</svg>"
    )


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


def show_instrument(key, instrument):
    """
    A diagram with a line saying what is being looked at.

    The key comes from the key box every time this runs, so
    changing the key draws the new one rather than leaving
    a picture of the old.
    """

    if not key or key not in MAJOR_SCALES:
        return (
            "<p>Choose a key to see where its notes sit.</p>"
        )

    if instrument not in INSTRUMENTS:
        instrument = INSTRUMENTS[0]

    scale = MAJOR_SCALES[key]

    if instrument.startswith("Violin"):
        explained = (
            "The numbers are fingers, nought the open "
            "string. Home is marked apart. Fingers drawn "
            "close together sit a half step apart on the "
            "instrument."
        )

    else:
        explained = (
            "Home is marked apart; the greyed positions "
            "are the notes outside the key."
        )

    return (
        f"<p><strong>{_escape(describe_key(key))}</strong> "
        f"on the {_escape(instrument.lower())}: "
        f"{_escape(' '.join(scale))}. "
        f"{explained}</p>"
        + diagram_for(key, instrument)
    )
