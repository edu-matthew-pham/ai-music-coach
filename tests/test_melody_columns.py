"""
The Melody lanes in columns and pages (melody_lanes.py).

Python draws a long song as one piece per phrase under one header
(phrase_ranges); in the browser FLOW_JS packs the pieces into columns
that fit the height left on screen and the columns into pages turned
with the arrows. These tests pin the Python half; the browser half is
checked in the real app (BUILDNOTES-append-melody-columns.md).

Expected pieces are worked out by hand from the Wellerman's phrase
starts, never taken from the code under test. Its 200 beats start a
phrase at

    0 11 19.5 27 36 43.5 52 59 68 75 83.5 91 100 107.5 116 123
    136 143.5 151.5 160 168 175.5 184 191

so it is 24 pieces: (0, 11), (11, 19.5), ... (191, 200).
"""

import ast
import os
import re

from examples import load_wellerman
from melody_lanes import (
    AUTO_SCALE,
    COLUMN_CHOICES,
    COLUMNS_AUTO,
    COLUMNS_ONE,
    COLUMNS_TWO,
    FLOW_JS,
    MAX_AUTO_COLUMNS,
    _note_slice,
    _span_slice,
    lanes_html,
    melody_blocks,
    melody_page,
    melody_view,
    phrase_ranges,
)
from fretted_tab import row_starts
from music import WHOLE_PART
from piece import Piece

KALIMBA = "Kalimba, 41 keys"
WELLERMAN_STARTS = [
    0, 11, 19.5, 27, 36, 43.5, 52, 59, 68, 75, 83.5, 91, 100, 107.5,
    116, 123, 136, 143.5, 151.5, 160, 168, 175.5, 184, 191,
]


def _wellerman():
    pitches, durations, lyrics, key, chart, _tempo = load_wellerman()

    return Piece.read(pitches, durations, lyrics, key, chart)


def _pieces(html):
    """Each phrase piece's HTML, in order."""

    return html.split('class="melody-cell"')[1:]


def _data(html, name):
    return re.search(rf'data-{name}="([^"]*)"', html).group(1)


# --- where the pieces fall -----------------------------------------

def test_one_column_is_the_whole_song_as_one_piece():
    assert phrase_ranges([0, 10, 20], 64, COLUMNS_ONE) == [(0, 64)]


def test_a_song_of_one_phrase_is_one_piece():
    assert phrase_ranges([0], 8, COLUMNS_AUTO) == [(0, 8)]
    assert phrase_ranges([], 8, COLUMNS_TWO) == [(0, 8)]


def test_every_phrase_start_begins_a_piece():
    expected = list(zip(WELLERMAN_STARTS, WELLERMAN_STARTS[1:] + [200]))

    assert phrase_ranges(WELLERMAN_STARTS, 200, COLUMNS_AUTO) == expected
    assert phrase_ranges(WELLERMAN_STARTS, 200, COLUMNS_TWO) == expected


def test_the_wellerman_cuts_are_its_tab_rows():
    # One list of phrase starts for the guitar tab and the lanes.
    assert row_starts(_wellerman()) == WELLERMAN_STARTS


def test_repeated_or_outside_starts_add_no_piece():
    assert phrase_ranges([0, 0, 8, 8, 16, -1, 20], 16, COLUMNS_AUTO) == [
        (0, 8), (8, 16)
    ]


# --- what goes in which piece --------------------------------------

def test_a_note_belongs_to_the_piece_it_begins_in_and_is_moved_up():
    blocks = [
        {"start": 35.5, "length": 0.5},
        {"start": 35, "length": 2},
        {"start": 36, "length": 1},
        {"start": 40, "length": 2},
    ]

    first = _note_slice(blocks, 0, 36)
    second = _note_slice(blocks, 36, 68)

    # The note at 35 runs on past the cut but BEGAN in the first.
    assert [b["start"] for b in first] == [35.5, 35]
    assert [b["start"] for b in second] == [0, 4]
    # Not changed in place: the boxes' blocks are read only.
    assert blocks[2]["start"] == 36


def test_a_chord_over_a_cut_is_in_both_pieces_clipped_to_each():
    spans = [
        {"start": 30, "length": 12},
        {"start": 36, "length": 4},
        {"start": 20, "length": 16},
    ]

    first = _span_slice(spans, 0, 36)
    second = _span_slice(spans, 36, 68)

    assert [(s["start"], s["length"]) for s in first] == [(30, 6), (20, 16)]
    # The chord that ENDS at the cut is not in the second piece.
    assert [(s["start"], s["length"]) for s in second] == [(0, 6), (0, 4)]


# --- the drawing ---------------------------------------------------

def test_one_column_draws_the_one_strip_with_nothing_to_pack():
    html = melody_view(_wellerman(), KALIMBA, columns=COLUMNS_ONE)

    assert "melody-flow" not in html
    assert _pieces(html) == []


def test_a_long_song_is_one_piece_per_phrase_under_one_header():
    html = melody_view(_wellerman(), KALIMBA)

    assert len(_pieces(html)) == 24
    assert html.count('class="melody-head"') == 1
    froms = re.findall(r'class="melody-cell" data-from="([^"]+)"', html)
    assert [float(f) for f in froms] == WELLERMAN_STARTS


def test_a_short_phrase_is_the_same_picture_whatever_columns_says():
    short = Piece.read("A4 A4 A4 A4", "1 1 1 1", "a b c d", "F",
                       "| F . . . |")

    assert melody_view(short, KALIMBA, columns=COLUMNS_AUTO) == (
        melody_view(short, KALIMBA, columns=COLUMNS_ONE)
    )


def test_no_note_is_lost_or_drawn_twice_across_the_pieces():
    piece = _wellerman()

    def lyrics(html):
        return re.findall(r'font-size="12" fill="#37474f">([^<]*)<', html)

    whole = lyrics(melody_view(piece, KALIMBA, columns=COLUMNS_ONE))
    cut = lyrics(melody_view(piece, KALIMBA, columns=COLUMNS_AUTO))

    assert len(whole) > 100
    assert cut == whole


def test_a_piece_numbers_its_beats_from_the_songs_start():
    pieces = _pieces(melody_view(_wellerman(), KALIMBA))

    # The second piece is beats 11 to 19.5; its bar line at beat 12
    # is the song's beat 13.
    assert "beat 13<" in pieces[1]
    assert "beat 1<" in pieces[0]
    assert all("beat 1<" not in later for later in pieces[1:])


def test_a_piece_leaves_the_line_at_its_end_to_the_next_piece():
    pieces = _pieces(melody_view(_wellerman(), KALIMBA))

    # 0 to 11: lines at beats 0..10 (11 is the next piece's first).
    assert pieces[0].count("<line ") == 11
    # The last, 191 to 200, draws its closing line: 191..200.
    assert pieces[-1].count("<line ") == 10


def test_only_the_last_piece_keeps_the_big_margin_under_it():
    pieces = _pieces(melody_view(_wellerman(), KALIMBA))

    def height(piece):
        return int(re.search(r'viewBox="0 0 \d+ (\d+)"', piece).group(1))

    # 11 beats x 28px, a 4px margin, the 10px pad on top.
    assert height(pieces[0]) == 11 * 28 + 4 + 10
    # 9 beats, the 24px margin the one strip always had.
    assert height(pieces[-1]) == 9 * 28 + 24 + 10


def test_a_piece_starting_part_way_through_a_beat_keeps_the_grid_true():
    third = _pieces(melody_view(_wellerman(), KALIMBA))[2]

    # Beats 19.5 to 27: the first line is beat 20, half a beat (14px)
    # down, and no line sits above the piece.
    assert re.search(r'<line x1="\d+" x2="\d+" y1="14.0"', third)
    assert 'y1="-' not in third


def test_every_piece_names_the_chord_playing_at_its_top():
    pieces = _pieces(melody_view(_wellerman(), KALIMBA))

    # The chart has Bb at beat 36 (read off the Wellerman's chart in
    # examples.py); the fifth piece starts there.
    assert ">Bb</text>" in pieces[4]
    assert all('<rect x="4" y=' in piece for piece in pieces)


def test_the_page_is_told_how_to_pack():
    auto = melody_view(_wellerman(), KALIMBA, columns=COLUMNS_AUTO)
    two = melody_view(_wellerman(), KALIMBA, columns=COLUMNS_TWO)

    assert _data(auto, "columns") == "auto"
    assert _data(auto, "max") == str(MAX_AUTO_COLUMNS) == "3"
    assert _data(two, "columns") == "two"
    assert _data(two, "max") == "2"
    # The kalimba picture is 878 wide (measured); 72% of it.
    assert abs(int(_data(auto, "least")) - int(878 * AUTO_SCALE)) <= 2


def test_a_piano_wants_more_width_than_a_kalimba_for_a_column():
    piece = _wellerman()
    kalimba = melody_view(piece, KALIMBA)
    piano = melody_view(piece, "Piano, 3 octaves")

    assert int(_data(piano, "least")) > int(_data(kalimba, "least"))


def test_a_cropped_keyboard_keeps_its_widest_when_packed():
    html = melody_view(_wellerman(), "Piano, 2 octaves")
    cap = int(_data(html, "cap"))

    if cap:
        assert f"max-width:{cap}px" in html
    else:
        assert "max-width" not in html.split("melody-head")[0]


def test_an_empty_song_is_not_cut():
    assert lanes_html([], KALIMBA, 0, columns=COLUMNS_TWO)


# --- the browser half, as far as it can be read --------------------

def test_the_packing_reads_what_python_writes():
    for name in ("columns", "least", "max", "cap"):
        assert f"dataset.{name}" in FLOW_JS
    for name in (".melody-flow", ".melody-cells", ".melody-cell",
                 ".melody-head"):
        assert name in FLOW_JS


def test_the_packing_counts_the_controls_above_the_lanes_in_full_screen():
    # The room is the section's height less everything above the lanes.
    assert "section.clientHeight - above" in FLOW_JS
    assert "getBoundingClientRect().top" in FLOW_JS


def test_the_arrows_turn_the_page_but_not_while_typing():
    assert "'ArrowLeft'" in FLOW_JS and "'ArrowRight'" in FLOW_JS
    assert "input, textarea, select" in FLOW_JS


def test_the_packing_starts_again_when_gradio_patches_a_view():
    assert "if (!packed) { flow.__cells = null; }" in FLOW_JS


def test_in_the_page_one_column_stays_the_scrolling_strip():
    assert "const strip = columns === 1 && !full;" in FLOW_JS


# --- the page and the screen ---------------------------------------

def test_the_page_passes_columns_down_to_every_tab():
    pitches, durations, lyrics, key, chart, _tempo = load_wellerman()
    kwargs = dict(
        pitch_text=pitches, duration_text=durations, lyric_text=lyrics,
        key_text=key, chart_text=chart, phrase_label=WHOLE_PART,
        instruments=[KALIMBA],
    )

    cut = melody_page(**kwargs, columns=COLUMNS_TWO)["views"][0]
    one = melody_page(**kwargs, columns=COLUMNS_ONE)["views"][0]

    assert len(_pieces(cut)) == 24
    assert _pieces(one) == []


def test_the_choices_are_auto_one_and_two_with_auto_first():
    assert COLUMN_CHOICES == [
        COLUMNS_AUTO, COLUMNS_ONE, COLUMNS_TWO
    ]


MAIN = os.path.join(os.path.dirname(__file__), "..", "main.py")


def _main_text():
    with open(MAIN) as source:
        return source.read()


def test_the_columns_choice_is_on_the_screen_and_wired_like_the_others():
    text = _main_text()

    assert "melody_columns = gr.Radio(" in text
    assert "melody_lanes.COLUMN_CHOICES" in text
    assert "value=melody_lanes.COLUMNS_AUTO" in text
    assert "melody_columns.change" in text

    inputs = [
        node for node in ast.walk(ast.parse(text))
        if isinstance(node, ast.Assign)
        and getattr(node.targets[0], "id", "") == "melody_inputs"
    ][0]

    assert "melody_columns" in ast.dump(inputs)


def test_the_top_of_the_lanes_choice_is_gone_and_compact_is_what_is_drawn():
    text = _main_text()

    assert "melody_header" not in text
    assert "melody_lanes.HEADER_COMPACT" in text


def test_the_packing_is_installed_once_when_the_page_loads():
    text = _main_text()

    assert "js=melody_lanes.FLOW_JS" in text


# --- the controls: one slim bar, options on their own tabs --------

def test_only_the_guitar_and_ukulele_tabs_show_the_fretted_options():
    from melody_lanes import option_rows

    assert option_rows("Guitar") == (True, False)
    assert option_rows("Ukulele") == (True, False)


def test_only_the_flute_and_sax_tabs_show_the_wind_option():
    from melody_lanes import option_rows

    assert option_rows("Flute") == (False, True)
    assert option_rows("Alto sax") == (False, True)


def test_the_other_tabs_show_neither_row():
    from melody_lanes import option_rows

    for family in ("Piano", "Kalimba", "Lever harp"):
        assert option_rows(family) == (False, False)


def test_the_option_rows_start_hidden_and_follow_the_tab_chosen():
    text = _main_text()

    assert "gr.Row(visible=False) as melody_fretted_row" in text
    assert "gr.Row(visible=False) as melody_wind_row" in text
    assert "melody_tab.select(" in text
    assert "melody_lanes.option_rows(family)" in text
    assert "outputs=[melody_fretted_row, melody_wind_row]" in text


def test_the_chords_go_choice_is_a_dropdown_in_the_slim_bar():
    text = _main_text()

    assert "melody_placement = gr.Dropdown(" in text


def test_full_screen_hides_the_page_heading_and_sentence():
    from melody_lanes import MELODY_CSS

    assert "#melody.melody-full .melody-intro { display: none; }" in (
        MELODY_CSS
    )
    # The heading, the sentence and the status line.
    assert _main_text().count('elem_classes="melody-intro"') == 3


def test_full_screen_does_not_squeeze_the_sections_blocks():
    from melody_lanes import MELODY_CSS

    # A fixed-height column shrinks its children unless told not to;
    # the phrase list and status line were drawn as slivers.
    assert "#melody.melody-full > * { flex-shrink: 0; }" in MELODY_CSS


def test_the_phrase_list_is_in_the_slim_bar_with_the_other_controls():
    text = _main_text()
    bar = text.index("            with gr.Row():\n\n                melody_phrase")

    assert bar < text.index("melody_show = gr.CheckboxGroup(")
    assert text.index("melody_phrase = gr.Dropdown(") < text.index(
        "melody_show = gr.CheckboxGroup("
    )
    # And it is no longer a line of its own above the bar.
    assert text.count("melody_phrase = gr.Dropdown(") == 1


def test_the_size_choice_sits_on_the_tab_names_line():
    from melody_lanes import MELODY_CSS

    assert "#melody .tabitem .sheet-size {" in MELODY_CSS
    assert "position: absolute; top: 0; right: 0;" in MELODY_CSS
