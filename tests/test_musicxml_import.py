"""
A score reads as a score.

The point of this path is that nothing has to be inferred
that the file already states: the lengths are written
values, the metre and key are given, and lyrics are
attached to their notes. So these check that what the
file says survives, rather than checking a repair.

The fixture is the app's own O Holy Night, which is why
it can be committed.
"""

import os
from fractions import Fraction

import pytest

FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "musicxml",
    "o-holy-night-satb__1_.mxl"
)


def present():
    return os.path.exists(FIXTURE)


def imported(label="1"):
    from musicxml_import import import_musicxml

    return import_musicxml(FIXTURE, label)


def test_parts_are_named_as_the_score_names_them():
    """
    No guessing from General MIDI numbers: a score carries
    the name the engraver gave each part, and a part with
    lyrics is a part someone sings.
    """

    if not present():
        pytest.skip("the score fixture is not present")

    from musicxml_import import parts_in

    labels = parts_in(FIXTURE)

    assert any("Soprano" in label for label in labels)
    assert any("with words" in label for label in labels)


def test_the_lengths_are_the_scores_own():
    """
    Nothing rescaled, nothing snapped. A dotted quarter is
    three quarters of a beat because the score says so.
    """

    if not present():
        pytest.skip("the score fixture is not present")

    pitches, durations, lyrics, bpm, feedback, chart, poly, key = imported()

    lengths = [Fraction(value) for value in durations.split()]

    assert Fraction(3, 4) in lengths
    assert Fraction(1, 4) in lengths

    # Every length is something notation can write.
    for length in lengths:
        assert length.denominator <= 64


def test_a_tie_is_one_note_sung_once():
    """
    A note tied across a bar line is written twice on the
    page and sung once. Left as two, the second gets no
    syllable and every word after it slides.
    """

    if not present():
        pytest.skip("the score fixture is not present")

    pitches, durations, lyrics, bpm, feedback, chart, poly, key = imported()

    sung = len([note for note in pitches.split() if note != "R"])

    assert len(lyrics.split()) == sung


def test_the_words_are_joined_into_words():
    """
    The file marks every syllable "single" and relies on a
    trailing space to say where a word ends, which is how a
    printed score is typed. music21 strips that space, so
    it is read from the file directly - without it, "Ho"
    and "ly" arrive as two words.
    """

    if not present():
        pytest.skip("the score fixture is not present")

    pitches, durations, lyrics, bpm, feedback, chart, poly, key = imported()

    assert "Ho-" in lyrics.split()
    assert "ly" in lyrics.split()

    assert "bright-" in lyrics.split()


def test_the_chart_is_exactly_as_long_as_the_music():
    """
    True by construction here, which is the point. The
    score states its divisions, so the melody and the
    voices under it are on one clock and nothing has to be
    rescaled onto anything else.
    """

    if not present():
        pytest.skip("the score fixture is not present")

    from chords import chart_beats, read_chart

    pitches, durations, lyrics, bpm, feedback, chart, poly, key = imported()

    music = sum(Fraction(value) for value in durations.split())

    read_chart(chart)

    assert chart_beats(chart) == float(music)


def test_what_comes_out_reads_as_music():
    """
    The same contract the MIDI importer meets, so
    everything above the import works unchanged.
    """

    if not present():
        pytest.skip("the score fixture is not present")

    from music import read_music, read_lyrics, list_phrases

    pitches, durations, lyrics, bpm, feedback, chart, poly, key = imported()

    read_music(pitches, durations)

    sung = len([note for note in pitches.split() if note != "R"])

    read_lyrics(lyrics, sung)

    # Phrases arrive as line breaks, correctable by hand.
    assert len(list_phrases(pitches, durations, lyrics)) > 1


def test_the_feedback_says_nothing_was_repaired():
    """
    Which is the difference worth telling a person about:
    a MIDI import may have respelled the timing, and this
    one had no need to.
    """

    if not present():
        pytest.skip("the score fixture is not present")

    pitches, durations, lyrics, bpm, feedback, chart, poly, key = imported()

    assert "score's own" in feedback


def test_a_part_number_is_read_from_a_label():
    from musicxml_import import part_number_from

    assert part_number_from("2  Piano, ALTO, 61 notes") == 2
    assert part_number_from(None) == 0
    assert part_number_from("nonsense") == 0


def test_the_extension_decides_which_importer_runs():
    """
    Both paths end in the same eight values, so nothing
    above the import needs to know which kind of file
    arrived.
    """

    from music import is_score_file, import_music_file

    assert is_score_file("piece.mxl")
    assert is_score_file("piece.musicxml")
    assert not is_score_file("piece.mid")
    assert not is_score_file(None)

    if not present():
        pytest.skip("the score fixture is not present")

    from_score = import_music_file(FIXTURE, "1")

    assert len(from_score) == 8

    midi = os.path.join(
        os.path.dirname(__file__), "fixtures", "midi",
        "d_ML_10791.mid"
    )

    if os.path.exists(midi):

        from music import list_music_parts

        from_midi = import_music_file(midi, list_music_parts(midi)[0])

        assert len(from_midi) == len(from_score)
