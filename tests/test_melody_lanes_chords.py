"""
Stage 3 of PLAN-melody-lanes.md: the chord layer, the Show
control, the instrument picture over the lanes, and where the
chords go. Expected values are worked out by hand from Twinkle's
chart, which is

    | C . . . | F . C . | ... (first line: C 4 beats, F 2, C 2)

Pitch numbers: C = 0, octave * 12, so C4 = 48, E4 = 52, G4 = 55,
F4 = 53, A4 = 57; the harp strings F3..C6 are indexes 0..18
(C4 = 4, E4 = 6, G4 = 8, F4 = 7, A4 = 9).
"""

from types import SimpleNamespace

from examples import load_twinkle
from melody_lanes import (
    AS_IN_SHEET,
    DEFAULT_SHOW,
    HEADER_COMPACT,
    HEADER_LABELS,
    HEADER_PICTURE,
    HEADER_SHORT,
    NEAR_MELODY,
    SHOW_CHORDS,
    SHOW_MELODY,
    chord_blocks,
    chord_spans,
    lanes_html,
    melody_blocks,
    melody_page,
    melody_view,
)
from piece import Piece

KALIMBA = "Kalimba, 34 keys"
HARP = "Lever harp, 19 strings"
PIANO = "Piano, 3 octaves"


def _twinkle():
    pitches, durations, lyrics, key, chart, _tempo = load_twinkle()

    return Piece.read(pitches, durations, lyrics, key, chart)


def _first_phrase():
    return _twinkle().phrase(0)


# --- the chart as spans ------------------------------------------

def test_the_chord_spans_are_the_charts_chords_with_their_length():
    spans = chord_spans(_first_phrase())

    assert [(s["start"], s["length"], s["name"]) for s in spans] == [
        (0, 4, "C"), (4, 2, "F"), (6, 2, "C"),
    ]


def test_no_chart_means_no_spans_and_a_bad_chart_is_not_an_error():
    plain = Piece.read("C4 D4", "1 1", "", "C", "")

    # A half-typed chart cannot make a Piece, but the view may
    # still be handed one text away from valid.
    broken = SimpleNamespace(chart="| Zz . . . |", beats=lambda: 4.0)

    assert chord_spans(plain) == []
    assert chord_spans(broken) == []


# --- near the melody ---------------------------------------------

def test_the_first_chord_near_the_melody_is_c_e_g_around_middle_c():
    """
    The notes sounding in C's four beats are C4 C4 G4 G4, centred
    at 51.5 (between D#4 and E4). Within six semitones of that
    (46 to 57) the tones are C4 (48), E4 (52) and G4 (55).
    """

    piece = _first_phrase()
    melody = melody_blocks(piece, KALIMBA)
    blocks = [
        b for b in chord_blocks(piece, KALIMBA, melody)
        if b["name"] == "C" and b["start"] == 0
    ]

    assert sorted(b["pitch"] for b in blocks) == [48, 52, 55]
    assert all(b["length"] == 4 for b in blocks)
    # Middle row columns: C4 8, E4 9, G4 10.
    assert sorted(b["lane"] for b in blocks) == [8, 9, 10]


def test_near_the_melody_the_harp_uses_strings_around_the_notes():
    piece = _first_phrase()
    melody = melody_blocks(piece, HARP)
    blocks = [
        b for b in chord_blocks(piece, HARP, melody)
        if b["name"] == "C" and b["start"] == 0
    ]

    assert sorted(b["lane"] for b in blocks) == [4, 6, 8]


def test_near_the_melody_follows_the_tune_up_the_instrument():
    """The same C chord over a high melody sits an octave up."""

    low = Piece.read("C4 C4 C4 C4", "1 1 1 1", "", "C", "| C . . . |")
    high = Piece.read("C5 C5 C5 C5", "1 1 1 1", "", "C", "| C . . . |")

    def lanes(piece):
        melody = melody_blocks(piece, PIANO)

        return sorted(b["lane"] for b in chord_blocks(piece, PIANO, melody))

    # Tones within six semitones of the melody's middle: under C4
    # (48) the G is the one below it (G3, 43); under C5 (60) it is
    # the one at 55.
    assert lanes(low) == [43, 48, 52]
    assert lanes(high) == [55, 60, 64]


def test_a_chord_never_lands_off_the_instrument():
    """A melody at the very top still gets in-range chord tones."""

    piece = Piece.read(
        "C6 C6 C6 C6", "1 1 1 1", "", "C", "| C . . . |"
    )
    melody = melody_blocks(piece, HARP)
    blocks = chord_blocks(piece, HARP, melody)

    assert blocks
    assert all(0 <= b["lane"] <= 18 for b in blocks)


# --- as in the chord sheet ---------------------------------------

def test_as_in_the_sheet_the_piano_puts_c_where_the_sheet_does():
    """
    Three octaves, C chord: the left hand plays C3 (key 0) and G3
    (key 7); the right hand plays C4 E4 G4 (keys 12, 16, 19). Keys
    count from C3 = 36, so the pitches are 36, 43, 48, 52, 55.
    """

    piece = Piece.read("C4 C4 C4 C4", "1 1 1 1", "", "C", "| C . . . |")
    melody = melody_blocks(piece, PIANO)
    blocks = chord_blocks(piece, PIANO, melody, AS_IN_SHEET)

    assert sorted(b["pitch"] for b in blocks) == [36, 43, 48, 52, 55]


def test_as_in_the_sheet_the_harp_uses_the_sheets_strings():
    piece = Piece.read("C4 C4 C4 C4", "1 1 1 1", "", "C", "| C . . . |")
    melody = melody_blocks(piece, HARP)
    blocks = chord_blocks(piece, HARP, melody, AS_IN_SHEET)

    assert len(blocks) == 3
    assert all(0 <= b["lane"] <= 18 for b in blocks)


def test_a_chord_with_no_sheet_shape_goes_near_the_melody_instead():
    """Eb on the kalimba has no shape (see PLAN-kalimba)."""

    piece = Piece.read("D#4 D#4 D#4 D#4", "1 1 1 1", "", "C", "| Eb . . . |")
    melody = melody_blocks(piece, KALIMBA)
    blocks = chord_blocks(piece, KALIMBA, melody, AS_IN_SHEET)

    assert len(blocks) == 3


# --- the picture -------------------------------------------------

def test_chord_blocks_are_drawn_before_the_melody_so_they_sit_behind():
    piece = _first_phrase()
    page = melody_view(piece, KALIMBA)

    chord_at = page.index('fill-opacity="0.25"')
    melody_at = page.index('rx="6"')  # a melody block's corners

    assert chord_at < melody_at


def test_the_margin_has_each_chords_name_and_a_bar():
    page = melody_view(_first_phrase(), KALIMBA)

    for name in ("C", "F"):
        assert f'font-weight="600" fill="#ad1457">{name}</text>' in page

    # Three chords, three margin bars.
    assert page.count('x="4" y=') == 3


def test_a_very_short_chord_keeps_its_bar_but_not_its_name():
    piece = Piece.read("C4 D4", "0.25 0.25", "", "C", "")
    page = lanes_html(
        melody_blocks(piece, KALIMBA), KALIMBA, 4.0, "",
        [], [{"start": 0, "length": 0.25, "name": "Dm"}],
    )

    assert 'x="4" y=' in page and ">Dm</text>" not in page


# --- the Show control --------------------------------------------

def test_both_layers_show_by_default():
    assert DEFAULT_SHOW == [SHOW_MELODY, SHOW_CHORDS]


def test_melody_only_has_no_chord_layer():
    page = melody_view(_first_phrase(), KALIMBA, [SHOW_MELODY])

    assert 'fill-opacity="0.25"' not in page
    assert 'x="4" y=' not in page


def test_chords_only_still_draws_the_chords_and_no_melody_notes():
    page = melody_view(_first_phrase(), KALIMBA, [SHOW_CHORDS])

    assert 'fill-opacity="0.55"' in page
    assert "Twin-" not in page


def test_nothing_ticked_shows_the_melody_so_the_view_is_never_blank():
    page = melody_view(_first_phrase(), KALIMBA, [])

    assert "Twin-" in page
    assert 'fill-opacity' not in page


def test_a_song_with_no_chart_has_no_chord_layer_at_all():
    piece = Piece.read("C4 D4", "1 1", "", "C", "")
    page = melody_view(piece, KALIMBA)

    assert 'fill-opacity' not in page
    assert CHORDS_LEGEND_MISSING not in page


CHORDS_LEGEND_MISSING = "Pale pink blocks"


# --- the header toggle -------------------------------------------

def test_compact_is_the_default_then_short_full_and_plain_labels():
    piece = _first_phrase()

    labels = melody_view(piece, KALIMBA, None, HEADER_LABELS)
    compact = melody_view(piece, KALIMBA)
    short = melody_view(piece, KALIMBA, None, HEADER_SHORT)
    full = melody_view(piece, KALIMBA, None, HEADER_PICTURE)

    assert compact == melody_view(piece, KALIMBA, None, HEADER_COMPACT)
    assert "The instrument, over its lanes" not in labels
    assert "The instrument, over its lanes" not in compact
    assert "The instrument, over its lanes" in short
    assert "The instrument, over its lanes" in full

    # Short crops the picture's height, so it is the smaller page.
    assert 'viewBox="-1 0 612 100"' in short
    assert 'viewBox="-1 0 612 148"' in full
    assert 'viewBox="0 0 878 72"' in compact


def test_the_short_picture_keeps_at_least_100_and_a_bit_over_half():
    piece = _first_phrase()

    # 41 keys: 206 tall, 55% is 113. Harp: 260, 55% is 143.
    assert 'viewBox="-1 0 612 113"' in melody_view(
        piece, "Kalimba, 41 keys", None, HEADER_SHORT
    )
    assert 'viewBox="10 0 570 143"' in melody_view(
        piece, HARP, None, HEADER_SHORT
    )


def test_the_compact_kalimba_strip_has_a_tine_and_a_top_dot_per_lane():
    piece = _first_phrase()
    page = melody_view(piece, "Kalimba, 41 keys")

    assert page.count('class="compact-tine"') == 17
    assert page.count('class="compact-top"') == 17
    # The 41-key's bass row runs under seven lanes (B3..A#3 are
    # seven tines); the 34-key has none.
    assert page.count('class="compact-bass"') == 7
    assert 'class="compact-bass"' not in melody_view(piece, KALIMBA)


def test_the_compact_strip_names_only_a_few_lanes():
    page = melody_view(_first_phrase(), KALIMBA, None, HEADER_COMPACT)
    header = page.split("</svg>")[0]

    # Lanes 0, 4, 8, 12 and 16 are D6, C5, C4, D5 and E6.
    for name in ("D6", "C5", "C4", "D5", "E6"):
        assert f">{name}</text>" in header

    for name in ("B5", "G5", "E5", "A4", "F4", "D4", "E4"):
        assert f">{name}</text>" not in header


def test_the_compact_tines_are_longest_at_the_centre_and_mirror_each_side():
    import re

    page = melody_view(_first_phrase(), KALIMBA, None, HEADER_COMPACT)
    heights = [
        float(h) for h in re.findall(
            r'class="compact-tine" x="[^"]*" y="[^"]*" width="18" '
            r'height="([\d.]+)"', page
        )
    ]

    assert len(heights) == 17
    assert heights[8] == max(heights)
    assert heights[0] < heights[8]
    assert heights[0] == heights[16]
    assert heights[3] == heights[13]


def test_the_compact_harp_and_piano_strips():
    piece = _first_phrase()
    harp = melody_view(piece, HARP)
    piano = melody_view(piece, PIANO)

    assert harp.count('class="compact-string"') == 19
    assert piano.count('class="compact-key"') >= 15
    assert 'viewBox="0 0' in harp and ' 72"' in harp


def test_the_kalimba_pictures_wear_the_row_tints_the_harp_does_not():
    piece = _first_phrase()

    for header in (HEADER_SHORT, HEADER_PICTURE):
        page = melody_view(piece, "Kalimba, 41 keys", None, header)

        assert 'fill="#90caf9"' in page      # middle
        assert 'fill="#ce93d8"' in page      # top
        assert 'fill="#80cbc4"' in page      # bass

    plain = melody_view(piece, HARP, None, HEADER_PICTURE)

    assert "#90caf9" not in plain


def test_the_other_sections_kalimba_picture_keeps_its_greys():
    from instrument_diagrams import kalimba_structure

    picture = kalimba_structure(True)

    assert 'fill="#cfd8dc"' in picture and "#90caf9" not in picture


def test_a_half_beat_chord_gets_a_small_name_and_a_quarter_beat_only_a_bar():
    piece = Piece.read("C4 D4", "0.25 0.25", "", "C", "")

    def page(length):
        return lanes_html(
            melody_blocks(piece, KALIMBA), KALIMBA, 4.0, "", [],
            [{"start": 0, "length": length, "name": "Dm"}],
        )

    assert 'font-size="9" font-weight="600" fill="#ad1457">Dm' in page(0.5)
    assert ">Dm</text>" not in page(0.25)
    assert 'x="4" y=' in page(0.25)


def test_the_picture_is_set_so_each_column_is_over_its_lane():
    """
    Kalimba: a column is 36 wide in the picture and in the lanes,
    so the picture is placed at the first lane's x with no scaling.
    Cropped to the lanes shown (all 17 here): 17 * 36 wide.
    """

    page = melody_view(_first_phrase(), KALIMBA, [SHOW_MELODY], HEADER_PICTURE)

    assert 'width="612"' in page
    # A tine is 22 wide 6 in from its column's left edge, so the
    # column's own left edge is one before the lane's: viewBox -1.
    assert 'viewBox="-1 0 612 148"' in page
    # Nested picture starts at the first lane (62, no chord margin).
    assert '<svg x="62" y="0" width="612"' in page


def test_the_piano_picture_is_cropped_to_the_same_lanes_as_the_body():
    piece = _first_phrase()
    page = melody_view(piece, PIANO, [SHOW_MELODY], HEADER_PICTURE)

    # Phrase 1 spans keys A3..B4, nine white lanes of 44.
    assert 'width="396" height="196"' in page
    # The crop starts at A3, after C D E F G (five whites of 44).
    assert 'viewBox="220 0 396 196"' in page


def test_the_page_passes_show_header_and_placement_through():
    pitches, durations, lyrics, key, chart, _tempo = load_twinkle()

    page = melody_page(
        pitches, durations, lyrics, key, chart, "Whole part",
        [KALIMBA], [SHOW_MELODY], HEADER_PICTURE, AS_IN_SHEET,
    )

    assert "The instrument, over its lanes" in page["views"][0]
    assert 'fill-opacity="0.25"' not in page["views"][0]


def test_the_harp_picture_starts_at_its_first_string():
    """19 strings of 30, the first 10 in from the left."""

    page = melody_view(_first_phrase(), HARP, [SHOW_MELODY], HEADER_PICTURE)

    assert 'viewBox="10 0 570 260"' in page


def test_the_piano_crop_stretches_to_hold_the_chord_layer():
    from melody_lanes import visible_lanes

    blocks = melody_blocks(
        Piece.read("C4 C4", "1 1", "", "C", ""), PIANO
    )

    without = visible_lanes(blocks, PIANO)
    # The sheet's left hand reaches down to C3 (36).
    with_chords = visible_lanes(blocks, PIANO, [36])

    assert without[0]["index"] > 36
    assert with_chords[0]["index"] == 36
