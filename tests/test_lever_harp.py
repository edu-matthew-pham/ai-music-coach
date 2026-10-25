"""
The Haze 19-string lever harp (PLAN-lever-harp.md, stage 1).

The string table is pinned against the instrument: 19
strings, F3 to C6, every one a natural note, C red and F
blue as pictured on the real harp's tuning pegs. The lever
rule is pinned by hand-worked keys, not by re-deriving the
rule inside the test.
"""

import re

import pytest

from harmony import MAJOR_SCALES
from instrument_diagrams import (
    HOME_COLOUR,
    INSTRUMENTS,
    LEVER_HARP_STRINGS,
    LEVER_HARP_STRING_COLOURS,
    _absolute_pitch,
    chord_overlay_for,
    diagram_for,
    lever_harp_setting,
    name_for,
    scale_overlay_for,
    shape_overlay_for,
    structure_for,
)

HARP = "Lever harp, 19 strings"


def _circles(svg):
    return len(re.findall(r"<circle", svg))


def _tabs(svg):
    return len(re.findall(r"<rect", svg))


def _raised(key):
    """
    The raised letters, written in C D E F G A B order.
    """

    raised, _ = lever_harp_setting(key)
    return "".join(letter for letter in "CDEFGAB" if letter in raised)


def _missing(key):
    _, missing = lever_harp_setting(key)
    return set(missing)


def test_the_strings_are_the_19_naturals_from_f3_to_c6():
    assert LEVER_HARP_STRINGS == (
        "F3 G3 A3 B3 C4 D4 E4 F4 G4 A4 B4 C5 D5 E5 F5 G5 A5 B5 C6"
    ).split()

    pitches = [_absolute_pitch(note) for note in LEVER_HARP_STRINGS]

    assert pitches == sorted(pitches)
    assert all(note[0] in "CDEFGAB" and len(note) == 2
               for note in LEVER_HARP_STRINGS)


def test_c_is_red_and_f_is_blue_on_the_positions_the_photo_shows():
    """
    The photo's coloured pegs fall on strings 1, 5, 8, 12, 15
    and 19 of the 19.
    """

    coloured = {
        index + 1: LEVER_HARP_STRING_COLOURS[note[0]]
        for index, note in enumerate(LEVER_HARP_STRINGS)
        if note[0] in LEVER_HARP_STRING_COLOURS
    }

    assert sorted(coloured) == [1, 5, 8, 12, 15, 19]
    assert [coloured[i] for i in (5, 12, 19)] == [
        LEVER_HARP_STRING_COLOURS["C"]
    ] * 3
    assert [coloured[i] for i in (1, 8, 15)] == [
        LEVER_HARP_STRING_COLOURS["F"]
    ] * 3

    structure = structure_for(HARP)

    for colour in LEVER_HARP_STRING_COLOURS.values():
        assert structure.count(f'stroke="{colour}"') == 3


@pytest.mark.parametrize("key, raised", [
    ("C", ""),
    ("G", "F"),
    ("D", "CF"),
    ("A", "CFG"),
    ("E", "CDFG"),
    ("B", "CDFGA"),
    # E sharp is an F, so E is raised to sound it.
    ("F#", "CDEFGA"),
    # D flat major is C sharp major: every lever up.
    ("Db", "CDEFGAB"),
])
def test_sharp_keys_get_the_levers_a_key_signature_gives_and_lose_nothing(
    key, raised
):
    assert _raised(key) == raised
    assert _missing(key) == set()


@pytest.mark.parametrize("key, missing", [
    # Worked by hand: each of these needs a flatted note, and a
    # sharpening lever can only get it by giving up the natural
    # of the same letter.
    ("F", {10}),
    ("Bb", {10, 3}),
    ("Eb", {3, 8}),
    ("Ab", {8}),
])
def test_flat_keys_report_exactly_the_notes_the_harp_cannot_sound(
    key, missing
):
    assert _missing(key) == missing


def test_every_key_the_app_knows_has_a_setting_that_sounds_most_of_it():
    for key in MAJOR_SCALES:
        _, missing = lever_harp_setting(key)

        assert len(missing) <= 2


def test_a_missing_note_is_named_in_the_key_s_own_spelling():
    scale = scale_overlay_for("F", HARP)

    assert "Not on this harp: Bb" in scale
    assert "Not on this harp" not in scale_overlay_for("C", HARP)
    assert "Not on this harp" not in scale_overlay_for("Db", HARP)


def test_c_major_marks_every_string_with_home_on_the_three_cs():
    scale = scale_overlay_for("C", HARP)

    assert _circles(scale) == 19
    assert scale.count(f'fill="{HOME_COLOUR}"') == 3
    assert _tabs(scale) == 0


def test_g_major_raises_the_three_f_levers_and_names_them_f_sharp():
    scale = scale_overlay_for("G", HARP)

    assert _circles(scale) == 19
    assert _tabs(scale) == 3
    assert scale.count(">F#</text>") == 3
    assert scale.count(">F</text>") == 0


def test_a_borrowed_chord_rings_the_strings_that_need_a_lever_flip():
    """
    D major (D F# A) in C, worked by hand: D4 D5 and A3 A4 A5
    sound as they are - 5 solid marks. F# is on the three F
    strings, each only a lever flip away - 3 rings, and their
    3 lever tabs outlined where they would have to move to.
    """

    chord = chord_overlay_for("C", HARP, "D")

    solid = len(re.findall(r'<circle[^>]*fill="#ad1457"', chord))
    rings = len(re.findall(r'<circle[^>]*fill="#ffffff"', chord))

    assert (solid, rings) == (5, 3)
    assert _tabs(chord) == 3


def test_a_chord_inside_the_key_needs_no_lever_flip():
    """
    C major (C E G), worked by hand: C4 C5 C6, E4 E5, G3 G4
    G5 - 8 strings. The B strings could be flipped to a C, but
    C is already sounding, so no ring is drawn for them.
    """

    chord = chord_overlay_for("C", HARP, "C")

    assert _circles(chord) == 8
    assert _tabs(chord) == 0


def test_every_layer_stacks_in_register():
    def box(svg):
        return re.search(r'viewBox="([^"]+)"', svg).group(1)

    shared = box(structure_for(HARP))

    for key in MAJOR_SCALES:
        assert box(scale_overlay_for(key, HARP)) == shared
        assert box(chord_overlay_for(key, HARP, "Am")) == shared
        assert box(diagram_for(key, HARP)) == shared


def test_the_structure_is_key_independent_and_unmarked():
    assert _circles(structure_for(HARP)) == 0


def test_chord_shapes_wait_for_stage_two():
    assert shape_overlay_for("C", HARP, "C") is None


def test_names_use_the_keys_own_spelling():
    assert name_for(10, "F") == "Bb"
    assert name_for(10, "G") == "A#"
