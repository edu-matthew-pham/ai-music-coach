"""
The Seeds 41-key chromatic kalimba (PLAN-kalimba.md, stages
1 and 2).

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

from chords import chord_semitones
from instrument_diagrams import (
    HOME_COLOUR,
    INSTRUMENTS,
    KALIMBA_LAYOUT,
    KALIMBA_TINES,
    SHAPE_COLOUR,
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
    assert box(shape_overlay_for("D", instrument, "Bm")) == shared
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


# Chord shapes (stage 2). The expected answers below are
# checked against chord_semitones and the hand-read layout,
# never against the rule that generates the shapes - so a
# rule-shaped mistake cannot pass its own test.

ROOTS = "C Db D Eb E F Gb G Ab A Bb B".split()
QUALITIES = ["", "m", "7", "m7"]
ALL_48 = [root + quality for quality in QUALITIES for root in ROOTS]

# The chords whose tones never fall in neighbouring columns
# on this layout - no shape, Chord notes instead. Pinned so
# a rule change that gains or loses a shape is seen.
NO_SHAPE = {"Eb", "Gm", "Eb7"}

# The sample Matthew plays on the real instrument, written
# out by hand: (row, note) per tine, sweep only (no bass).
PLAYED_SAMPLE = {
    "C": {("middle", "C4"), ("middle", "E4"), ("middle", "G4")},
    "Am": {("middle", "A4"), ("middle", "C5"), ("middle", "E5")},
    "F": {("middle", "F4"), ("middle", "A4"), ("middle", "C5")},
    "G": {("middle", "G4"), ("middle", "B4"), ("middle", "D5")},
    "E": {("middle", "E4"), ("top", "G#4"), ("middle", "B4")},
    "Bb": {("middle", "D4"), ("middle", "F4"), ("top", "A#4")},
}


def _column(tine):
    return round(
        (tine["x"] - KALIMBA_LAYOUT["left"]) / KALIMBA_LAYOUT["column_width"]
    )


def _shape(chord, bass=True):
    from chords import split_chord
    from instrument_diagrams import kalimba_shape_tines

    return kalimba_shape_tines(*split_chord(chord), bass=bass)


def _sweep(shape):
    return [tine for tine in shape if tine["row"] != "bass"]


def _runs(columns):
    columns = sorted(columns)
    runs = [[columns[0]]]
    for column in columns[1:]:
        if column == runs[-1][-1] + 1:
            runs[-1].append(column)
        else:
            runs.append([column])
    return runs


@pytest.mark.parametrize("chord", ALL_48)
def test_every_shape_plays_exactly_its_chord(chord):
    """
    All 48 root/quality combinations: either honestly no
    shape, or root present, each chord tone on exactly one
    tine, and nothing else sounding.
    """

    shape = _shape(chord)

    if chord in NO_SHAPE:
        assert shape is None
        return

    assert shape is not None

    tones = chord_semitones(chord)
    sounding = [tine["pitch"] % 12 for tine in _sweep(shape)]

    assert tones[0] in sounding
    assert sorted(sounding) == sorted(tones)


@pytest.mark.parametrize("chord", sorted(set(ALL_48) - NO_SHAPE))
def test_every_shape_is_one_sweep_per_thumb(chord):
    """
    At most one tine per column, and the columns form one
    run of neighbours, or two - one each side of C4's
    centre column.
    """

    columns = [_column(tine) for tine in _sweep(_shape(chord))]
    centre = len(KALIMBA_TINES["middle"]) // 2

    assert len(set(columns)) == len(columns)

    runs = _runs(columns)

    assert len(runs) in (1, 2)

    if len(runs) == 2:
        assert runs[0][-1] <= centre <= runs[1][0]


def test_most_shapes_are_one_thumb():
    """
    Two thumbs only where one cannot do it - measured: three
    chords, all sevenths.
    """

    two_thumb = {
        chord for chord in set(ALL_48) - NO_SHAPE
        if len(_runs([_column(t) for t in _sweep(_shape(chord))])) == 2
    }

    assert two_thumb == {"Bb7", "Cm7", "Gm7"}


@pytest.mark.parametrize("chord", sorted(PLAYED_SAMPLE))
def test_the_sample_to_play_is_the_hand_checked_shape(chord):
    played = {(tine["row"], tine["note"]) for tine in _sweep(_shape(chord))}

    assert played == PLAYED_SAMPLE[chord]


@pytest.mark.parametrize("chord", ["C", "Dm", "Em", "F", "G", "Am"])
def test_the_key_of_c_chords_are_three_middle_row_neighbours_root_lowest(chord):
    sweep = _sweep(_shape(chord))
    columns = sorted(_column(tine) for tine in sweep)
    lowest = min(sweep, key=lambda tine: tine["pitch"])

    assert all(tine["row"] == "middle" for tine in sweep)
    assert columns == list(range(columns[0], columns[0] + 3))
    assert lowest["pitch"] % 12 == chord_semitones(chord)[0]


@pytest.mark.parametrize("chord", sorted(set(ALL_48) - NO_SHAPE))
def test_a_doubled_note_uses_its_middle_copy_where_that_still_plays(chord):
    """
    F4, C5, F5 and C6 have a tine in both rows. A shape
    may use the top copy only when swapping in the middle
    copy would break the sweep or need a second thumb - one
    thumb outranks the middle row. The one chord where that
    ordering decides it is Fm7 (D#4 C4 F4top G#4 in one
    sweep, rather than F4 D#4 C4 + G#4 across two thumbs):
    found by this test failing on its first run, kept as the
    rule's stated order, and on the list to play.
    """

    sweep = _sweep(_shape(chord))
    middle_of = {
        tine["pitch"]: tine for tine in _kalimba_tines(bass=False)
        if tine["row"] == "middle"
    }
    centre = len(KALIMBA_TINES["middle"]) // 2

    for tine in sweep:
        if tine["row"] != "top" or tine["pitch"] not in middle_of:
            continue

        swapped = [
            middle_of[tine["pitch"]] if other is tine else other
            for other in sweep
        ]
        columns = [_column(other) for other in swapped]
        runs = _runs(columns)

        thumbs_before = len(_runs([_column(other) for other in sweep]))

        still_plays = (
            len(set(columns)) == len(columns)
            and len(runs) <= thumbs_before
            and (len(runs) == 1 or (
                len(runs) == 2
                and runs[0][-1] <= centre <= runs[1][0]
            ))
        )

        assert not still_plays


def test_41_keys_adds_the_root_from_the_bass_row_and_nothing_else():
    """
    The bass row holds F3 to B3: roots F to B gain that one
    bass tine, roots C to E (no bass tine) gain nothing. The
    sweep itself is the same on both variants.
    """

    bass_roots = {
        _absolute_pitch(note) % 12 for note in KALIMBA_TINES["bass"]
    }

    for chord in set(ALL_48) - NO_SHAPE:
        with_bass = _shape(chord, bass=True)
        without = _shape(chord, bass=False)
        added = [tine for tine in with_bass if tine["row"] == "bass"]
        root = chord_semitones(chord)[0]

        assert _sweep(with_bass) == without
        assert all(tine["row"] != "bass" for tine in without)

        if root in bass_roots:
            assert [tine["pitch"] % 12 for tine in added] == [root]
        else:
            assert added == []


@pytest.mark.parametrize("instrument", ["Kalimba, 34 keys", "Kalimba, 41 keys"])
def test_the_shape_layer_marks_only_the_shape_in_shape_colour(instrument):
    # C on 34 keys: C4 E4 G4. G on 41 keys: G4 B4 D5 plus G3.
    chord, count = ("C", 3) if "34" in instrument else ("G", 4)

    shape = shape_overlay_for("C", instrument, chord)

    assert _marks(shape) == count
    assert shape.count(SHAPE_COLOUR) == count


def test_no_shape_falls_back_rather_than_drawing_nothing():
    for instrument in ("Kalimba, 34 keys", "Kalimba, 41 keys"):
        assert shape_overlay_for("C", instrument, "Gm") is None
        # A quality outside the four shapes are checked for.
        assert shape_overlay_for("C", instrument, "Cmaj7") is None


def test_every_instrument_name_carries_a_variant():
    """
    InstrumentPanel.svelte rebuilds the lookup key as
    "family, variant". A name with no ", " part would be
    looked up as "Name, " and silently draw nothing.
    """

    for instrument in INSTRUMENTS:
        family, _, variant = instrument.partition(", ")
        assert family and variant
