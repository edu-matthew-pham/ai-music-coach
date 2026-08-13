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


def test_every_instrument_draws_the_same_height():
    """
    Piano, Guitar, and both violin positions are shown side
    by side in the mixer's instrument panel - a picture much
    shorter or taller than its neighbours reads as a layout
    accident, not a deliberate choice, so all four share one
    height even though their widths genuinely differ.
    """

    import re

    heights = set()

    for instrument in INSTRUMENTS:
        picture = diagram_for("C", instrument)
        box = re.search(r'viewBox="0 0 (\d+) (\d+)"', picture)
        heights.add(box.group(2))

    assert len(heights) == 1


def test_home_is_marked_apart_from_the_rest_of_the_key():
    from instrument_diagrams import HOME_COLOUR

    for instrument in INSTRUMENTS:
        assert HOME_COLOUR in diagram_for("C", instrument)


def test_the_piano_draws_twelve_keys_to_the_octave():
    picture = piano_diagram("C")

    # Seven white and five black per octave, three octaves.
    assert len(re.findall(r"<rect", picture)) == 36


def test_the_view_says_what_it_is_showing():
    shown = show_instrument("F", "Guitar")

    assert "F major / D minor" in shown
    assert "Bb" in shown
    assert "<svg" in shown


def test_no_key_asks_for_one_instead_of_drawing_nothing():
    assert "<svg" not in show_instrument("", "Piano")
    assert "<svg" not in show_instrument(None, "Piano")


def test_choosing_no_instrument_says_so_rather_than_going_blank():
    """
    Every box unticked is a legitimate choice, not a fault:
    the function says what to do instead of returning an
    empty string that would render as broken.
    """

    from instrument_diagrams import show_instruments

    shown = show_instruments("C", [])

    assert "<svg" not in shown
    assert "instrument" in shown.lower()


def test_an_unknown_instrument_is_ignored_rather_than_guessed():
    """
    A stale value must not take the page down - but nor
    should it be quietly drawn as something else. Silently
    substituting a piano for an instrument nobody asked
    for is a lie the picture cannot own up to, so unknown
    names are dropped and the section says what to do.
    """

    shown = show_instrument("C", "Kazoo")

    assert "<svg" not in shown
    assert "instrument" in shown.lower()

    # And a stale name alongside a real one leaves the
    # real one drawn.
    from instrument_diagrams import show_instruments

    both = show_instruments("C", ["Kazoo", "Piano"])

    assert both.count("<svg") == 1
    assert "Piano" in both


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


def test_the_first_finger_lands_on_the_perfect_fourth():
    """
    Third position is defined by its first finger playing
    what the third finger played in first position: five
    semitones above the open string, a perfect fourth.

    This chart once put the whole hand a semitone sharp,
    so the definition is pinned at the semitone: on the A
    string, third position's first finger is D.
    """

    from instrument_diagrams import (
        POSITION_STARTS, fingering_for, _note_at, name_for
    )

    def fingers_on(string, key, position):
        frame = POSITION_STARTS[position]
        return {
            finger: name_for(_note_at(string, step), key)
            for step, finger in fingering_for(string, key, frame)
        }

    # D major, A string: the third finger's note in first
    # position is the first finger's in third.
    first = fingers_on("A4", "D", "First position")
    third = fingers_on("A4", "D", "Third position")

    assert first[3] == "D"
    assert third[1] == "D"

    # Which is five semitones above the open string: a
    # perfect fourth, not a fifth.
    assert _note_at("A4", 5) == _note_at("D4", 0)


def test_each_finger_is_used_once_on_a_string():
    """
    The fingers are ordinal: within a position the four of
    them take the next four notes of the key in order. A
    chart that stamps the same number on two notes and
    never reaches the fourth is modelling a hand with four
    fixed places rather than four fingers.

    This chart did exactly that on the A and E strings in
    third position - two threes, no four.
    """

    from harmony import MAJOR_SCALES
    from instrument_diagrams import (
        VIOLIN_STRINGS, POSITION_STARTS, fingering_for
    )

    for key in MAJOR_SCALES:
        for position, frame in POSITION_STARTS.items():
            for string in VIOLIN_STRINGS:

                fingers = [
                    finger
                    for step, finger in
                    fingering_for(string, key, frame)
                ]

                assert fingers == sorted(fingers)

                assert len(fingers) == len(set(fingers)), (
                    f"{key} {position} {string}: {fingers}"
                )

                assert fingers == list(range(1, len(fingers) + 1))


def test_a_hand_reaches_all_four_fingers_in_a_major_key():
    """
    Seven semitones of a major scale always hold four
    notes, so every string in every key gives a full hand.
    """

    from harmony import MAJOR_SCALES
    from instrument_diagrams import (
        VIOLIN_STRINGS, POSITION_STARTS, fingering_for
    )

    for key in MAJOR_SCALES:
        for frame in POSITION_STARTS.values():
            for string in VIOLIN_STRINGS:

                assert len(
                    fingering_for(string, key, frame)
                ) == 4


def test_the_open_string_belongs_to_every_position():
    """
    An open string needs no finger, so no shift takes it
    away: both charts draw the nought at the nut. What a
    shifted hand loses is the nut itself - its first
    finger starts five semitones up.
    """

    from instrument_diagrams import violin_chart

    first = violin_chart("C", "First position")
    third = violin_chart("C", "Third position")

    assert ">0</text>" in first
    assert ">0</text>" in third


def test_the_two_charts_share_one_ruler_of_the_neck():
    """
    Both charts count semitones from the open string, so
    third position visibly sits further along the neck:
    its ruler reaches twelve where first position's stops
    at seven, and its first fingered mark stands past
    where the first position's hand ends.
    """

    from instrument_diagrams import violin_chart

    first = violin_chart("C", "First position")
    third = violin_chart("C", "Third position")

    assert ">7</text>" in first
    assert ">11</text>" not in first

    # The frame starts at four and the hand reaches seven
    # more: the ruler runs to eleven.
    assert ">11</text>" in third


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


def test_the_piano_spans_three_octaves():
    """
    One octave shows the pattern; three show it repeating,
    which is how a keyboard is read. Every octave carries
    the same marks.
    """

    import re

    from instrument_diagrams import piano_diagram

    picture = piano_diagram("F")

    assert len(re.findall(r"<rect", picture)) == 36

    assert picture.count(">F</text>") == 3
    assert picture.count(">Bb</text>") == 3