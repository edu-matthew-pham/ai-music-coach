"""
The melody on the instrument (melody_lanes.py): the notes of a
song laid out in lanes, one per kalimba tine.

Expected lanes below are read off the kalimba's own layout by
hand (the tine table in PLAN-kalimba.md), never taken from the
code under test. The middle row, left to right, is

    D6 B5 G5 E5 C5 A4 F4 D4 [C4] E4 G4 B4 D5 F5 A5 C6 E6

so column 0 is D6 and the centre column, 8, is C4.
"""

import ast
import os
import re

import pytest

from examples import load_twinkle, load_wellerman
from melody_lanes import (
    LEGEND,
    default_variant,
    keep_phrase,
    lanes_for,
    lanes_html,
    melody_blocks,
    melody_page,
    range_message,
    supported_families,
)
from music import WHOLE_PART
from piece import Piece

KALIMBA_34 = "Kalimba, 34 keys"
KALIMBA_41 = "Kalimba, 41 keys"


def _twinkle():
    pitches, durations, lyrics, key, chart, _tempo = load_twinkle()

    return Piece.read(pitches, durations, lyrics, key, chart)


def _piece(pitches, durations=None, lyrics="", key="C"):
    notes = pitches.split()
    durations = durations or " ".join("1" for _ in notes)

    return Piece.read(pitches, durations, lyrics, key, "")


# --- Twinkle, worked out by hand ---------------------------------

def test_twinkles_first_phrase_lands_on_the_right_tines():
    """
    C C G G A A G, then a rest. C4 is the centre column (8), G4
    two to the right of centre (10), A4 three to the left (5).
    """

    blocks = melody_blocks(_twinkle().phrase(0), KALIMBA_34)

    assert [block["lane"] for block in blocks] == [8, 8, 10, 10, 5, 5, 10]
    assert [block["note"] for block in blocks] == list("CCGGAAG")
    assert [block["start"] for block in blocks] == [0, 1, 2, 3, 4, 5, 6]
    assert [block["length"] for block in blocks] == [1, 1, 1, 1, 1, 1, 1.5]
    assert [block["lyric"] for block in blocks] == [
        "Twin-", "kle", "twin-", "kle", "lit-", "tle", "star",
    ]
    assert all(block["row"] == "middle" for block in blocks)
    assert all(block["in_range"] for block in blocks)


def test_the_rest_leaves_a_gap_and_no_block():
    blocks = melody_blocks(_twinkle().phrase(0), KALIMBA_34)

    # 8 slots, one a rest.
    assert len(blocks) == 7


def test_twinkles_second_phrase_is_the_descent():
    """F F E E D D C: columns 6, 6, 9, 9, 7, 7, 8."""

    blocks = melody_blocks(_twinkle().phrase(1), KALIMBA_34)

    assert [block["lane"] for block in blocks] == [6, 6, 9, 9, 7, 7, 8]


def test_the_whole_tune_is_every_phrase_one_after_another():
    blocks = melody_blocks(_twinkle(), KALIMBA_41)

    assert len(blocks) == 42

    # The second phrase starts eight beats in.
    assert blocks[7]["start"] == 8
    assert blocks[7]["note"] == "F"


def test_a_phrase_starts_at_its_own_beat_zero():
    blocks = melody_blocks(_twinkle().phrase(2), KALIMBA_34)

    assert blocks[0]["start"] == 0


# --- thumbs ------------------------------------------------------

def test_thumbs_follow_which_side_of_the_centre_a_lane_is_on():
    blocks = melody_blocks(_twinkle().phrase(0), KALIMBA_34)

    assert [block["thumb"] for block in blocks] == [
        "centre", "centre", "right", "right", "left", "left", "right",
    ]


# --- which tine a note uses --------------------------------------

def test_a_doubled_note_uses_its_middle_row_tine():
    """F4 is column 6 on the middle row and column 9 on the top row."""

    (block,) = melody_blocks(_piece("F4"), KALIMBA_34)

    assert (block["lane"], block["row"]) == (6, "middle")


def test_a_sharp_is_on_the_top_row_in_its_columns():
    """
    The top row, left to right: D#6 C6 G#5 F5 C#5 A#4 F#4 D#4 C#4
    F4 G#4 C5 D#5 F#5 A#5 C#6 F6. F#4 is column 6, C#4 column 8,
    G#4 column 10.
    """

    blocks = melody_blocks(_piece("F#4 C#4 G#4"), KALIMBA_34)

    assert [(b["lane"], b["row"]) for b in blocks] == [
        (6, "top"), (8, "top"), (10, "top"),
    ]


def test_a_flat_is_the_same_tine_as_its_sharp():
    flat = melody_blocks(_piece("Bb4"), KALIMBA_34)[0]
    sharp = melody_blocks(_piece("A#4"), KALIMBA_34)[0]

    assert (flat["lane"], flat["row"]) == (sharp["lane"], sharp["row"])
    assert (flat["lane"], flat["row"]) == (5, "top")


def test_the_41_key_has_the_bass_row_under_the_centre():
    """
    Bass, left to right, from column 5: B3 A3 G3 F3 F#3 G#3 A#3,
    so B3 sits under column 5, F3 under the centre column 8.
    """

    blocks = melody_blocks(_piece("B3 F3 A#3"), KALIMBA_41)

    assert [(b["lane"], b["row"]) for b in blocks] == [
        (5, "bass"), (8, "bass"), (11, "bass"),
    ]
    assert all(block["in_range"] for block in blocks)


# --- off the instrument ------------------------------------------

def test_a_note_below_the_34_key_is_flagged_not_moved():
    (block,) = melody_blocks(_piece("B3"), KALIMBA_34)

    assert block["in_range"] is False
    assert block["lane"] is None
    assert block["where"] == "below"
    assert block["pitch"] == 47


def test_a_note_above_the_highest_tine_is_flagged_above():
    (block,) = melody_blocks(_piece("G6"), KALIMBA_41)

    assert block["in_range"] is False
    assert block["where"] == "above"


def test_nothing_is_said_when_every_note_is_on_the_instrument():
    blocks = melody_blocks(_twinkle(), KALIMBA_34)

    assert range_message(blocks, KALIMBA_34) == ""


def test_the_message_counts_the_notes_and_says_which_way_to_shift():
    blocks = melody_blocks(_piece("B3 C4 B3"), KALIMBA_34)
    message = range_message(blocks, KALIMBA_34)

    assert message.startswith("2 notes are below the lowest tine (C4)")
    assert "Octave up" in message


def test_one_note_is_singular():
    message = range_message(
        melody_blocks(_piece("B3 C4"), KALIMBA_34), KALIMBA_34
    )

    assert message.startswith("1 note is below")


def test_it_does_not_promise_a_shift_that_would_push_other_notes_off():
    # B3 is below the 34-key and one octave up fits B3 C4 C5 ...
    blocks = melody_blocks(_piece("B3 C4 C5"), KALIMBA_34)

    assert "Octave up" in range_message(blocks, KALIMBA_34)

    # ... but not B3 C4 C6: C7 is off the top.
    blocks = melody_blocks(_piece("B3 C4 C6"), KALIMBA_34)

    assert "Octave up" not in range_message(blocks, KALIMBA_34)

    blocks = melody_blocks(_piece("B3 F6"), KALIMBA_34)
    message = range_message(blocks, KALIMBA_34)

    assert "Octave up" not in message
    assert "No single octave shift" in message


def test_a_note_too_high_says_octave_down():
    blocks = melody_blocks(_piece("G6 C5"), KALIMBA_41)

    assert "Octave down" in range_message(blocks, KALIMBA_41)

    # E3 is not a tine, so G6 E4 cannot be saved by one shift down.
    blocks = melody_blocks(_piece("G6 E4"), KALIMBA_41)

    assert "Octave down" not in range_message(blocks, KALIMBA_41)


def test_the_wellerman_needs_an_octave_up_on_the_kalimba():
    """
    The real song, checked against the instrument rather than
    against a count: its lowest note is D3, below even the 41-key's
    F3, and an octave up fits the whole tune.
    """

    from piece import Piece as P

    pieces = P.read(*load_wellerman()[:5])

    for instrument in (KALIMBA_34, KALIMBA_41):
        blocks = melody_blocks(pieces, instrument)
        off = [block for block in blocks if not block["in_range"]]

        assert off, instrument
        assert all(block["where"] == "below" for block in off)
        assert "Octave up" in range_message(blocks, instrument)

    sounding = [p for p in pieces.pitches if p != "R"]

    assert len(melody_blocks(pieces, KALIMBA_41)) == len(sounding)


# --- the lanes ---------------------------------------------------

def test_the_kalimba_has_seventeen_lanes_named_by_its_tines():
    lanes = lanes_for(KALIMBA_34)

    assert len(lanes) == 17
    assert [lane["label"] for lane in lanes] == [
        "D6", "B5", "G5", "E5", "C5", "A4", "F4", "D4", "C4",
        "E4", "G4", "B4", "D5", "F5", "A5", "C6", "E6",
    ]
    assert lanes[8]["sub"] == "C#4"


# --- the picture -------------------------------------------------

def _html(piece, instrument=KALIMBA_34):
    return lanes_html(
        melody_blocks(piece, instrument), instrument, piece.beats(),
        piece.chart,
    )


def test_every_block_is_drawn_once_with_its_lyric():
    piece = _twinkle().phrase(0)
    page = _html(piece)

    # 7 note blocks (a rounded rect each) and 7 syllables.
    assert page.count('rx="6"') == 7

    for syllable in ("Twin-", "kle", "lit-", "tle", "star"):
        assert syllable in page


def test_the_header_names_every_lane():
    page = _html(_twinkle().phrase(0))

    for name in ("D6", "C4", "E6"):
        assert f">{name}</text>" in page


def test_no_red_strip_unless_a_note_is_off_the_instrument():
    assert "off</text>" not in _html(_twinkle().phrase(0))
    assert "off</text>" in _html(_piece("B3 C4"))


def test_a_top_row_note_is_marked_with_an_up_triangle():
    assert "F#▲" in _html(_piece("F#4"))


def test_a_bass_note_is_marked_with_a_down_triangle():
    assert "B▼" in _html(_piece("B3"), KALIMBA_41)


def test_a_lyric_with_markup_in_it_is_escaped():
    piece = _piece("C4", lyrics="<script>alert(1)</script>")
    page = _html(piece)

    assert "<script" not in page
    assert "&lt;script" in page


def test_bars_come_from_the_chart_when_there_is_one():
    piece = _twinkle().phrase(0)

    # | C . . . | F . C . | : bars at beats 0 and 4.
    assert "beat 1" in _html(piece)
    assert "beat 5" in _html(piece)


def test_the_picture_scales_with_the_page_not_a_fixed_width():
    page = _html(_twinkle().phrase(0))

    assert "max-width" not in page
    assert 'width="100%"' in page


# --- the whole section: what the boxes say -----------------------

def _boxes():
    pitches, durations, lyrics, key, chart, _tempo = load_twinkle()

    return pitches, durations, lyrics, key, chart


def test_the_section_gives_one_view_per_instrument():
    pitches, durations, lyrics, key, chart = _boxes()

    page = melody_page(
        pitches, durations, lyrics, key, chart, WHOLE_PART,
        [KALIMBA_34, KALIMBA_41],
    )

    assert len(page["views"]) == 2
    assert page["choices"][0] == WHOLE_PART
    assert len(page["choices"]) == 7
    assert page["label"] == WHOLE_PART
    assert page["status"] == "The whole tune."


def test_a_chosen_phrase_shows_only_that_phrase():
    pitches, durations, lyrics, key, chart = _boxes()
    choices = melody_page(
        pitches, durations, lyrics, key, chart, WHOLE_PART, [KALIMBA_34]
    )["choices"]

    page = melody_page(
        pitches, durations, lyrics, key, chart, choices[2], [KALIMBA_34]
    )

    assert page["status"] == "Phrase 2."
    assert "won-" in page["views"][0]
    assert "Twin-" not in page["views"][0]


def test_music_that_cannot_be_read_gives_a_message_not_an_error():
    page = melody_page(
        "C4 D4", "1", "", "C", "", WHOLE_PART, [KALIMBA_34]
    )

    assert "durations" in page["views"][0]

    page = melody_page("", "", "", "C", "", WHOLE_PART, [KALIMBA_34])

    assert "Enter some notes" in page["views"][0]


def test_a_phrase_keeps_its_number_when_the_words_change():
    choices = [
        WHOLE_PART, "Phrase 1: New words", "Phrase 2: Other words",
    ]

    assert keep_phrase("Phrase 2: Old words", choices) == choices[2]
    assert keep_phrase("Phrase 9: Gone", choices) == WHOLE_PART
    assert keep_phrase(None, choices) == WHOLE_PART
    assert keep_phrase(choices[1], choices) == choices[1]


def test_kalimba_harp_and_piano_have_lanes_and_the_kalimba_starts_on_41_keys():
    families = supported_families()

    # In the one list of instruments' order.
    assert list(families) == [
        "Piano", "Guitar", "Ukulele", "Kalimba", "Lever harp",
    ]
    assert default_variant("Kalimba", families["Kalimba"]) == KALIMBA_41
    assert default_variant("Piano", families["Piano"]) == "Piano, 3 octaves"


def test_the_legend_explains_the_colours_and_triangles():
    assert "blue" in LEGEND and "purple" in LEGEND and "grey" in LEGEND
    assert "▲" in LEGEND and "▼" in LEGEND


# --- the song's boxes are never written --------------------------

MAIN = os.path.join(os.path.dirname(__file__), "..", "main.py")


def _main_tree():
    with open(MAIN) as source:
        return ast.parse(source.read())


def _assigned(tree, name):
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
        ):
            return node.value

    pytest.fail(f"{name} is missing")


def _names(node):
    """Names in source order, so [a, b] + c reads a, b, c."""

    if isinstance(node, ast.BinOp):
        return _names(node.left) + _names(node.right)

    if isinstance(node, ast.List):
        return [name for element in node.elts for name in _names(element)]

    if isinstance(node, ast.Name):
        return [node.id]

    return []


def test_nothing_the_melody_section_returns_goes_into_a_song_box():
    outputs = _names(_assigned(_main_tree(), "melody_outputs"))

    assert outputs == [
        "melody_phrase", "melody_status", "melody_views",
    ]

    for box in ("pitch_input", "duration_input", "lyric_input",
                "key_input", "chart_input"):
        assert box not in outputs


def test_the_melody_section_reads_all_five_boxes():
    inputs = _names(_assigned(_main_tree(), "melody_inputs"))

    for box in ("pitch_input", "duration_input", "lyric_input",
                "key_input", "chart_input"):
        assert box in inputs


def test_the_refresh_handler_takes_what_it_is_wired_to():
    for node in ast.walk(_main_tree()):
        if (
            isinstance(node, ast.FunctionDef)
            and node.name == "refresh_melody"
        ):
            names = [arg.arg for arg in node.args.args]

            assert names == [
                "phrase_label", "pitch_text", "duration_text",
                "lyric_text", "key_text", "chart_text",
                "show", "header", "placement",
            ]
            assert node.args.vararg.arg == "variants"
            return

    pytest.fail("refresh_melody is missing")


def test_the_melody_section_sits_after_chords_and_before_practice():
    with open(MAIN) as source:
        text = source.read()

    chords = text.index('elem_id="chords"')
    melody = text.index('elem_id="melody"')
    practice = text.index('elem_id="practice"')

    assert chords < melody < practice
    assert 'anchor_link("Melody", "melody")' in text
