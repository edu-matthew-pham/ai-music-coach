# chords.py

"""
Chord charts: what is sounding underneath the melody.

A chart is written the way a musician writes one on paper,
in bars of beat slots:

    | Dm .  Bb . | F  .  .  . |
    | Dm .  .    | F  .  .    |

Each bar opens with a line, each token stands for one beat,
and a dot carries on the chord before it. The bars declare
the metre themselves: three slots is three four, four slots
is four four, and a piece that changes metre simply writes
bars of different lengths. Nothing has to be told the time
signature separately.

Chords live on their own timeline rather than alongside the
notes. One chord spans many notes, a melisma spans none, and
a syncopated melody crosses the bar lines freely: the two
are separate sequences over the same clock, joined by time.
"""

from notes import NOTE_SEMITONES


class ChartError(ValueError):
    """
    Something about the chart stops it being read.

    The message is written to be shown to whoever typed it.
    """


# What each chord is made of, as semitones above the root.
# Enough to write most songs with, and every quality here
# is one a singer would recognise by name.
CHORD_QUALITIES = {
    "": [0, 4, 7],
    "m": [0, 3, 7],
    "7": [0, 4, 7, 10],
    "m7": [0, 3, 7, 10],
    "maj7": [0, 4, 7, 11],
    "dim": [0, 3, 6],
    "aug": [0, 4, 8],
    "sus2": [0, 2, 7],
    "sus4": [0, 5, 7],
    "6": [0, 4, 7, 9],
    "m6": [0, 3, 7, 9]
}


# The mark that carries the previous chord on for another
# beat, as a chart does with a dot or a slash.
CONTINUE = "."

BAR_LINE = "|"


def split_chord(name):
    """
    Separate a chord name into its root and its quality.

    Returns (root, quality) such as ("Bb", "m7").
    """

    text = name.strip()

    if len(text) == 0:
        raise ChartError("A chord name cannot be empty.")

    root = text[0].upper()
    rest = text[1:]

    if root not in "ABCDEFG":
        raise ChartError(
            f"'{name}' does not start with a note name."
        )

    # A sharp or flat belongs to the root, not the quality.
    if rest[:1] in ("#", "b"):
        root += rest[0]
        rest = rest[1:]

    if root not in NOTE_SEMITONES:
        raise ChartError(f"'{name}' is not a chord.")

    if rest not in CHORD_QUALITIES:
        known = ", ".join(
            quality for quality in CHORD_QUALITIES if quality
        )

        raise ChartError(
            f"'{name}' is not a chord this app knows. "
            f"After the root it understands: {known}, "
            f"or nothing at all for a major chord."
        )

    return root, rest


def chord_semitones(name):
    """
    The pitch classes a chord is made of, as semitones
    from C, whichever octave they are played in.
    """

    root, quality = split_chord(name)

    root_semitone = NOTE_SEMITONES[root]

    return [
        (root_semitone + interval) % 12
        for interval in CHORD_QUALITIES[quality]
    ]


def chord_root(name):
    """
    The pitch class a chord is built on, which is what a
    bass line sings.
    """

    root, quality = split_chord(name)

    return NOTE_SEMITONES[root]


def read_chart(chart_text):
    """
    Read a chart into chords and bars.

    Returns (chords, bars), where chords is a list of
    (start_beats, length_beats, name) and bars is a list of
    (start_beats, length_beats). A chord that lasts several
    beats appears once, with its full length, however many
    dots carried it.
    """

    text = chart_text.strip()

    if len(text) == 0:
        return [], []

    if not text.startswith(BAR_LINE):
        raise ChartError(
            "A chart begins with a bar line, as in "
            "| Dm . Bb . |"
        )

    chords = []
    bars = []

    beat = 0.0

    for section in text.split(BAR_LINE):

        tokens = section.split()

        if len(tokens) == 0:
            continue

        bar_start = beat

        for token in tokens:

            if token == CONTINUE:

                if len(chords) == 0:
                    raise ChartError(
                        "A chart cannot begin with a dot: "
                        "there is no chord to carry on."
                    )

                start, length, name = chords[-1]

                chords[-1] = (start, length + 1.0, name)

            else:

                # Reading it now means a bad chord name is
                # reported where it was written.
                split_chord(token)

                chords.append((beat, 1.0, token))

            beat += 1.0

        bars.append((bar_start, beat - bar_start))

    return chords, bars


def chart_beats(chart_text):
    """
    How many beats a chart covers.
    """

    chords, bars = read_chart(chart_text)

    if len(bars) == 0:
        return 0.0

    last_start, last_length = bars[-1]

    return last_start + last_length


def chord_at(chords, beat):
    """
    The chord sounding at a moment, or None.

    A note takes the chord it begins under, which is what
    an arranger does and what the ear hears: a note held
    across a change keeps the identity it started with,
    and that is what lets a suspension resolve rather than
    simply sound wrong.
    """

    for start, length, name in chords:

        if start <= beat < start + length:
            return name

    return None


def describe_chart(chart_text):
    """
    A sentence summarising a chart, for feedback.
    """

    chords, bars = read_chart(chart_text)

    if len(chords) == 0:
        return "No chords."

    lengths = {length for start, length in bars}

    if len(lengths) == 1:
        metre = f"{int(lengths.pop())} beats to the bar"

    else:
        metre = "changing bar lengths"

    return (
        f"{len(chords)} chords over {len(bars)} bars, "
        f"{metre}."
    )
