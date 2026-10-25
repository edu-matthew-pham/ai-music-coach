"""
The Seeds 41-key chromatic kalimba (PLAN-kalimba.md, stage 1).

The layout table is pinned against the instrument itself:
the rows below were read tine by tine off a real Seeds
41-key (engraved numbered notation, the unlabelled bass
tines by tuner), written out here as plain note names
rather than derived from any rule - so a rule-shaped
mistake in KALIMBA_TINES cannot also be a mistake in its
own test.
"""

import re

import pytest

from instrument_diagrams import (
    HOME_COLOUR,
    INSTRUMENTS,
    KALIMBA_TINES,
    _absolute_pitch,
    _kalimba_tines,
    chord_overlay_for,
    diagram_for,
    scale_overlay_for,
    shape_overlay_for,
    structure_for,
)


READ_OFF_THE_INSTRUMENT = {
    "top": (
        "D#6 C6 G#5 F5 C#5 A#4 F#4 D#4 C#4 "
        "F4 G#4 C5 D#5 F#5 A#5 C#6 F6"
    ).split(),
    "middle": (
        "D6 B5 G5 E5 C5 A4 F4 D4 C4 "
        "E4 G4 B4 D5 F5 A5 C6 E6"
    ).split(),
    "bass": "B3 A3 G3 F3 F#3 G#3 A#3".split(),
}


def _marks(svg):
    return len(re.findall(r"<circle", svg))


def test_the_layout_is_the_one_read_off_the_instrument():
    assert KALIMBA_TINES == READ_OFF_THE_INSTRUMENT


def test_every_top_tine_is_a_semitone_above_the_middle_tine_beneath_it():
    for top, middle in zip(KALIMBA_TINES["top"], KALIMBA_TINES["middle"]):
        assert _absolute_pitch(top) == _absolute_pitch(middle) + 1


def test_the_middle_row_is_the_standard_layout_centre_out():
    """
    C4 at the centre, and each side climbing in thirds away
    from it - the pattern every kalimba is played by.
    """

    middle = [_absolute_pitch(n) for n in KALIMBA_TINES["middle"]]
    centre = len(middle) // 2

    assert KALIMBA_TINES["middle"][centre] == "C4"

    left = middle[:centre + 1][::-1]
    right = middle[centre:]

    # Outward from C4 the two sides take turns: D4 left,
    # E4 right, F4 left... - so each side's neighbours are a
    # third apart, and every next note up alternates sides.
    for side in (left[1:], right):
        for lower, upper in zip(side, side[1:]):
            assert upper - lower in (3, 4)

    assert sorted(middle) == [
        _absolute_pitch(n) for n in
        "C4 D4 E4 F4 G4 A4 B4 C5 D5 E5 F5 G5 A5 B5 C6 D6 E6".split()
    ]


def test_41_keys_cover_f3_to_f6_chromatically_with_four_doubled_notes():
    pitches = [tine["pitch"] for tine in _kalimba_tines(bass=True)]

    assert len(pitches) == 41
    assert len(set(pitches)) == 37
    assert min(pitches) == _absolute_pitch("F3")
    assert max(pitches) == _absolute_pitch("F6")
    assert set(pitches) == set(range(min(pitches), max(pitches) + 1))

    doubled = {p for p in pitches if pitches.count(p) == 2}
    assert doubled == {
        _absolute_pitch(n) for n in ("F4", "C5", "F5", "C6")
    }


def test_34_keys_is_the_same_instrument_without_the_bass_row():
    with_bass = _kalimba_tines(bass=True)
    without = _kalimba_tines(bass=False)

    assert len(without) == 34
    assert all(tine["row"] != "bass" for tine in without)
    assert without == [t for t in with_bass if t["row"] != "bass"]


def test_no_two_marks_in_one_column_touch():
    """
    A column can hold three tines (bass, middle, top); each
    row's tips sit at their own depth so its three marks
    stay apart, at every column.
    """

    from instrument_diagrams import KALIMBA_LAYOUT

    radius = KALIMBA_LAYOUT["mark_radius"]
    by_column = {}

    for tine in _kalimba_tines(bass=True):
        by_column.setdefault(tine["x"], []).append(tine["tip"])

    for tips in by_column.values():
        tips.sort()
        for upper, lower in zip(tips, tips[1:]):
            assert lower - upper > 2 * radius


@pytest.mark.parametrize("instrument", ["Kalimba, 34 keys", "Kalimba, 41 keys"])
def test_every_layer_stacks_in_register(instrument):
    def box(svg):
        return re.search(r'viewBox="([^"]+)"', svg).group(1)

    shared = box(structure_for(instrument))

    assert box(scale_overlay_for("D", instrument)) == shared
    assert box(chord_overlay_for("D", instrument, "Bm")) == shared
    assert box(diagram_for("D", instrument)) == shared


def test_the_structure_is_key_independent_and_unmarked():
    assert _marks(structure_for("Kalimba, 41 keys")) == 0


def test_c_major_marks_every_tine_it_contains_both_copies_included():
    """
    Counted by hand from the table: all 17 middle tines, the
    5 natural notes in the top row (C6 C5 F5 F4 F6), and the
    4 lettered bass tines - 26. Home is C: C4 C5 C6 in the
    middle row, C5 C6 again in the top row - 5.
    """

    scale = scale_overlay_for("C", "Kalimba, 41 keys")

    assert _marks(scale) == 26
    assert scale.count(HOME_COLOUR) == 5

    # Without the bass row, the 4 lettered bass tines go.
    assert _marks(scale_overlay_for("C", "Kalimba, 34 keys")) == 22


def test_a_chord_marks_every_tine_of_its_tones():
    """
    Bb major (Bb D F), counted by hand: A#3 A#4 A#5, D4 D5
    D6, and F on six tines - F3, both F4s, both F5s, F6.
    """

    assert _marks(chord_overlay_for("Bb", "Kalimba, 41 keys", "Bb")) == 12


def test_chord_shapes_wait_for_stage_two():
    assert shape_overlay_for("C", "Kalimba, 41 keys", "C") is None


def test_every_instrument_name_carries_a_variant():
    """
    InstrumentPanel.svelte rebuilds the lookup key as
    "family, variant". A name with no ", " part would be
    looked up as "Name, " and silently draw nothing.
    """

    for instrument in INSTRUMENTS:
        family, _, variant = instrument.partition(", ")
        assert family and variant
