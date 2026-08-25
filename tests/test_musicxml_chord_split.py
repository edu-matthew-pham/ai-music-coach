"""
A staff whose sung notes include chords lands as two lines.

This Love (Maroon 5) is the real file that found this: the
chorus is written as two-note chords with one syllable each -
melody and harmony sharing one stem, no voice markup - and in
that file the TOP note is the harmony, not the tune. The old
top-note-only rule silently discarded the melody. Which note
is the tune is not decidable from notation (conventions
genuinely conflict), so the importer splits the staff into an
upper and a lower line and the singer picks theirs in the
mixer, like any divided song.

The real file is not committable, so every test here builds
its own score with music21, the same technique the multi-key
and unfold tests use. The shape mirrors This Love: plain
single notes, then a divisi stretch of two-note chords with
one lyric per chord, including a tied chord pair.
"""

from fractions import Fraction

import pytest


def dyad_score():
    """
    Two bars of single notes, two bars of lyric-bearing
    dyads (one tied across the middle), one closing note.
    """

    from music21 import chord, metadata, note, stream

    part = stream.Part()
    part.partName = "Voice"

    measure_1 = stream.Measure(number=1)
    for name, word in [("C4", "one"), ("D4", "two"),
                       ("E4", "three"), ("F4", "four")]:
        n = note.Note(name, quarterLength=1)
        n.lyric = word
        measure_1.append(n)

    measure_2 = stream.Measure(number=2)
    c1 = chord.Chord(["E4", "G4"], quarterLength=2)
    c1.lyric = "shine"
    c2 = chord.Chord(["D4", "F4"], quarterLength=2)
    c2.lyric = "bright"
    measure_2.append(c1)
    measure_2.append(c2)

    # A dyad held across the bar line: written as two
    # chords joined by a tie, sung once.
    measure_3 = stream.Measure(number=3)
    c3 = chord.Chord(["C4", "E4"], quarterLength=4)
    c3.lyric = "home"
    for member in c3.notes:
        member.tie = __import__("music21").tie.Tie("start")
    measure_3.append(c3)

    measure_4 = stream.Measure(number=4)
    c4 = chord.Chord(["C4", "E4"], quarterLength=2)
    for member in c4.notes:
        member.tie = __import__("music21").tie.Tie("stop")
    measure_4.append(c4)
    closing = note.Note("C4", quarterLength=2)
    closing.lyric = "end"
    measure_4.append(closing)

    part.append([measure_1, measure_2, measure_3, measure_4])

    score = stream.Score()
    score.metadata = metadata.Metadata(title="Dyads")
    score.append(part)
    return score


def plain_score():
    """The same tune with no chords anywhere."""

    from music21 import metadata, note, stream

    part = stream.Part()
    part.partName = "Voice"
    measure = stream.Measure(number=1)
    for name, word in [("C4", "one"), ("D4", "two"),
                       ("E4", "three"), ("F4", "four")]:
        n = note.Note(name, quarterLength=1)
        n.lyric = word
        measure.append(n)
    part.append(measure)
    score = stream.Score()
    score.metadata = metadata.Metadata(title="Plain")
    score.append(part)
    return score


def written(score, tmp_path, name):
    path = tmp_path / name
    score.write("musicxml", fp=str(path))
    return str(path)


def tunes_of(result):
    from piece import Piece
    pitches, durations, lyrics, bpm, feedback, chart, poly, key = result
    return Piece.read_parts(pitches, durations, lyrics, key, chart, bpm)


# --- what is offered ------------------------------------------


def test_a_chord_bearing_staff_offers_both_lines(tmp_path):
    from musicxml_import import parts_in

    path = written(dyad_score(), tmp_path, "dyads.musicxml")
    labels = parts_in(path)

    assert len(labels) == 3
    assert "Voice" in labels[0]
    assert "lower line" in labels[1]
    assert "both lines" in labels[2]


def test_both_lines_is_the_default(tmp_path):
    from musicxml_import import default_part_in, parts_in

    path = written(dyad_score(), tmp_path, "dyads.musicxml")

    default = default_part_in(path)
    assert "both lines" in default
    assert default in parts_in(path)


def test_a_staff_without_chords_is_untouched(tmp_path):
    from musicxml_import import parts_in

    path = written(plain_score(), tmp_path, "plain.musicxml")
    labels = parts_in(path)

    assert len(labels) == 1
    assert "line" not in labels[0]


# --- what each line holds -------------------------------------


def test_the_upper_line_is_what_the_staff_always_imported_as(tmp_path):
    """
    Choosing the first entry must change nothing against the
    old top-note rule: same pitches, lengths and words as the
    whole staff read before the split existed.
    """
    from musicxml_import import import_musicxml

    path = written(dyad_score(), tmp_path, "dyads.musicxml")
    upper = import_musicxml(path, "0  Voice")

    assert upper[0].split() == [
        "C4", "D4", "E4", "F4", "G4", "F4", "E4", "C4"
    ]
    assert upper[1].split() == [
        "1", "1", "1", "1", "2", "2", "6", "2"
    ]
    assert upper[2].split() == [
        "one", "two", "three", "four", "shine", "bright",
        "home", "end"
    ]


def test_the_lower_line_is_the_discarded_notes_with_rests(tmp_path):
    from musicxml_import import import_musicxml

    path = written(dyad_score(), tmp_path, "dyads.musicxml")
    lower = import_musicxml(path, "1  Voice, lower line")

    # A bar of rest for the single-note stretch, then each
    # chord's bottom note, the tied pair merged. No trailing
    # rest: a part imported to sing alone has always read
    # consecutively and stopped at its last note; the
    # combined entry (next test) is where the tail is padded
    # so the tunes line up.
    assert lower[0].split() == ["R", "E4", "D4", "C4"]
    assert lower[1].split() == ["4", "2", "2", "6"]
    assert lower[2].split() == ["shine", "bright", "home"]


def test_both_lines_land_as_one_divided_song(tmp_path):
    from musicxml_import import import_musicxml

    path = written(dyad_score(), tmp_path, "dyads.musicxml")
    result = import_musicxml(path, "2  Voice, both lines")

    tunes = tunes_of(result)
    assert [name for name, tune in tunes] == ["Voice 1", "Voice 2"]

    upper, lower = (tune for name, tune in tunes)
    assert upper.pitches == [
        "C4", "D4", "E4", "F4", "G4", "F4", "E4", "C4"
    ]
    # Rests either side: silent through the single-note
    # opening, the discarded chord notes, then padded to the
    # upper line's own end so the tunes line up.
    assert lower.pitches == ["R", "E4", "D4", "C4", "R"]

    assert sum(map(float, upper.durations)) == \
        sum(map(float, lower.durations))


def test_a_tied_chord_is_one_note_in_both_lines(tmp_path):
    from musicxml_import import import_musicxml

    path = written(dyad_score(), tmp_path, "dyads.musicxml")

    upper = import_musicxml(path, "0  Voice")
    lower = import_musicxml(path, "1  Voice, lower line")

    # 4 + 2 beats joined: one token of 6 in each line.
    assert "6" in upper[1].split()
    assert "6" in lower[1].split()
