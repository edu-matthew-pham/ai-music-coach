"""
The melody lanes on the lever harp and the piano (stage 2 of
PLAN-melody-lanes.md). Expected lanes are worked out by hand.

Harp strings, lowest first, are index 0..18:

    F3 G3 A3 B3 C4 D4 E4 F4 G4 A4 B4 C5 D5 E5 F5 G5 A5 B5 C6

A sharp or flat is the string below it with its lever up.

The piano's keyboard starts at C3. A lane's index is its pitch
counted in semitones with C0 = 0, so C3 is 36, middle C (C4) is
48 and B5 is 71.
"""

from examples import load_twinkle, load_wellerman
from melody_lanes import (
    LEGENDS,
    lanes_for,
    lanes_html,
    melody_blocks,
    melody_view,
    range_message,
    visible_lanes,
)
from piece import Piece

HARP = "Lever harp, 19 strings"
PIANO_2 = "Piano, 2 octaves"
PIANO_3 = "Piano, 3 octaves"


def _twinkle():
    pitches, durations, lyrics, key, chart, _tempo = load_twinkle()

    return Piece.read(pitches, durations, lyrics, key, chart)


def _piece(pitches, key="C"):
    count = len(pitches.split())

    return Piece.read(pitches, " ".join("1" for _ in range(count)), "", key, "")


# --- the harp ----------------------------------------------------

def test_the_harp_has_nineteen_lanes_with_c_red_and_f_blue():
    lanes = lanes_for(HARP)

    assert [lane["label"] for lane in lanes] == [
        "F3", "G3", "A3", "B3", "C4", "D4", "E4", "F4", "G4", "A4",
        "B4", "C5", "D5", "E5", "F5", "G5", "A5", "B5", "C6",
    ]

    by_label = {lane["label"]: lane["colour"] for lane in lanes}

    for red in ("C4", "C5", "C6"):
        assert by_label[red] == "#e57373"

    for blue in ("F3", "F4", "F5"):
        assert by_label[blue] == "#64b5f6"

    assert by_label["D4"] == "#b0bec5"


def test_twinkle_on_the_harp_goes_up_and_down_the_strings():
    first = melody_blocks(_twinkle().phrase(0), HARP)
    second = melody_blocks(_twinkle().phrase(1), HARP)

    # C4 is string 4, G4 string 8, A4 string 9.
    assert [block["lane"] for block in first] == [4, 4, 8, 8, 9, 9, 8]
    # F4 7, E4 6, D4 5, C4 4.
    assert [block["lane"] for block in second] == [7, 7, 6, 6, 5, 5, 4]
    assert not any(block["lever"] for block in first + second)
    assert all(block["thumb"] is None for block in first)


def test_a_sharp_or_flat_is_the_string_below_with_its_lever_up():
    blocks = melody_blocks(_piece("F4 F#4 Bb4 A4"), HARP)

    # F4 string 7 (lever down); F#4 the same string, lever up;
    # Bb4 is A4's string (9) with the lever up; A4 string 9, down.
    assert [block["lane"] for block in blocks] == [7, 7, 9, 9]
    assert [block["lever"] for block in blocks] == [False, True, True, False]


def test_the_harp_spans_f3_to_c6_and_one_more_by_the_top_lever():
    low = melody_blocks(_piece("E3 F3"), HARP)
    high = melody_blocks(_piece("C#6 D6"), HARP)

    assert [block["in_range"] for block in low] == [False, True]
    assert low[0]["where"] == "below"

    # C#6 is C6's lever; D6 is above everything.
    assert [block["in_range"] for block in high] == [True, False]
    assert high[1]["where"] == "above"


def test_the_harp_message_says_strings_and_what_octave_shift_fits():
    blocks = melody_blocks(_piece("C3 D3 E4"), HARP)

    message = range_message(blocks, HARP)

    assert "2 notes are below the lowest string (F3)" in message
    assert "Octave up" in message


def test_the_harp_picture_draws_a_lever_tab_only_for_a_raised_lever():
    plain = lanes_html(
        melody_blocks(_piece("F4 A4"), HARP), HARP, 2.0
    )
    raised = lanes_html(
        melody_blocks(_piece("F#4 A4"), HARP), HARP, 2.0
    )

    assert "↑" not in plain and "stroke=\"#607d8b\"" not in plain
    assert "F#↑" in raised and "stroke=\"#607d8b\"" in raised


# --- the piano ---------------------------------------------------

def test_the_piano_starts_at_c3_and_has_white_and_black_lanes():
    three = lanes_for(PIANO_3)
    two = lanes_for(PIANO_2)

    assert [lane["index"] for lane in three][:3] == [36, 37, 38]
    assert three[0]["label"] == "C3" and three[0]["kind"] == "white"
    assert three[1]["kind"] == "black" and three[1]["sub"] == "C#3"

    assert len(three) == 36 and len(two) == 24
    assert sum(lane["kind"] == "white" for lane in three) == 21
    assert sum(lane["kind"] == "black" for lane in three) == 15
    assert three[-1]["index"] == 71


def test_twinkle_on_the_piano_sits_on_its_own_pitch():
    first = melody_blocks(_twinkle().phrase(0), PIANO_3)

    # Middle C is 48, G4 is 55, A4 is 57.
    assert [block["lane"] for block in first] == [48, 48, 55, 55, 57, 57, 55]
    assert not any(block["black"] for block in first)


def test_a_black_key_is_marked_as_black():
    blocks = melody_blocks(_piece("C4 C#4 Eb4"), PIANO_3)

    assert [block["lane"] for block in blocks] == [48, 49, 51]
    assert [block["black"] for block in blocks] == [False, True, True]


def test_the_two_octave_piano_runs_out_at_b4():
    blocks = melody_blocks(_piece("B4 C5"), PIANO_2)

    assert [block["in_range"] for block in blocks] == [True, False]
    assert "above the highest (B4)" in range_message(blocks, PIANO_2)


def test_the_piano_message_says_keys():
    blocks = melody_blocks(_piece("B2 C4"), PIANO_3)

    assert "1 note is below the lowest key (C3)" in range_message(
        blocks, PIANO_3
    )


def test_the_piano_is_cropped_to_the_song_with_two_keys_spare():
    """
    Twinkle's first phrase is C4 (48) to A4 (57). Two spare keys
    either side is 46 to 59; 46 is a black key, so the crop starts
    one lower, on the white A3 (45); 59 is the white B4.
    """

    blocks = melody_blocks(_twinkle().phrase(0), PIANO_3)
    lanes = visible_lanes(blocks, PIANO_3)

    assert [lane["index"] for lane in lanes] == list(range(45, 60))
    assert lanes[0]["kind"] == "white"


def test_a_song_wider_than_the_crop_is_not_cropped_off():
    blocks = melody_blocks(_piece("C3 B5"), PIANO_3)

    # Clamped to the keyboard itself.
    assert [lane["index"] for lane in visible_lanes(blocks, PIANO_3)] == (
        list(range(36, 72))
    )


def test_the_harp_and_kalimba_are_never_cropped():
    blocks = melody_blocks(_piece("C4 D4"), HARP)

    assert len(visible_lanes(blocks, HARP)) == 19


def test_the_piano_picture_has_narrow_black_blocks_and_a_narrow_wrapper():
    blocks = melody_blocks(_piece("C4 C#4"), PIANO_3)
    page = lanes_html(blocks, PIANO_3, 2.0)

    # A white lane is 44 wide (the picture's white key), so its
    # block is 36; a black lane is 26 wide, its block 22.
    assert 'width="36"' in page and 'width="22"' in page
    assert "max-width:" in page


# --- songs through the whole view --------------------------------

def test_every_instrument_draws_twinkle_and_the_wellerman():
    wellerman = Piece.read(*load_wellerman()[:5])

    for instrument in (
        "Kalimba, 34 keys", "Kalimba, 41 keys", HARP, PIANO_2, PIANO_3,
    ):
        for piece in (_twinkle(), wellerman):
            view = melody_view(piece, instrument)

            assert "melody-lanes" in view
            assert "<svg" in view


def test_the_legends_say_what_each_picture_means():
    assert "lever" in LEGENDS["Lever harp"]
    assert "white" in LEGENDS["Piano"]
    assert "blue" in LEGENDS["Kalimba"]
