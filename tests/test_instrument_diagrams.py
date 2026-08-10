"""
The diagrams have to agree with the music.

A picture of a key is only useful if the positions it
marks are the notes the app would play and spell. These
check the theory underneath the drawing, and that the
drawing is well formed enough to render.
"""

import re

import pytest

from harmony import MAJOR_SCALES
from notes import NOTE_SEMITONES
from instrument_diagrams import (
    INSTRUMENTS,
    STRING_TUNINGS,
    FRETS_SHOWN,
    diagram_for,
    fretboard_diagram,
    name_for,
    piano_diagram,
    semitones_in,
    show_instrument,
    _note_at
)


def test_a_key_holds_seven_notes():
    for key in MAJOR_SCALES:
        assert len(semitones_in(key)) == 7


def test_the_semitones_are_the_scale_the_app_harmonises_from():
    """
    The diagram and the harmony must draw on one idea of
    the key, or the picture teaches a scale the app will
    not sing.
    """

    for key, scale in MAJOR_SCALES.items():

        assert semitones_in(key) == {
            NOTE_SEMITONES[note] % 12 for note in scale
        }


def test_a_key_written_in_flats_is_drawn_in_flats():
    """
    In F the fourth is Bb. A# is the same sound in the
    wrong dialect, and a player reading Bb in the boxes
    should not have to translate.
    """

    assert name_for(10, "F") == "Bb"
    assert name_for(10, "Bb") == "Bb"

    assert name_for(10, "D") == "A#"
    assert name_for(6, "G") == "F#"


def test_an_unknown_key_is_refused_rather_than_guessed():
    with pytest.raises(KeyError):
        semitones_in("H")


def test_a_string_stopped_at_a_fret_sounds_the_right_note():
    """
    Twelve frets is an octave, and the fifth fret of the
    low E is the A the next string is tuned to - the way
    a guitar is tuned by ear.
    """

    assert _note_at("E2", 0) == _note_at("E2", 12)

    assert _note_at("E2", 5) == _note_at("A2", 0)
    assert _note_at("A2", 5) == _note_at("D3", 0)

    # The violin is tuned in fifths, seven semitones apart.
    assert _note_at("G3", 7) == _note_at("D4", 0)


def test_every_instrument_draws_every_key():
    for key in MAJOR_SCALES:
        for instrument in INSTRUMENTS:

            picture = diagram_for(key, instrument)

            assert picture.startswith("<svg")
            assert picture.endswith("</svg>")

            # Every tag opened is closed: a malformed
            # picture renders as nothing at all.
            opened = len(re.findall(r"<(rect|circle|line|text)\b", picture))

            closed = (
                len(re.findall(r"/>", picture))
                + len(re.findall(r"</text>", picture))
            )

            assert closed >= opened


def test_the_neck_marks_every_position_not_only_the_key():
    """
    A player needs to see the note to avoid as much as the
    note to play, so the positions outside the key are
    drawn faintly rather than left out.
    """

    from instrument_diagrams import OFF_KEY_COLOUR, IN_KEY_COLOUR

    picture = fretboard_diagram("C", "Guitar")

    strings = len(STRING_TUNINGS["Guitar"])

    positions = len(re.findall(r"<circle", picture))

    # Every string at every fret, plus the inlaid dots.
    assert positions >= strings * (FRETS_SHOWN + 1)

    assert OFF_KEY_COLOUR in picture
    assert IN_KEY_COLOUR in picture


def test_home_is_marked_apart_from_the_rest_of_the_key():
    from instrument_diagrams import HOME_COLOUR

    for instrument in INSTRUMENTS:
        assert HOME_COLOUR in diagram_for("C", instrument)


def test_the_piano_draws_seven_white_keys_and_five_black():
    picture = piano_diagram("C")

    assert len(re.findall(r"<rect", picture)) == 12


def test_the_view_says_what_it_is_showing():
    shown = show_instrument("F", "Guitar")

    assert "F major / D minor" in shown
    assert "Bb" in shown
    assert "<svg" in shown


def test_no_key_asks_for_one_instead_of_drawing_nothing():
    assert "<svg" not in show_instrument("", "Piano")
    assert "<svg" not in show_instrument(None, "Piano")


def test_an_unknown_instrument_falls_back_rather_than_failing():
    """
    The dropdown cannot offer one, but a stale value must
    not take the page down with it.
    """

    assert "<svg" in show_instrument("C", "Kazoo")


def test_the_violin_chart_reads_in_fingers_not_frets():
    """
    D major in first position: the A string reads open,
    one, two, three - and the third finger lands on home.
    """

    from instrument_diagrams import violin_chart

    picture = violin_chart("D", "First position")

    assert picture.startswith("<svg")

    # Finger numbers are what the chart prints.
    for finger in "01234":
        assert f">{finger}</text>" in picture


def test_the_shift_lands_the_first_finger_where_the_third_was():
    """
    The relation between the two charts is the shift
    itself: in third position the hand starts five
    semitones up, so its first finger covers ground the
    first position gave to the third.
    """

    from instrument_diagrams import (
        POSITION_STARTS, FINGER_FOR_SEMITONE
    )

    shift = POSITION_STARTS["Third position"]

    # Semitone six from the nut: third finger's ground in
    # first position, first finger's in third position.
    assert FINGER_FOR_SEMITONE[6] == 3
    assert FINGER_FOR_SEMITONE[6 - shift] == 1


def test_a_shifted_hand_has_no_open_string():
    """
    Nought means the open string, which only exists where
    the hand can reach the nut.
    """

    from instrument_diagrams import violin_chart

    first = violin_chart("C", "First position")
    third = violin_chart("C", "Third position")

    assert ">0</text>" in first
    assert ">0</text>" not in third


def test_the_fourth_finger_matches_the_next_string_open():
    """
    In first position the fourth finger sounds the note
    the next string plays open - the tuning check every
    violinist makes.
    """

    from instrument_diagrams import (
        VIOLIN_STRINGS, _note_at
    )

    for lower, upper in zip(VIOLIN_STRINGS, VIOLIN_STRINGS[1:]):
        assert _note_at(lower, 7) == _note_at(upper, 0)


def test_both_positions_are_offered_as_instruments():
    from instrument_diagrams import INSTRUMENTS, show_instrument

    assert "Violin, first position" in INSTRUMENTS
    assert "Violin, third position" in INSTRUMENTS

    for instrument in INSTRUMENTS:
        assert "<svg" in show_instrument("D", instrument)


def test_an_unknown_position_is_refused():
    from instrument_diagrams import violin_chart

    with pytest.raises(KeyError):
        violin_chart("C", "Ninth position")
