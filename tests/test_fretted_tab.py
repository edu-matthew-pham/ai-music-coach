"""
Guitar and ukulele tab, layer 1: Nearest the nut (fretted_tab.py,
PLAN-fretted-tab.md). Expected frets are worked out by hand from
the tunings, never taken from the code under test.

Pitch numbers count semitones with C0 = 0, so C4 = 48.

    Guitar, lowest string first: E2 28, A2 33, D3 38, G3 43, B3 47,
        E4 52 (string 0 is the bottom line of the tab).
    Ukulele, string 4 first as stored: G4 55, C4 48, E4 52, A4 57.
        Re-entrant: the first string (G) is higher than the second (C).
"""

import os
import re

import pytest

from examples import load_twinkle, load_wellerman
from fretted_tab import (
    FINGERINGS,
    NEAREST_NUT,
    candidates,
    fretted_blocks,
    fretted_view,
    instrument_range,
    range_message,
    tab_html,
)
from melody_lanes import (
    default_variant,
    melody_page,
    melody_view,
    supported_families,
)
from piece import Piece

GUITAR_8 = "Guitar, 8 frets"
GUITAR_13 = "Guitar, 13 frets"
UKE_6 = "Ukulele, 6 frets"
UKE_10 = "Ukulele, 10 frets"


def _twinkle():
    pitches, durations, lyrics, key, chart, _tempo = load_twinkle()

    return Piece.read(pitches, durations, lyrics, key, chart)


def _piece(pitches, key="C"):
    count = len(pitches.split())

    return Piece.read(pitches, " ".join("1" for _ in range(count)), "", key, "")


def _places(blocks):
    return [(b["string"], b["fret"]) for b in blocks]


# --- where a note can be played ---------------------------------

def test_g4_on_the_guitar_has_three_places_lowest_fret_first():
    """
    G4 = 55. High E (52) fret 3, B (47) fret 8, G (43) fret 12;
    D (38) would need fret 17.
    """

    assert candidates(55, GUITAR_13) == [(5, 3), (4, 8), (3, 12)]


def test_a_shorter_neck_drops_the_far_places():
    assert candidates(55, GUITAR_8) == [(5, 3), (4, 8)]


def test_an_open_string_is_fret_zero_and_nothing_below_it():
    assert candidates(52, GUITAR_13)[0] == (5, 0)
    # D3 (38) is below the A string (33)+... : A fret 5, E fret 10.
    assert candidates(38, GUITAR_13) == [(2, 0), (1, 5), (0, 10)]


def test_ukulele_g4_is_its_first_string_open_not_the_c_string():
    """
    G4 = 55: the G string (first stored) open; the E string (52)
    at fret 3; the C string (48) at fret 7. The G string is not
    the lowest by pitch.
    """

    assert candidates(55, UKE_10) == [(0, 0), (2, 3), (1, 7)]


# --- nearest the nut: Twinkle, worked out by hand ---------------

def test_twinkles_first_phrase_on_the_guitar():
    """
    C4 (48): B string fret 1. G4 (55): high E fret 3. A4 (57):
    high E fret 5.
    """

    blocks = fretted_blocks(_twinkle().phrase(0), GUITAR_13)

    assert _places(blocks) == [
        (4, 1), (4, 1), (5, 3), (5, 3), (5, 5), (5, 5), (5, 3),
    ]
    assert [b["note"] for b in blocks] == list("CCGGAAG")
    assert [b["start"] for b in blocks] == [0, 1, 2, 3, 4, 5, 6]
    assert [b["lyric"] for b in blocks][:2] == ["Twin-", "kle"]


def test_twinkles_second_phrase_on_the_guitar():
    """F4 high E 1, E4 high E open, D4 B string 3, C4 B string 1."""

    blocks = fretted_blocks(_twinkle().phrase(1), GUITAR_13)

    assert _places(blocks) == [
        (5, 1), (5, 1), (5, 0), (5, 0), (4, 3), (4, 3), (4, 1),
    ]


def test_twinkle_is_all_open_strings_or_low_frets_on_the_ukulele():
    """
    First phrase: C4 open C, G4 open G, A4 open A. Second: F4 on
    the E string fret 1, E4 open E, D4 on the C string fret 2.
    """

    first = fretted_blocks(_twinkle().phrase(0), UKE_10)
    second = fretted_blocks(_twinkle().phrase(1), UKE_10)

    assert _places(first) == [
        (1, 0), (1, 0), (0, 0), (0, 0), (3, 0), (3, 0), (0, 0),
    ]
    assert _places(second) == [
        (2, 1), (2, 1), (2, 0), (2, 0), (1, 2), (1, 2), (1, 0),
    ]


def test_a_notes_place_never_depends_on_the_other_notes():
    together = fretted_blocks(_piece("C4 G4 A4 F4"), GUITAR_13)
    alone = [
        fretted_blocks(_piece(note), GUITAR_13)[0]
        for note in ("C4", "G4", "A4", "F4")
    ]

    assert _places(together) == _places(alone)


def test_a_rest_leaves_a_gap_and_no_block():
    assert len(fretted_blocks(_twinkle().phrase(0), GUITAR_13)) == 7


def test_the_whole_tune_is_every_phrase_one_after_another():
    blocks = fretted_blocks(_twinkle(), GUITAR_13)

    assert len(blocks) == 42
    assert blocks[7]["start"] == 8


def test_an_unknown_fingering_is_refused():
    with pytest.raises(ValueError):
        fretted_blocks(_piece("C4"), GUITAR_13, "Anything else")

    assert FINGERINGS == [NEAREST_NUT]


# --- why --------------------------------------------------------

def test_every_block_says_why_it_was_placed_there():
    blocks = fretted_blocks(_piece("G4 E4 C4"), GUITAR_13)

    assert blocks[0]["why"] == (
        "fret 3 on the high E string - the lowest fret that plays G"
    )
    assert blocks[1]["why"] == (
        "open high E string - the nearest the nut there is"
    )


# --- range ------------------------------------------------------

def test_the_guitar_neck_runs_from_e2_to_the_last_fret_shown():
    """High E (52) plus 13 is 65 = F5; plus 8 is 60 = C5."""

    low, high = instrument_range(GUITAR_13)
    assert (low["note"], high["note"]) == ("E2", "F5")
    assert instrument_range(GUITAR_8)[1]["note"] == "C5"


def test_the_ukulele_lowest_note_is_its_c_string_not_its_g():
    """C4 (48) is lowest; A4 (57) plus 10 is 67 = G5; plus 6 is D#5."""

    low, high = instrument_range(UKE_10)
    assert (low["note"], high["note"]) == ("C4", "G5")
    assert instrument_range(UKE_6)[1]["note"] == "D#5"


def test_notes_off_the_neck_are_flagged_and_never_moved():
    blocks = fretted_blocks(_piece("D2 E3 C6"), GUITAR_13)

    assert [b["in_range"] for b in blocks] == [False, True, False]
    assert [b["where"] for b in blocks] == ["below", None, "above"]
    assert blocks[0]["string"] is None and blocks[0]["fret"] is None


def test_the_message_counts_them_and_checks_the_octave_fix():
    blocks = fretted_blocks(_piece("D2 E3"), GUITAR_13)
    message = range_message(blocks, GUITAR_13)

    assert "1 note is below the lowest string (E2)" in message
    assert "Octave up" in message

    wide = fretted_blocks(_piece("D2 C6"), GUITAR_13)

    assert "No single octave shift" in range_message(wide, GUITAR_13)
    assert range_message(fretted_blocks(_piece("E3"), GUITAR_13), GUITAR_13) == ""


def test_the_ukulele_message_names_its_c_as_the_lowest():
    blocks = fretted_blocks(_piece("B3 C4"), UKE_10)

    assert "below the lowest string (C4)" in range_message(blocks, UKE_10)


# --- the drawing ------------------------------------------------

def test_the_tab_has_a_line_per_string_named_at_the_left():
    page = tab_html(
        fretted_blocks(_twinkle().phrase(0), GUITAR_13), GUITAR_13, 8.0
    )

    for name in ("low E", "A", "D", "G", "B", "high E"):
        assert f">{name}</text>" in page

    ukulele = tab_html(
        fretted_blocks(_twinkle().phrase(0), UKE_10), UKE_10, 8.0
    )

    # The picture has the A on top and the G at the bottom, as
    # ukulele tab is read: a smaller y is higher up the page.
    def label_y(page, name):
        match = re.search(
            rf'<text x="[\d.]+" y="([\d.]+)"[^>]*>{name}</text>', page
        )

        return float(match.group(1))

    assert label_y(ukulele, "A") < label_y(ukulele, "G")

    # And the guitar's high E over its low E.
    assert label_y(page, "high E") < label_y(page, "low E")


def test_a_long_tune_wraps_into_rows_of_sixteen_beats():
    piece = _twinkle()
    page = tab_html(
        fretted_blocks(piece, GUITAR_13), GUITAR_13, piece.beats()
    )

    rows = -(-int(piece.beats()) // 16)

    assert page.count(">high E</text>") == rows
    assert rows == 3


def test_fret_numbers_are_in_the_notes_and_the_reason_is_a_tooltip():
    page = tab_html(
        fretted_blocks(_piece("G4"), GUITAR_13), GUITAR_13, 4.0
    )

    assert ">3</text>" in page
    assert "<title>fret 3 on the high E string" in page


def test_an_off_note_is_a_red_block_on_a_line_of_its_own():
    page = tab_html(
        fretted_blocks(_piece("D2 E3"), GUITAR_13), GUITAR_13, 4.0
    )

    assert ">off</text>" in page
    assert 'fill="#c62828"' in page and "D▼" in page


def test_the_view_has_the_warning_the_tab_and_the_legend():
    pieces = Piece.read(*load_wellerman()[:5])
    view = fretted_view(pieces, UKE_10)

    assert "melody-tab" in view
    assert "below the lowest string (C4)" in view
    assert "Nearest the nut" in view


# --- how the section uses it ------------------------------------

def test_guitar_and_ukulele_are_in_the_melody_section_on_the_longer_neck():
    families = supported_families()

    assert default_variant("Guitar", families["Guitar"]) == GUITAR_13
    assert default_variant("Ukulele", families["Ukulele"]) == UKE_10


def test_the_melody_view_hands_guitar_and_ukulele_to_the_tab():
    piece = _twinkle().phrase(0)

    assert "melody-tab" in melody_view(piece, GUITAR_13)
    assert "melody-tab" in melody_view(piece, UKE_6)
    assert "melody-lanes" in melody_view(piece, "Piano, 3 octaves")


def test_the_page_draws_a_tab_view_for_each_fretted_tab():
    pitches, durations, lyrics, key, chart, _tempo = load_twinkle()

    page = melody_page(
        pitches, durations, lyrics, key, chart, "Whole part",
        [GUITAR_13, UKE_10, "Piano, 3 octaves"],
    )

    assert "melody-tab" in page["views"][0]
    assert "melody-tab" in page["views"][1]
    assert "melody-lanes" in page["views"][2]


def test_the_tab_module_never_touches_the_interface_or_the_boxes():
    path = os.path.join(os.path.dirname(__file__), "..", "fretted_tab.py")

    with open(path) as source:
        text = source.read()

    assert "import gradio" not in text and "gr." not in text
    assert "import main" not in text


# --- rows follow the phrases ------------------------------------

from fretted_tab import row_starts


def test_a_row_starts_at_each_phrase():
    """Twinkle has six phrases of eight beats."""

    assert row_starts(_twinkle()) == [0, 8, 16, 24, 32, 40]


def test_a_single_phrase_is_one_row():
    assert row_starts(_twinkle().phrase(2)) == [0]


def test_a_long_phrase_is_cut_at_the_latest_bar_that_fits():
    """
    Twenty-four one-beat notes, no lyrics, no chart: bars every four
    beats. From 0 the latest bar within sixteen beats is 16, and what
    is left (8 beats) is one row.
    """

    piece = _piece(" ".join(["C4"] * 24))

    assert row_starts(piece) == [0, 16]


def test_a_chart_with_odd_bars_decides_where_the_cut_goes():
    """Three-beat bars (0, 3, 6, ...): the latest within 16 is 15."""

    piece = Piece.read(
        " ".join(["C4"] * 24), " ".join(["1"] * 24), "", "C",
        "| " + " | ".join(["C . ."] * 8) + " |",
    )

    assert row_starts(piece) == [0, 15]


def test_a_phrase_cut_never_leaves_a_row_over_sixteen_beats():
    piece = _piece(" ".join(["C4"] * 50))
    starts = row_starts(piece) + [50]

    assert all(b - a <= 16 for a, b in zip(starts, starts[1:]))


def test_rows_are_drawn_one_per_start_and_as_wide_as_their_phrase():
    piece = _twinkle()
    blocks = fretted_blocks(piece, GUITAR_13)
    page = tab_html(
        blocks, GUITAR_13, piece.beats(), piece.chart, row_starts(piece)
    )

    assert page.count(">high E</text>") == 6
    # Eight beats of 48 plus the margins: 62 + 384 + 12 = 458.
    assert 'viewBox="0 0 458 ' in page
    # Never stretched past its natural size.
    assert "max-width:468px" in page


def test_a_note_goes_in_the_row_of_its_phrase():
    """The first note of phrase two starts at beat 8, row two, at x=62."""

    piece = _twinkle()
    blocks = fretted_blocks(piece, GUITAR_13)
    page = tab_html(
        blocks, GUITAR_13, piece.beats(), piece.chart, row_starts(piece)
    )

    # Every phrase opens on a note at the row's own left edge, so
    # six rows put six note blocks at x=62.
    assert page.count('<rect x="62.0" y=') == 6


def test_with_no_bar_line_to_cut_at_a_long_phrase_is_cut_at_sixteen():
    """One 20-beat bar: nowhere to cut but the limit."""

    piece = Piece.read(
        " ".join(["C4"] * 20), " ".join(["1"] * 20), "", "C",
        "| C " + " ".join(["."] * 19) + " |",
    )

    assert row_starts(piece) == [0, 16]
