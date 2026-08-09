"""
A piece of music as one object.

The point of it is slicing. Everything the app does to a
stretch of music - play it, sing it, judge it, draw it -
needs the notes, the words under those notes and the chords
over them, cut to the same place. Doing that conversion in
several functions is how the same bug keeps arriving, so it
is done here and tested here.
"""

import pytest

from piece import Piece
from music import MusicInputError


TWINKLE = Piece.read(
    "C4 C4 G4 G4 A4 A4 G4 R",
    "1 1 1 1 1 1 3/2 1/2",
    "Twin- kle twin- kle lit- tle star",
    "C",
    "| C . . . | F . C . |"
)


def test_a_piece_knows_how_long_it_is():
    assert len(TWINKLE) == 8
    assert TWINKLE.beats() == 8
    assert TWINKLE.sung() == 7


def test_length_in_seconds_needs_a_tempo():
    """
    Rhythm is kept in beats, so nothing about the music
    depends on how fast it is sung.
    """

    assert TWINKLE.seconds(120) == 4.0
    assert TWINKLE.seconds(60) == 8.0


def test_slicing_takes_the_words_with_it():
    opening = TWINKLE.slice(0, 3)

    assert opening.pitches == ["C4", "C4", "G4", "G4"]
    assert opening.lyrics == "Twin- kle twin- kle"


def test_slicing_takes_the_chords_with_it():
    """
    Chords are cut in beats while notes are counted one by
    one, and getting that conversion wrong is what this
    object exists to prevent.
    """

    assert TWINKLE.slice(0, 3).chart == "| C . . . |"
    assert TWINKLE.slice(4, 7).chart == "| F . C . |"


def test_a_slice_beginning_mid_chord_still_names_it():
    """
    A phrase starting halfway through a bar of D minor is
    still in D minor, and a chart may not open with a dot.
    """

    piece = Piece.read(
        "D4 E4 F4 G4 A4 B4 C5 D5",
        "1 1 1 1 1 1 1 1",
        "",
        "C",
        "| Dm . . . | G . . . |"
    )

    middle = piece.slice(2, 5)

    assert middle.chart.startswith("| Dm")


def test_a_rest_between_lines_stays_with_the_line_before():
    assert TWINKLE.slice(4, 7).pitches[-1] == "R"

    # And the words are only those of the sung notes.
    assert TWINKLE.slice(4, 7).lyrics == "lit- tle star"


def test_a_piece_without_chords_slices_without_them():
    plain = Piece.read("C4 E4 G4", "1 1 1")

    assert plain.slice(0, 1).chart == ""


def test_phrases_come_from_the_lines_of_the_lyrics():
    piece = Piece.read(
        "C4 C4 G4 G4 A4 A4 G4 R",
        "1 1 1 1 1 1 3/2 1/2",
        "Twin- kle twin- kle\nlit- tle star",
        "C",
        "| C . . . | F . C . |"
    )

    assert len(piece.phrases()) == 2

    first = piece.phrase(0)

    assert first.lyrics == "Twin- kle twin- kle"
    assert first.chart == "| C . . . |"


def test_asking_for_a_phrase_that_is_not_there():
    with pytest.raises(MusicInputError, match="no phrase"):
        TWINKLE.phrase(9)


def test_the_song_tempo_is_not_the_playing_tempo():
    """
    The tempo of the song is part of the song, as a
    marking on a score is. How fast you are singing it
    today is not: a piece slowed down to learn a harmony
    line is the same piece.
    """

    piece = Piece.read(
        "C4 E4", "1 1", "", "C", "", tempo=192
    )

    assert piece.tempo == 192

    # And it travels with a slice, since it belongs to the
    # music rather than to the moment.
    assert piece.slice(0, 0).tempo == 192

    # But it decides nothing about length in beats.
    assert piece.beats() == 2


def test_reading_reports_the_same_mistakes_as_before():
    with pytest.raises(MusicInputError, match="syllable"):
        Piece.read("C4 E4", "1 1", "only-one-word")

    with pytest.raises(MusicInputError, match="same length"):
        Piece.read("C4 E4", "1 1", "", "C", "| C . . . |")


def test_line_breaks_survive_being_read():
    """
    The line breaks in the lyrics are the phrasing, so
    reading a piece must not flatten them.
    """

    piece = Piece.read(
        "C4 E4 G4 C5",
        "1 1 1 1",
        "one two\nthree four"
    )

    assert "\n" in piece.lyrics
    assert len(piece.phrases()) == 2