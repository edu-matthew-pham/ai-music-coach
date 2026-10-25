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
from chords import chord_semitones
from instrument_diagrams import (
    HOME_COLOUR,
    INSTRUMENTS,
    LEVER_HARP_SHAPE_REACH,
    LEVER_HARP_STRINGS,
    LEVER_HARP_STRING_COLOURS,
    SHAPE_COLOUR,
    _absolute_pitch,
    lever_harp_shape_strings,
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


def test_chord_marks_use_the_chords_spelling_and_the_footer_the_keys():
    """
    Db major (Db F Ab) drawn in C: the C strings and G strings
    are lever flips away, labelled Db and Ab by the chord, not
    C# and G# by the key. The footer line is about the key, so
    it stays in the key's own spelling.
    """

    chord = chord_overlay_for("C", HARP, "Db")

    labels = set(re.findall(r">([A-G][#b]?)</text>", chord))

    assert labels == {"Db", "F", "Ab"}

    assert "Not on this harp: Bb" in scale_overlay_for("F", HARP)


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


def test_names_use_the_keys_own_spelling():
    assert name_for(10, "F") == "Bb"
    assert name_for(10, "G") == "A#"


# ---- Stage 2: chord shapes -----------------------------------

ROOTS = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
QUALITIES = ["", "m", "7", "m7"]


def _shape(chord):
    from chords import split_chord

    root, quality = split_chord(chord)
    shape = lever_harp_shape_strings(root, quality)

    if shape is None:
        return None

    return " ".join(
        string["note"] + ("^" if string["up"] else "") for string in shape
    )


@pytest.mark.parametrize("quality", QUALITIES)
@pytest.mark.parametrize("root", ROOTS)
def test_every_shape_sounds_exactly_the_chords_tones(root, quality):
    """
    Checked against chord_semitones, not against the rule: one
    string per tone, no string twice, the pitches exactly the
    chord's, within an octave of strings, root present.
    """

    from chords import split_chord

    chord = root + quality
    shape = lever_harp_shape_strings(root, quality)
    tones = chord_semitones(chord)

    assert shape is not None, f"no shape for {chord}"

    assert len(shape) == len(tones)
    assert len({s["note"] for s in shape}) == len(shape)
    assert {s["sounding"] % 12 for s in shape} == set(tones)

    indices = [LEVER_HARP_STRINGS.index(s["note"]) for s in shape]

    assert max(indices) - min(indices) <= LEVER_HARP_SHAPE_REACH

    # A lever raises a string one semitone, never more.
    for string in shape:
        natural = _absolute_pitch(string["note"])
        assert string["sounding"] - natural in (0, 1)


# Worked by hand, tone by tone, for the chords a beginner meets
# first plus every awkward case: "^" is a raised lever. The
# strings are the lowest, root-position placement nearest the
# middle of the harp (index 9, A4) that needs the fewest levers.
HAND_WORKED = {
    "C": "C5 E5 G5",
    "Am": "A4 C5 E5",
    "F": "F4 A4 C5",
    "G": "G4 B4 D5",
    "Em": "E4 G4 B4",
    "D": "D5 F5^ A5",
    "E": "E4 G4^ B4",
    # Bb is Bb D F; Bb is a raised A.
    "Bb": "A4^ D5 F5",
    # Db is Db F Ab: Db a raised C, Ab a raised G.
    "Db": "C5^ F5 G5^",
    # F# is F# A# C#: three raised levers, nothing natural.
    "F#": "F4^ A4^ C5^",
    "Cm": "C5 D5^ G5",
    "G7": "G4 B4 D5 F5",
    "Gm7": "G4 A4^ D5 F5",
    "Eb7": "D5^ G5 A5^ C6^",
}


@pytest.mark.parametrize("chord, expected", sorted(HAND_WORKED.items()))
def test_hand_worked_shapes(chord, expected):
    assert _shape(chord) == expected


def test_chords_in_c_major_need_no_levers_and_f_sharp_needs_three():
    for chord in ("C", "Dm", "Em", "F", "G", "Am", "G7", "Am7", "Dm7"):
        assert "^" not in _shape(chord)

    assert _shape("F#").count("^") == 3


def test_a_shape_marks_its_strings_and_raises_only_the_levers_it_needs():
    shape = shape_overlay_for("C", HARP, "D")

    # D F# A: three strings, one lever up (F#).
    assert _circles(shape) == 3
    assert _tabs(shape) == 1
    assert shape.count(f'fill="{SHAPE_COLOUR}"') == 3 + 1

    plain = shape_overlay_for("C", HARP, "C")

    assert _circles(plain) == 3
    assert _tabs(plain) == 0


def test_a_shape_is_the_same_in_every_key_and_spelled_by_the_chord():
    """
    A chord's shape is the strings and levers the chord itself
    needs - the marks never move with the key, like every other
    instrument's.
    """

    pictures = {shape_overlay_for(key, HARP, "Db") for key in MAJOR_SCALES}

    assert len(pictures) == 1

    labels = re.findall(r">([A-G][#b]?)</text>", pictures.pop())

    assert set(labels) == {"Db", "F", "Ab"}


def test_a_shape_stacks_in_register_on_the_structure():
    def box(svg):
        return re.search(r'viewBox="([^"]+)"', svg).group(1)

    assert box(shape_overlay_for("C", HARP, "Am")) == box(structure_for(HARP))


def test_a_quality_outside_the_four_has_no_shape_and_falls_back():
    assert shape_overlay_for("C", HARP, "Cmaj7") is None
    assert shape_overlay_for("C", HARP, "Csus4") is None
