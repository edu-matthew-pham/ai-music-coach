"""
A second opinion on chord naming.

Our detector is the source of truth in the app, and this
checks its judgements against an independent library that
knows nothing of our scoring. The two disagree legitimately
in three ways, so the comparison normalises before it
counts:

- pychord names inversions (G/D); we name the harmony (G).
  Same chord.
- pychord requires the pitch set to match a chord exactly,
  so a beat with a passing tone defeats it and it returns
  nothing. No opinion is not a disagreement.
- Some pitch sets genuinely are two chords (D6 and Bm7 are
  the same four notes). Either answer is right.

What is left after that is real disagreement, and there
should be very little of it.
"""

import os

import pytest

pychord = pytest.importorskip(
    "pychord",
    reason="cross-check runs only where pychord is installed"
)

from pychord.analyzer import find_chords_from_notes

from chord_detector import detect_chords, weigh_pitches
from notes import SHARP_NAMES


SATB_FILE = os.path.join(
    os.path.dirname(__file__),
    "fixtures",
    "midi",
    "o-holy-night-satb.mid"
)


def normalise(name):
    """
    Strip an inversion and standardise the quality.
    """

    name = name.split("/")[0]

    return (
        name
        .replace("M7", "maj7")
        .replace("madd4", "m")
        .replace("add4", "")
    )


def test_our_names_agree_with_an_independent_namer():

    if not os.path.exists(SATB_FILE):
        pytest.skip("the satb fixture is not present")

    import mido

    from midi_import import read_notes

    midi_file = mido.MidiFile(SATB_FILE)

    notes, bpm = read_notes(midi_file)

    total = int(max(start + length for start, length, n in notes))

    ours = detect_chords(notes, total, 4)

    agreements = 0
    opinions = 0
    disagreements = []

    for start, length, name in ours:

        weights, lowest = weigh_pitches(notes, start, start + length)

        sounding = [
            SHARP_NAMES[semitone]
            for semitone in range(12)
            if weights[semitone] > 0.2
        ]

        theirs = [
            normalise(str(chord))
            for chord in find_chords_from_notes(sounding)
        ]

        if not theirs:
            # No opinion is not a disagreement.
            continue

        opinions += 1

        if normalise(name) in theirs:
            agreements += 1

        else:
            disagreements.append(
                (start, name, theirs, sounding)
            )

    # Where the independent namer has an opinion at all, we
    # should nearly always be among its answers.
    assert opinions > 20

    agreement = agreements / opinions

    assert agreement > 0.8, (
        f"only {agreements} of {opinions} agree; "
        f"first disagreements: {disagreements[:5]}"
    )
