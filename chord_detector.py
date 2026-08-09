# chord_detector.py

"""
Work out the chords from the notes.

A chord is what is sounding at once, so a file with more
than one voice already contains its chords: the four parts
of a hymn spell one out on every beat. Nothing has to be
inferred from a melody alone, which is guesswork; this is
reading what is written.

The method is a beat at a time. Every note sounding during
the beat votes, weighted by how long it sounds for, and the
chord whose notes collect the most votes wins. Runs of the
same chord are then joined, which is what turns a list of
beats into a chart with one entry per change.

This reads; chords.py defines. The vocabulary of chords,
what each is made of, and how a chart is written all live
there.
"""

from chords import CHORD_QUALITIES, CHORD_QUALITIES as QUALITIES
from notes import SHARP_NAMES


# The chords worth looking for. Kept deliberately short:
# offering every quality invites the detector to explain a
# passing note by calling a plain triad something exotic,
# and a chart full of thirteenths helps nobody practise.
DETECTED_QUALITIES = ["", "m", "7", "m7", "dim"]


# How much a note outside the chord counts against it.
# Passing notes are ordinary and should not veto a chord,
# but a chord that leaves half the music unexplained is
# the wrong chord.
OUTSIDE_PENALTY = 0.6


# The root gets extra credit for being in the bass, since
# that is what the ear uses to name a chord. Not decisive:
# inversions are ordinary, and a passing bass note should
# not rename the harmony.
BASS_BONUS = 0.35


# What it costs to claim a chord whose notes are not all
# sounding. Without this, any triad in first inversion can
# be renamed as a minor chord built on its bass note, a
# chord which happens to share two notes with it and whose
# third is nowhere to be heard. D, F sharp and A over F
# sharp is a D chord, not an F sharp minor missing its
# C sharp.
MISSING_PENALTY = 0.5


# A beat with almost nothing sounding cannot be named, and
# guessing there produces chords nobody played.
QUIET_BEAT = 0.05


# How close a second name has to be before it is worth
# mentioning. Scaled by how much is sounding, so a busy
# beat and a quiet one are judged alike.
ALTERNATIVE_MARGIN = 0.15


def weigh_pitches(notes, start, end):
    """
    How long each pitch class sounds during a span.

    Returns (weights, lowest) where weights is a list of
    twelve durations and lowest is the pitch class of the
    lowest note sounding, or None.
    """

    weights = [0.0] * 12

    lowest_midi = None

    for note_start, length, midi_number in notes:

        note_end = note_start + length

        overlap = min(end, note_end) - max(start, note_start)

        if overlap <= 0:
            continue

        weights[midi_number % 12] += overlap

        if lowest_midi is None or midi_number < lowest_midi:
            lowest_midi = midi_number

    lowest = None if lowest_midi is None else lowest_midi % 12

    return weights, lowest


def score_chord(weights, lowest, root, quality):
    """
    How well a chord explains what is sounding.

    Every note belonging to the chord counts for it, and
    every note outside counts against, so the winner is the
    chord that leaves least unexplained.
    """

    intervals = QUALITIES[quality]

    tones = {(root + interval) % 12 for interval in intervals}

    score = 0.0

    for semitone in range(12):

        if semitone in tones:
            score += weights[semitone]

        else:
            score -= OUTSIDE_PENALTY * weights[semitone]

    total = sum(weights)

    if lowest is not None and lowest == root:
        score += BASS_BONUS * total

    # A chord is a worse explanation for every one of its
    # notes that cannot be heard.
    missing = len([
        semitone for semitone in tones
        if weights[semitone] == 0
    ])

    if missing:
        score -= MISSING_PENALTY * total * missing / len(tones)

    return score


def name_chord(weights, lowest):
    """
    The chord that best explains a span, or None.
    """

    total = sum(weights)

    if total <= QUIET_BEAT:
        return None

    best = None
    best_score = None

    for root in range(12):

        for quality in DETECTED_QUALITIES:

            score = score_chord(weights, lowest, root, quality)

            if best_score is None or score > best_score:
                best_score = score
                best = SHARP_NAMES[root] + quality

    # A chord that explains less than it leaves out is not
    # worth naming.
    if best_score is not None and best_score <= 0:
        return None

    return best


def detect_chords(notes, total_beats, beats_per_bar=4):
    """
    Name the chord on every beat, then join the repeats.

    Returns a list of (start_beats, length_beats, name).
    """

    if total_beats <= 0:
        return []

    named = []

    for beat in range(int(round(total_beats))):

        weights, lowest = weigh_pitches(
            notes,
            beat,
            beat + 1
        )

        named.append(name_chord(weights, lowest))

    # Join runs of the same chord into one entry.
    chords = []

    for beat in range(len(named)):

        name = named[beat]

        if name is None:
            continue

        if chords:

            start, length, previous = chords[-1]

            if previous == name and start + length == beat:
                chords[-1] = (start, length + 1.0, name)
                continue

        chords.append((float(beat), 1.0, name))

    return chords


def fill_gaps(chords, total_beats):
    """
    Stretch chords over the beats nothing was named on.

    A beat of silence between phrases belongs to the chord
    before it, so far as a chart is concerned: charts have
    no way to write nothing, and the alternative is a hole
    where a bar should be.
    """

    if not chords:
        return []

    filled = []

    for position in range(len(chords)):

        start, length, name = chords[position]

        if position + 1 < len(chords):
            next_start = chords[position + 1][0]

        else:
            next_start = total_beats

        filled.append((start, next_start - start, name))

    # The first chord reaches back to the beginning.
    first_start, first_length, first_name = filled[0]

    if first_start > 0:
        filled[0] = (0.0, first_start + first_length, first_name)

    return filled


def write_chart(chords, total_beats, beats_per_bar=4):
    """
    Write chords out in the chart notation.

    One token per beat, a dot carrying the chord on, and a
    bar line every few beats as the time signature says.
    """

    if not chords:
        return ""

    on_beat = {}

    for start, length, name in chords:
        on_beat[int(round(start))] = name

    tokens = []

    for beat in range(int(round(total_beats))):

        if beat in on_beat:
            tokens.append(on_beat[beat])

        else:
            tokens.append(".")

    # A chart cannot begin with a dot.
    if tokens and tokens[0] == ".":
        return ""

    bars = []

    for position in range(0, len(tokens), int(beats_per_bar)):

        bar = tokens[position:position + int(beats_per_bar)]

        bars.append(" ".join(bar))

    return "| " + " | ".join(bars) + " |"


def chart_from_notes(notes, total_beats, beats_per_bar=4):
    """
    Read a chord chart out of a piece of polyphonic music.
    """

    chords = detect_chords(notes, total_beats, beats_per_bar)

    chords = fill_gaps(chords, total_beats)

    return write_chart(chords, total_beats, beats_per_bar)


def other_names_for(weights, lowest, chosen, most=2):
    """
    What else the same notes could be called.

    Some pitch sets genuinely are two chords: D, F sharp,
    A and B is a D sixth and a B minor seventh at once, and
    which one it is depends on the music around it rather
    than on the notes. Naming only the winner hides that
    the question was open.

    Returns the next best names, closest first.
    """

    total = sum(weights)

    if total <= QUIET_BEAT:
        return []

    scored = []

    for root in range(12):

        for quality in DETECTED_QUALITIES:

            name = SHARP_NAMES[root] + quality

            if name == chosen:
                continue

            scored.append(
                (score_chord(weights, lowest, root, quality), name)
            )

    scored.sort(reverse=True)

    best = score_chord_for_name(weights, lowest, chosen)

    close = [
        name for score, name in scored
        if best - score <= ALTERNATIVE_MARGIN * total
    ]

    return close[:most]


def score_chord_for_name(weights, lowest, name):
    """
    Score a chord given the way it is written.
    """

    for root in range(12):

        for quality in DETECTED_QUALITIES:

            if SHARP_NAMES[root] + quality == name:
                return score_chord(weights, lowest, root, quality)

    return 0.0


def bass_note_for(weights, lowest, name):
    """
    The bass note, when it is not the root.

    A chord with a note other than its root at the bottom
    is an inversion, written D/F sharp. The chart notation
    has no way to say that, so it is worth mentioning
    rather than losing.
    """

    if lowest is None:
        return None

    for root in range(12):

        for quality in DETECTED_QUALITIES:

            if SHARP_NAMES[root] + quality == name:

                if lowest != root:
                    return SHARP_NAMES[lowest]

                return None

    return None


def describe_detection(notes, chords):
    """
    What the chart does not say.

    The chart holds one name per chord because it has to
    parse and be played. Everything else the detection
    knew - the inversions, and the places where another
    name fits just as well - is reported alongside it, for
    the player to judge.
    """

    inversions = []
    alternatives = []

    for start, length, name in chords:

        weights, lowest = weigh_pitches(notes, start, start + length)

        bass = bass_note_for(weights, lowest, name)

        if bass:
            inversions.append(f"{name}/{bass}")

        others = other_names_for(weights, lowest, name)

        if others:
            alternatives.append(
                f"{name} ({' or '.join(others)})"
            )

    lines = []

    if inversions:
        lines.append(
            "Some chords are played over another note: "
            + ", ".join(inversions[:6])
            + "."
        )

    if alternatives:
        lines.append(
            "Some could be named differently: "
            + ", ".join(alternatives[:6])
            + "."
        )

    return " ".join(lines)


def as_midi_object(notes, ticks_per_beat=480):
    """
    Build a MIDI object in memory from a list of notes.

    Chord readers that expect a file can read one of these
    just as well: a file is only a way of carrying notes
    about, and we already have the notes.
    """

    from miditoolkit import MidiFile, Instrument, Note

    midi_object = MidiFile()

    midi_object.ticks_per_beat = ticks_per_beat

    instrument = Instrument(program=0)

    for start, length, midi_number in notes:

        instrument.notes.append(
            Note(
                velocity=80,
                pitch=midi_number,
                start=int(start * ticks_per_beat),
                end=int((start + length) * ticks_per_beat)
            )
        )

    midi_object.instruments.append(instrument)

    # Without this the readers find no music: it is how
    # they know where to stop looking.
    midi_object.max_tick = max(
        (note.end for note in instrument.notes),
        default=0
    )

    return midi_object


def midi_reader_opinion(notes, chords):
    """
    What a chord reader working from the notes makes of it.

    This one does its own segmentation, weighing one beat
    against two before deciding, so it disagrees with us in
    a different way than a namer does: not about what the
    notes are called, but about where one chord ends.
    """

    try:
        from chorder import Dechorder

    except ImportError:
        return ""

    theirs = Dechorder.dechord(as_midi_object(notes))

    differences = []

    for start, length, name in chords:

        beat = int(round(start))

        if beat >= len(theirs):
            continue

        other = str(theirs[beat])

        if other == "None":
            continue

        if root_of(other) != root_of(name):
            differences.append(f"{name} (or {other})")

    if not differences:
        return ""

    return (
        "A reader that decides where chords change would "
        "hear some differently: "
        + ", ".join(differences[:4])
        + "."
    )


def root_of(name):
    """
    The note a chord is built on, however it is written.
    """

    name = str(name).split("/")[0]

    for quality in [
        "maj7", "m7", "dim", "aug", "sus4", "sus2",
        "M7", "M", "m", "7", "o", "+", "6"
    ]:
        if name.endswith(quality):
            name = name[:-len(quality)]
            break

    name = name.replace("-", "b")

    return {
        "Bb": "A#", "Eb": "D#", "Ab": "G#",
        "Db": "C#", "Gb": "F#"
    }.get(name, name)


def second_opinion(notes, chords):
    """
    What another chord namer makes of the same notes.

    Our detector fills the chart; this only comments. It is
    worth hearing because it disagrees usefully: pychord
    names a set of notes strictly and says nothing when a
    passing tone spoils the set, so its silence marks the
    beats where something is sounding that the chord does
    not explain.

    Not needed for the app to work, and this returns
    nothing when it is absent.
    """

    try:
        from pychord.analyzer import find_chords_from_notes

    except ImportError:
        return ""

    differences = []

    for start, length, name in chords:

        weights, lowest = weigh_pitches(notes, start, start + length)

        sounding = [
            SHARP_NAMES[semitone]
            for semitone in range(12)
            if weights[semitone] > 0.2
        ]

        theirs = [
            str(chord)
            for chord in find_chords_from_notes(sounding)
        ]

        if not theirs:
            continue

        if not any(
            chord.split("/")[0] == name for chord in theirs
        ):
            differences.append(
                f"{name} (read elsewhere as {theirs[0]})"
            )

    if not differences:
        return (
            "A second chord reader agrees with all of "
            "these."
        )

    return (
        "A second chord reader would name some of these "
        "differently: "
        + ", ".join(differences[:6])
        + "."
    )


def asides_for(notes, chords):
    """
    A short note to print under each chord symbol.

    Keyed by the beat the chord starts on, so the picture
    can place them without knowing how they were worked
    out.
    """

    asides = {}

    for start, length, name in chords:

        weights, lowest = weigh_pitches(notes, start, start + length)

        parts = []

        bass = bass_note_for(weights, lowest, name)

        if bass:
            parts.append("/" + bass)

        others = other_names_for(weights, lowest, name, most=1)

        if others:
            parts.append("or " + others[0])

        if parts:
            asides[round(float(start), 3)] = "  ".join(parts)

    return asides