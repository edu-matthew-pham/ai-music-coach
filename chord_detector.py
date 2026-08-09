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