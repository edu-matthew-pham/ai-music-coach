"""
The phrase dropdown is a view on the boxes.

It used to reload the file, which meant the phrasing was
decided at import and could not be changed afterwards. Now
the boxes hold the whole part, the line breaks in the
lyrics are the phrasing, and choosing a phrase cuts to it
without touching anything.
"""

import os

import pytest

from music import (
    list_phrases,
    selected_piece,
    phrase_chosen,
    WHOLE_PART
)


NOTES = "C4 C4 G4 G4 A4 A4 G4 R"
LENGTHS = "1 1 1 1 1 1 3/2 1/2"
CHART = "| C . . . | F . C . |"


def test_one_line_of_lyrics_offers_no_phrases():
    """
    Music that is one phrase does not need a dropdown.
    """

    labels = list_phrases(NOTES, LENGTHS, "Twin- kle twin- kle lit- tle star")

    assert labels == [WHOLE_PART]


def test_each_line_becomes_a_phrase_to_choose():
    labels = list_phrases(
        NOTES, LENGTHS,
        "Twin- kle twin- kle\nlit- tle star"
    )

    assert len(labels) == 3
    assert labels[0] == WHOLE_PART
    assert "Twinkle twinkle" in labels[1]
    assert "little star" in labels[2]


def test_choosing_a_phrase_cuts_the_music_to_it():
    labels = list_phrases(
        NOTES, LENGTHS,
        "Twin- kle twin- kle\nlit- tle star"
    )

    first = selected_piece(
        NOTES, LENGTHS,
        "Twin- kle twin- kle\nlit- tle star",
        "C", CHART, labels[1]
    )

    assert first.pitches == ["C4", "C4", "G4", "G4"]
    assert first.chart == "| C . . . |"
    assert first.lyrics == "Twin- kle twin- kle"


def test_the_whole_part_is_always_available():
    whole = selected_piece(
        NOTES, LENGTHS,
        "Twin- kle twin- kle\nlit- tle star",
        "C", CHART, WHOLE_PART
    )

    assert len(whole) == 8
    assert whole.chart == CHART


def test_a_label_says_which_phrase_it_is():
    assert phrase_chosen("Phrase 3: some words") == 2
    assert phrase_chosen(WHOLE_PART) is None
    assert phrase_chosen(None) is None


def test_correcting_the_lyrics_changes_the_phrases():
    """
    The whole point of moving the phrasing into the box:
    when the guess is wrong it costs a keystroke.
    """

    one = list_phrases(NOTES, LENGTHS, "Twin- kle twin- kle lit- tle star")

    two = list_phrases(
        NOTES, LENGTHS, "Twin- kle twin- kle\nlit- tle star"
    )

    assert len(one) == 1
    assert len(two) == 3


def test_music_that_will_not_read_offers_the_whole_part():
    """
    Half typed music should not empty the dropdown or
    raise: the player is in the middle of editing.
    """

    assert list_phrases("C4 wrong", "1 1", "") == [WHOLE_PART]


def test_a_phrase_of_an_imported_file_plays_on_its_own():
    from music import (
        import_midi_file,
        list_midi_tracks,
        play_music
    )

    path = os.path.join(
        os.path.dirname(__file__),
        "fixtures", "midi", "d_ML_10791.mid"
    )

    if not os.path.exists(path):
        pytest.skip("the band arrangement fixture is absent")

    tracks = list_midi_tracks(path)

    (
        pitches,
        durations,
        lyrics,
        bpm,
        feedback,
        chart,
        chart_notes,
        key
    ) = import_midi_file(path, tracks[0])

    labels = list_phrases(pitches, durations, lyrics)

    assert len(labels) > 2

    rate, phrase_audio = play_music(
        pitches, durations, key, True, False, bpm, False,
        "Third below", chart, False,
        "Thirds, chord-corrected", False, lyrics, labels[1]
    )

    rate, whole_audio = play_music(
        pitches, durations, key, True, False, bpm, False,
        "Third below", chart, False,
        "Thirds, chord-corrected", False, lyrics, WHOLE_PART
    )

    # A phrase is a part of the whole, not the whole again.
    assert len(phrase_audio) < len(whole_audio)


def test_a_phrase_ending_mid_beat_still_has_its_chords():
    """
    A phrase closing on the second half of a beat sits
    under a chord that lasts the whole of it, so the chart
    may run a little past the notes.
    """

    # Two lines, the first ending half way through beat
    # four.
    piece = selected_piece(
        "C4 C4 C4 D4 E4 F4 G4 R",
        "1 1 1 1/2 1/2 1 1 2",
        "one two three four\nfive six seven",
        "C", "| C . . . | F . . . |",
        "Phrase 1: one two three four"
    )

    assert piece.beats() == 3.5
    assert piece.chart
