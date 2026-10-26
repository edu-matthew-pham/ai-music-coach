"""
The Melody lanes in columns (melody_lanes.py): a long song cut at
phrase starts into strips of about one screen, drawn side by side.

Expected cuts are worked out by hand from the Wellerman's phrase
starts, never taken from the code under test. Its 200 beats start
a phrase at

    0 11 19.5 27 36 43.5 52 59 68 75 83.5 91 100 107.5 116 123
    136 143.5 151.5 160 168 175.5 184 191

Six strips (200 / 32 = 6.25, rounded); the even shares fall at
33.3 66.7 100 133.3 166.7, and the nearest phrase starts are
36 68 100 136 168.
"""

import ast
import os
import re

from examples import load_wellerman
from melody_lanes import (
    AUTO_SCALE,
    CHUNK_BEATS,
    COLUMN_CHOICES,
    COLUMNS_AUTO,
    COLUMNS_ONE,
    COLUMNS_TWO,
    _note_slice,
    _span_slice,
    chunk_ranges,
    lanes_html,
    melody_blocks,
    melody_page,
    melody_view,
)
from fretted_tab import row_starts
from music import WHOLE_PART
from piece import Piece

KALIMBA = "Kalimba, 41 keys"
WELLERMAN_CUTS = [36, 68, 100, 136, 168]
WELLERMAN_RANGES = [
    (0, 36), (36, 68), (68, 100), (100, 136), (136, 168), (168, 200)
]


def _wellerman():
    pitches, durations, lyrics, key, chart, _tempo = load_wellerman()

    return Piece.read(pitches, durations, lyrics, key, chart)


def _strips(html):
    return html.count('class="melody-chunk"')


# --- where the cuts fall -----------------------------------------

def test_one_column_is_the_whole_song_as_one_strip():
    assert chunk_ranges([0, 10, 20], 64, COLUMNS_ONE) == [(0, 64)]


def test_a_song_of_a_screen_or_less_is_one_strip():
    assert chunk_ranges([0, 4], 8, COLUMNS_AUTO) == [(0, 8)]
    assert chunk_ranges([0, 8], 40, COLUMNS_AUTO) == [(0, 40)]


def test_each_cut_is_the_phrase_start_nearest_an_even_share():
    cuts = [0, 11, 19.5, 27, 36, 43.5, 52, 59, 68, 75, 83.5, 91, 100,
            107.5, 116, 123, 136, 143.5, 151.5, 160, 168, 175.5, 184,
            191]

    assert chunk_ranges(cuts, 200, COLUMNS_AUTO) == WELLERMAN_RANGES


def test_a_phrase_is_never_split_whatever_the_even_share_says():
    # Halfway is 32; the starts are 10, 22 and 40, and 40 is nearer.
    assert chunk_ranges([0, 10, 22, 40], 64, COLUMNS_AUTO) == [
        (0, 40), (40, 64)
    ]


def test_a_tie_between_two_phrase_starts_goes_to_the_earlier():
    assert chunk_ranges([0, 30, 34], 64, COLUMNS_AUTO) == [
        (0, 30), (30, 64)
    ]


def test_the_strips_tile_the_song_with_no_gap_and_no_overlap():
    ranges = chunk_ranges([0, 11, 19.5, 27, 36], 48, COLUMNS_TWO)

    assert ranges[0][0] == 0 and ranges[-1][1] == 48

    for before, after in zip(ranges, ranges[1:]):
        assert before[1] == after[0]


def test_two_columns_cuts_even_a_short_song_in_two():
    assert chunk_ranges([0, 4], 8, COLUMNS_TWO) == [(0, 4), (4, 8)]


def test_a_song_with_no_phrase_start_to_cut_at_is_cut_at_a_whole_beat():
    assert chunk_ranges([], 64, COLUMNS_TWO) == [(0, 32), (32, 64)]


def test_one_phrase_start_to_cut_at_gives_one_cut_not_a_repeat_of_it():
    assert chunk_ranges([0, 19.5], 200, COLUMNS_TWO) == [
        (0, 19.5), (19.5, 200)
    ]


# --- what goes on which strip ------------------------------------

def test_a_note_belongs_to_the_strip_it_begins_in_and_is_moved_up():
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


def test_a_chord_over_a_cut_is_on_both_strips_clipped_to_each():
    spans = [
        {"start": 30, "length": 12},
        {"start": 36, "length": 4},
        {"start": 20, "length": 16},
    ]

    first = _span_slice(spans, 0, 36)
    second = _span_slice(spans, 36, 68)

    assert [(s["start"], s["length"]) for s in first] == [(30, 6), (20, 16)]
    # The chord that ENDS at the cut is not on the second strip.
    assert [(s["start"], s["length"]) for s in second] == [(0, 6), (0, 4)]


# --- the drawing ---------------------------------------------------

def test_one_column_draws_no_grid_at_all():
    html = melody_view(_wellerman(), KALIMBA, columns=COLUMNS_ONE)

    assert "melody-grid" not in html
    assert _strips(html) == 0


def test_a_long_song_is_six_strips_by_default():
    html = melody_view(_wellerman(), KALIMBA)

    assert _strips(html) == 6


def test_a_short_phrase_is_the_same_picture_whatever_columns_says():
    piece = _wellerman()
    one = melody_view(piece, KALIMBA, columns=COLUMNS_ONE)

    # Eight beats of the same song, cut as a phrase.
    short = Piece.read("A4 A4 A4 A4", "1 1 1 1", "a b c d", "F",
                       "| F . . . |")
    assert melody_view(short, KALIMBA, columns=COLUMNS_AUTO) == (
        melody_view(short, KALIMBA, columns=COLUMNS_ONE)
    )
    assert "melody-grid" not in one


def test_every_strip_has_the_lane_header_over_it():
    html = melody_view(_wellerman(), KALIMBA, columns=COLUMNS_TWO)

    assert html.count('class="melody-head"') == 6
    assert html.count("compact-tine") == 6 * html.split(
        'class="melody-chunk"'
    )[1].count("compact-tine")


def test_no_note_is_lost_or_drawn_twice_across_the_strips():
    piece = _wellerman()

    def lyrics(html):
        return re.findall(r'font-size="12" fill="#37474f">([^<]*)<', html)

    whole = lyrics(melody_view(piece, KALIMBA, columns=COLUMNS_ONE))
    cut = lyrics(melody_view(piece, KALIMBA, columns=COLUMNS_TWO))

    assert len(whole) > 100
    assert cut == whole


def test_a_strip_numbers_its_beats_from_the_songs_start_not_its_own():
    html = melody_view(_wellerman(), KALIMBA, columns=COLUMNS_TWO)

    # Strip two begins at beat 36, which is beat number 37.
    assert "beat 37<" in html
    assert html.count("beat 1<") == 1


def test_a_strip_that_starts_part_way_through_a_beat_keeps_the_grid_true():
    piece = _wellerman()
    blocks = melody_blocks(piece, KALIMBA)
    html = lanes_html(
        blocks, KALIMBA, piece.beats(), piece.chart, header="Compact",
        columns=COLUMNS_TWO, cuts=[0, 19.5],
    )
    second = html.split('class="melody-chunk"')[2]

    # Beat 20 is half a beat (14px) below the top of a strip that
    # starts at 19.5, and the first beat line is that one.
    assert re.search(r'<line x1="\d+" x2="\d+" y1="14.0"', second)
    # And no line above the top of the strip.
    assert 'y1="-' not in second


def test_every_strip_names_the_chord_playing_at_its_top():
    html = melody_view(_wellerman(), KALIMBA, columns=COLUMNS_TWO)
    strips = html.split('class="melody-chunk"')[1:]

    # The chart is Dm Dm Dm Gm ... and has Bb at beat 36 (read off
    # the Wellerman's chart in examples.py).
    assert ">Dm</text>" in strips[0]
    assert ">Bb</text>" in strips[1]
    assert all('<rect x="4" y=' in strip for strip in strips)


def test_two_columns_is_two_whatever_the_width():
    html = melody_view(_wellerman(), KALIMBA, columns=COLUMNS_TWO)

    assert "grid-template-columns:repeat(2," in html
    assert "@container" not in html


def test_auto_lets_the_page_fit_as_many_as_keep_the_note_names_readable():
    html = melody_view(_wellerman(), KALIMBA, columns=COLUMNS_AUTO)
    least = re.search(r"repeat\(auto-fit,minmax\((\d+)px", html)

    assert least
    # The kalimba picture is 878 wide (measured); 72% of it.
    assert 600 < int(least.group(1)) < 700
    assert int(least.group(1)) == int(878 * AUTO_SCALE) or (
        abs(int(least.group(1)) - int(878 * AUTO_SCALE)) <= 2
    )


def test_where_only_one_strip_fits_it_is_one_tall_strip_again():
    html = melody_view(_wellerman(), KALIMBA, columns=COLUMNS_AUTO)
    least = int(re.search(r"minmax\((\d+)px", html).group(1))

    assert "@container melody (max-width:" in html
    # Below two strips (and the gap) wide: no gap, one header kept.
    assert f"max-width:{2 * least + 13}px" in html
    assert ".melody-chunk{display:contents}" in html
    assert ".melody-chunk+.melody-chunk .melody-head{display:none}" in (
        html
    )


def test_a_piano_wants_more_width_than_a_kalimba_for_two_columns():
    piece = _wellerman()
    kalimba = melody_view(piece, KALIMBA, columns=COLUMNS_AUTO)
    piano = melody_view(piece, "Piano, 3 octaves", columns=COLUMNS_AUTO)

    def least(html):
        return int(re.search(r"minmax\((\d+)px", html).group(1))

    assert least(piano) > least(kalimba)


def test_an_empty_song_is_not_cut():
    assert lanes_html([], KALIMBA, 0, columns=COLUMNS_TWO)


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

    assert _strips(cut) == 6
    assert _strips(one) == 0


def test_the_choices_are_auto_one_and_two_with_auto_first():
    assert COLUMN_CHOICES == [
        COLUMNS_AUTO, COLUMNS_ONE, COLUMNS_TWO
    ]
    assert CHUNK_BEATS == 32


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


def test_the_cuts_come_from_the_same_phrase_starts_as_the_tab_rows():
    # One list of phrase starts for the guitar tab and the lanes.
    assert row_starts(_wellerman())[0] == 0


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
    assert _main_text().count('elem_classes="melody-intro"') == 2


def test_full_screen_does_not_squeeze_the_sections_blocks():
    from melody_lanes import MELODY_CSS

    # A fixed-height column shrinks its children unless told not to;
    # the phrase list and status line were drawn as slivers.
    assert "#melody.melody-full > * { flex-shrink: 0; }" in MELODY_CSS
