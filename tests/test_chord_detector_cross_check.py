"""
Second opinions on chord naming.

Our detector is the source of truth in the app. These
tests check its judgements against independent libraries
that know nothing of our scoring, on real files.

Both are optional: the suite passes without them, and they
run where they are installed.

A caution learned the hard way. The first version of this
comparison reported that our detector was badly wrong, and
both halves of that were mistakes of the harness rather
than of the detector: our reader was quietly dropping
repeated notes, and chorder reports one chord per beat
while the comparison indexed it by bar. A cross-check
disagreeing means look closer, not that either side is
wrong.
"""

import os

import pytest


SATB_FILE = os.path.join(
    os.path.dirname(__file__),
    "fixtures", "midi", "o-holy-night-satb.mid"
)


def root_of(name):
    """
    The note a chord is built on, however it is written.

    Strips the inversion, the quality and the spelling, so
    that D/F sharp, DM and D all come back as D.
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


def satb_notes():
    if not os.path.exists(SATB_FILE):
        pytest.skip("the satb fixture is not present")

    import mido

    from midi_import import read_notes

    return read_notes(mido.MidiFile(SATB_FILE))


def test_our_names_agree_with_a_chord_namer():
    """
    pychord names a set of notes. It has no opinion when a
    passing tone spoils the set, and no opinion is not a
    disagreement.
    """

    pytest.importorskip("pychord")

    from pychord.analyzer import find_chords_from_notes

    from chord_detector import detect_chords, weigh_pitches
    from notes import SHARP_NAMES

    notes, bpm = satb_notes()

    total = int(max(start + length for start, length, n in notes))

    agreements = 0
    opinions = 0

    for start, length, name in detect_chords(notes, total, 4):

        weights, lowest = weigh_pitches(notes, start, start + length)

        sounding = [
            SHARP_NAMES[semitone]
            for semitone in range(12)
            if weights[semitone] > 0.2
        ]

        theirs = [
            root_of(str(chord))
            for chord in find_chords_from_notes(sounding)
        ]

        if not theirs:
            continue

        opinions += 1

        if root_of(name) in theirs:
            agreements += 1

    assert opinions > 20
    assert agreements / opinions > 0.8


def test_our_names_agree_with_a_midi_chord_reader():
    """
    chorder reads chords from a MIDI file directly, one
    for every beat, which is the same question we ask.
    """

    pytest.importorskip("chorder")
    pytest.importorskip("miditoolkit")

    from chorder import Dechorder
    from miditoolkit import MidiFile

    from chord_detector import weigh_pitches, name_chord

    notes, bpm = satb_notes()

    theirs = Dechorder.dechord(MidiFile(SATB_FILE))

    agreements = 0
    compared = 0

    for beat in range(len(theirs)):

        if str(theirs[beat]) == "None":
            continue

        weights, lowest = weigh_pitches(notes, beat, beat + 1)

        ours = name_chord(weights, lowest)

        if ours is None:
            continue

        compared += 1

        if root_of(ours) == root_of(str(theirs[beat])):
            agreements += 1

    assert compared > 50

    agreement = agreements / compared

    assert agreement > 0.8, f"only {agreements} of {compared} agree"