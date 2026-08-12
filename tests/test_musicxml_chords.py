"""
A score that prints its own chords should be read, not
re-guessed.

MusicXML can carry chord symbols the same way a lead sheet
does - a name above the staff, at a stated beat. Where a
file has them, invariant 5 says reading beats detecting:
a human wrote that symbol down, which is stronger evidence
than anything inferred from which notes happen to be
sounding. Where a file has none, the existing polyphony
detection is exactly as before.

These fixtures are built in memory with music21 rather than
committed as files, the same way a unit test builds any
other small piece of data - a chord symbol or two is not
worth a fixture file, and it keeps every case exact about
what it is testing.
"""

import os

import pytest

from musicxml_import import import_musicxml, parts_in, _printed_chart


def _build(path, chord_symbols=(), notes=(), time_signature="4/4"):
    """
    A minimal score: a time signature, some chord symbols
    at given offsets, and some notes at given offsets.

    notes is a list of (offset, midi, length) triples.
    chord_symbols is a list of (offset, name) pairs.
    """

    from music21 import stream, note, harmony, meter

    part = stream.Part()
    part.insert(0, meter.TimeSignature(time_signature))

    for offset, name in chord_symbols:
        symbol = harmony.ChordSymbol(name)
        part.insert(offset, symbol)

    for offset, midi, length in notes:
        part.insert(offset, note.Note(midi, quarterLength=length))

    score = stream.Score()
    score.append(part)
    score.write("musicxml", fp=str(path))


def _import(path):
    label = parts_in(str(path))[0]
    return import_musicxml(str(path), label)


def test_a_printed_chord_becomes_the_chart(tmp_path):

    path = tmp_path / "test.musicxml"

    _build(
        path,
        chord_symbols=[(0, "Em"), (2, "G")],
        notes=[(0, 64, 1), (1, 64, 1), (2, 67, 1), (3, 67, 1)]
    )

    _, _, _, _, feedback, chart, _, _ = _import(path)

    assert chart == "| Em . G . |"
    assert "printed" in feedback


def test_no_printed_symbols_falls_back_to_detection(tmp_path):
    """
    A file with real polyphony but no chord symbols reads
    exactly as it always did: detected, not printed.
    """

    path = tmp_path / "test.musicxml"

    from music21 import stream, chord as chord_mod, meter, note

    part = stream.Part()
    part.insert(0, meter.TimeSignature("4/4"))
    part.insert(0, chord_mod.Chord(["E4", "G4", "B4"], quarterLength=2))
    part.insert(2, chord_mod.Chord(["G4", "B4", "D5"], quarterLength=2))

    score = stream.Score()
    score.append(part)
    score.write("musicxml", fp=str(path))

    _, _, _, _, feedback, chart, _, _ = _import(path)

    assert chart
    assert "printed" not in feedback
    assert "sounding together" in feedback


def test_a_slash_chords_bass_note_is_dropped_not_the_root():
    """
    Invariant 12: the chart holds one name per chord because
    it must parse and play. D/F# is D with F# in the bass -
    the chart keeps D and drops the bass note, which is
    display detail the chart was never meant to carry.
    """

    from music21 import stream, harmony, meter

    part = stream.Part()
    part.insert(0, meter.TimeSignature("4/4"))
    part.insert(0, harmony.ChordSymbol("D/F#"))

    chart = _printed_chart([part], 4.0, 4.0)

    assert chart == "| D . . . |"


def test_an_unmappable_quality_falls_back_to_its_triad_shape():
    """
    C9 (a dominant ninth) has no exact match in the app's
    ten chord qualities. Its underlying triad is still
    major, so it becomes plain C rather than being dropped -
    a plainer chord that plays is worth more than an exact
    one the app cannot represent.
    """

    from music21 import stream, harmony, meter

    part = stream.Part()
    part.insert(0, meter.TimeSignature("4/4"))
    part.insert(0, harmony.ChordSymbol("C9"))

    chart = _printed_chart([part], 4.0, 4.0)

    assert chart == "| C . . . |"


def test_a_chord_with_no_representable_triad_is_dropped():
    """
    A power chord has no third, so it has no triad to fall
    back to (music21 calls its quality "other", same as its
    kind). Nothing to fall back to, so it is left out rather
    than guessed - the same choice invariant 6 makes anywhere
    else a guess would be worse than a gap.
    """

    from music21 import stream, harmony, meter

    part = stream.Part()
    part.insert(0, meter.TimeSignature("4/4"))
    part.insert(0, harmony.ChordSymbol("Cpower"))

    chart = _printed_chart([part], 4.0, 4.0)

    assert chart == ""


def test_offsets_are_read_across_the_whole_piece_not_one_measure():
    """
    A chord symbol's own .offset resets to zero at every
    measure - only a flattened part turns that into one
    running count from the start of the piece. Read the
    unflattened way, a chord in the second bar collides
    with whatever is in the first bar's equivalent beat,
    and every bar after the first is silently wrong.
    """

    from music21 import stream, harmony, meter, note

    part = stream.Part()
    part.insert(0, meter.TimeSignature("4/4"))

    # Bar 1: nothing printed. Bar 2: a chord on its second
    # beat - absolute beat 5, not beat 1.
    part.insert(4, harmony.ChordSymbol("G"))

    for offset in range(8):
        part.insert(offset, note.Note(60, quarterLength=1))

    chart = _printed_chart([part], 8.0, 4.0)

    # fill_gaps stretches the first (only) chord back to
    # the start, so the whole chart is G - but it has to be
    # one chord lasting the whole piece, not two bars each
    # thinking they hold beat 1.
    assert chart == "| G . . . | . . . . |"


def test_a_pickup_chord_lands_in_the_bar_it_was_written_into():
    """
    A symbol on the "and" of a beat has to give up that
    timing - a chart here holds one token per beat - and it
    has to give it up by rounding down to the beat it
    starts within, not to the nearest beat. Python's own
    round() sends a half beat to the nearest even number,
    which would push this chord a whole beat late, into the
    bar after the one it was written into.
    """

    from music21 import stream, harmony, meter

    part = stream.Part()
    part.insert(0, meter.TimeSignature("4/4"))
    part.insert(0, harmony.ChordSymbol("Em"))
    part.insert(3.5, harmony.ChordSymbol("G"))

    chart = _printed_chart([part], 4.0, 4.0)

    assert chart == "| Em . . G |"


def test_duplicate_symbols_on_a_second_staff_are_read_once():
    """
    A grand-staff piano part often prints the same chord
    symbols on both staves. Reading every part should not
    double the chart or disagree with itself.
    """

    from music21 import stream, harmony, meter, note

    def staff():
        part = stream.Part()
        part.insert(0, meter.TimeSignature("4/4"))
        part.insert(0, harmony.ChordSymbol("C"))
        part.insert(2, harmony.ChordSymbol("G"))
        part.insert(0, note.Note(60, quarterLength=4))
        return part

    chart = _printed_chart([staff(), staff()], 4.0, 4.0)

    assert chart == "| C . G . |"


def test_chord_symbols_are_not_counted_as_notes(tmp_path):
    """
    music21 models a chord symbol as a kind of chord, so it
    passes every "just the notes" filter a real note passes.
    Left in, four real notes and two printed chord symbols
    would be read as six notes, and the two symbols would
    turn into phantom pitches in the melody.
    """

    path = tmp_path / "test.musicxml"

    _build(
        path,
        chord_symbols=[(0, "Em"), (2, "G")],
        notes=[(0, 60, 1), (1, 62, 1), (2, 64, 1), (3, 65, 1)]
    )

    label = parts_in(str(path))[0]

    assert "4 notes" in label

    pitches, durations, _, _, _, _, _, _ = import_musicxml(
        str(path), label
    )

    assert len(pitches.split()) == 4
