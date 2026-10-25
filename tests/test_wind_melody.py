"""
The melody on a flute or an alto sax (wind_melody.py,
PLAN-wind-melody.md). Expected values are worked out by hand from the
song, never taken from the code under test.

Pitch numbers count semitones with C0 = 0, so C4 = 48. The sounding
(concert) pitch is what the boxes hold; an E-flat alto sax reads a
major sixth above it, i.e. +9 semitones: sounding F4 (53) is written
D5 (62), sounding C5 (60) is written A5 (69).

The fingering tables used here are INVENTED for the tests (so that
adjacent notes differ by a known number of keys). They are not
fingerings; the shipped table is wind_fingerings.FINGERINGS.
"""

import re

import pytest

import wind_fingerings
from chords import chord_semitones
from melody_lanes import melody_page, melody_view, supported_families
from piece import Piece
from wind_melody import (
    WRITTEN_RANGE,
    chord_roles,
    fold_repeats,
    keys_changed,
    wind_blocks,
    wind_rows,
    wind_view,
)

FLUTE = "Flute"
SAX = "Alto sax"

# Frere Jacques in F, 32 beats, eight phrases, the chord F throughout
# (four beats a bar, eight bars).
PITCHES = (
    "F4 G4 A4 F4  F4 G4 A4 F4  A4 Bb4 C5  A4 Bb4 C5  "
    "C5 D5 C5 Bb4 A4 F4  C5 D5 C5 Bb4 A4 F4  F4 C4 F4  F4 C4 F4"
)
LENGTHS = (
    "1 1 1 1  1 1 1 1  1 1 2  1 1 2  "
    "0.5 0.5 0.5 0.5 1 1  0.5 0.5 0.5 0.5 1 1  1 1 2  1 1 2"
)
WORDS = (
    "Are you sleep- ing,\nare you sleep- ing,\nBro- ther John?\n"
    "Bro- ther John?\nMorn- ing bells are ring- ing,\n"
    "morn- ing bells are ring- ing,\nDing dang dong,\nding dang dong."
)
CHART = "| F . . . " * 8 + "|"


def _jacques(chart=CHART, key="F"):
    return Piece.read(PITCHES, LENGTHS, WORDS, key, chart)


def _piece(pitches, key="F", chart=""):
    count = len(pitches.split())

    return Piece.read(
        pitches, " ".join("1" for _ in range(count)), "", key, chart
    )


# Invented: each note a distinct set of keys of the right layout.
def _table(entries):
    return {
        FLUTE: {pitch: {"keys": keys} for pitch, keys in entries.items()},
        SAX: {},
    }


def _sax_table(entries):
    return {
        FLUTE: {},
        SAX: {pitch: {"keys": keys} for pitch, keys in entries.items()},
    }


# --- chord roles ------------------------------------------------

def test_chord_roles_are_named_from_the_root():
    assert chord_roles("F") == {5: "R", 9: "3", 0: "5"}
    assert chord_roles("Dm") == {2: "R", 5: "3", 9: "5"}
    assert chord_roles("G7") == {7: "R", 11: "3", 2: "5", 5: "7"}
    assert chord_roles("Csus4") == {0: "R", 5: "4", 7: "5"}


def test_chord_roles_cover_exactly_the_chords_tones():
    for name in ("F", "Dm", "Bb", "Em7", "Cmaj7", "Bdim", "Gaug", "C6"):
        assert set(chord_roles(name)) == set(chord_semitones(name))


# --- the blocks: written pitch, transposition -------------------

def test_the_flute_reads_what_sounds():
    blocks = wind_blocks(_jacques(), FLUTE)

    assert [b["note"] for b in blocks[:4]] == ["F4", "G4", "A4", "F4"]
    assert blocks[0]["concert"] is None
    assert blocks[0]["written_pitch"] == 53 == blocks[0]["pitch"]


def test_the_alto_sax_reads_a_major_sixth_above_in_the_written_key():
    blocks = wind_blocks(_jacques(), SAX)

    # F G A F sounding in F major read D E F# D in D major; the
    # key is spelled with sharps, so A reads F#, not Gb.
    assert [b["note"] for b in blocks[:4]] == ["D5", "E5", "F#5", "D5"]
    assert [b["concert"] for b in blocks[:4]] == ["F4", "G4", "A4", "F4"]
    assert [b["written_pitch"] for b in blocks[:4]] == [62, 64, 66, 62]
    assert [b["pitch"] for b in blocks[:4]] == [53, 55, 57, 53]


def test_a_flat_note_in_a_flat_key_is_spelled_by_the_written_key():
    # Sounding Bb4 (58) is written G5 (67), and G5 has no accidental.
    blocks = wind_blocks(_piece("Bb4"), SAX)

    assert blocks[0]["note"] == "G5"
    assert blocks[0]["concert"] == "Bb4"


def test_start_and_length_and_lyrics_come_from_the_piece():
    blocks = wind_blocks(_jacques(), FLUTE)

    assert [b["start"] for b in blocks[:4]] == [0, 1, 2, 3]
    assert blocks[10]["length"] == 2 and blocks[10]["lyric"] == "John?"
    assert blocks[0]["lyric"] == "Are"


def test_rests_leave_a_gap_and_are_not_blocks():
    piece = Piece.read("C5 R D5", "1 2 1", "", "C", "")
    blocks = wind_blocks(piece, FLUTE)

    assert [b["start"] for b in blocks] == [0, 3]


# --- out of range moves an octave, flagged ----------------------

def test_flute_range_is_c4_to_c7_and_sax_b_flat_3_to_f_sharp_6():
    # C4 = 48, so C7 = 48 + 36 = 84; B-flat 3 = 48 - 2 = 46 and
    # F-sharp 6 = 48 + 24 + 6 = 78. (Stage 1 had the flute at 96,
    # caught when the first chart was transcribed.)
    assert WRITTEN_RANGE[FLUTE] == (48, 84)
    assert WRITTEN_RANGE[SAX] == (46, 78)


def test_a_note_above_the_flute_comes_down_an_octave():
    # D7 (86) is above C7 (84): played D6 (74).
    block = wind_blocks(_piece("D7"), FLUTE)[0]

    assert block["shift"] == -1 and block["written_pitch"] == 74


def test_a_note_below_the_flute_goes_up_an_octave_and_is_flagged():
    # A3 (45) is below the flute's low C4 (48): played A4 (57).
    block = wind_blocks(_piece("A3"), FLUTE)[0]

    assert block["shift"] == 1 and block["written_pitch"] == 57
    assert block["pitch"] == 57 and block["in_range"]


def test_a_sax_note_above_the_range_goes_down_an_octave():
    # Sounding Bb5 (70) would be written 79, above F#6 (78): it is
    # played an octave down, sounding Bb4 (58), written G5 (67).
    block = wind_blocks(_piece("Bb5"), SAX)[0]

    assert block["shift"] == -1
    assert block["written_pitch"] == 67 and block["pitch"] == 58


def test_a_sax_note_below_the_range_goes_up_an_octave():
    # Sounding C3 (36) would be written 45, below B-flat 3 (46).
    block = wind_blocks(_piece("C3"), SAX)[0]

    assert block["shift"] == 1
    assert block["written_pitch"] == 57 and block["pitch"] == 48


def test_a_note_in_range_is_not_moved():
    assert all(b["shift"] == 0 for b in wind_blocks(_jacques(), SAX))


# --- chord role of each note ------------------------------------

def test_notes_take_their_role_in_the_chord_they_begin_under():
    blocks = wind_blocks(_jacques(), FLUTE)
    roles = {b["note"]: b["role"] for b in blocks[:4]}

    # Over F: F is the root, A the third, C the fifth; G passes.
    assert roles == {"F4": "R", "G4": None, "A4": "3"}
    assert [b["role"] for b in blocks[8:11]] == ["3", None, "5"]


def test_roles_follow_the_sounding_pitch_not_the_written_one():
    # The sax's written F# is the chord's third (A): the role is
    # worked out in concert pitch, so it matches the chord card.
    blocks = wind_blocks(_jacques(), SAX)

    assert blocks[2]["note"] == "F#5" and blocks[2]["role"] == "3"


def test_no_chart_means_no_roles_and_no_chord():
    blocks = wind_blocks(_jacques(chart=""), FLUTE)

    assert all(b["role"] is None and b["chord"] is None for b in blocks)


def test_a_note_held_across_a_change_keeps_the_chord_it_began_under():
    # D5 lasts three beats; the chord changes from F to Dm at beat 2.
    # It began under F, where D is not a chord tone.
    piece = Piece.read("D5 D5", "3 1", "", "F", "| F . Dm . |")
    held, after = wind_blocks(piece, FLUTE)

    assert held["chord"] == "F" and held["role"] is None
    assert after["chord"] == "Dm" and after["role"] == "R"


def test_roles_change_with_the_chord():
    piece = Piece.read("D5 D5", "2 2", "", "F", "| F . Dm . |")
    first, second = wind_blocks(piece, FLUTE)

    # D is not in F, but is the root of Dm.
    assert first["role"] is None and second["role"] == "R"
    assert (first["chord"], second["chord"]) == ("F", "Dm")


# --- fingerings come from the table, never guessed --------------

def test_a_note_with_no_fingering_has_keys_none():
    blocks = wind_blocks(_jacques(), FLUTE, _table({53: ["L1"]}))

    assert blocks[0]["keys"] == ["L1"]
    assert blocks[1]["keys"] is None


def test_the_shipped_table_is_empty_until_a_chart_arrives_and_then_sourced():
    for name in (FLUTE, SAX):
        if wind_fingerings.FINGERINGS[name]:
            assert wind_fingerings.SOURCE[name], (
                f"{name} fingerings need the chart they came from "
                "named in SOURCE"
            )


def test_the_table_is_asked_in_written_pitch():
    # The sax table is keyed by what the player reads: sounding F4
    # is written D5 (62).
    blocks = wind_blocks(_jacques(), SAX, _sax_table({62: ["O", "L1"]}))

    assert blocks[0]["keys"] == ["O", "L1"]


def test_keys_changed_counts_keys_that_differ():
    assert keys_changed(["L1", "L2"], ["L1", "R1"]) == 2
    assert keys_changed(["L1"], ["L1"]) == 0
    assert keys_changed([], ["L1", "L2", "L3"]) == 3
    assert keys_changed(None, ["L1"]) is None
    assert keys_changed(["L1"], None) is None


# --- the rows ---------------------------------------------------

def test_there_is_a_row_for_every_phrase():
    rows = wind_rows(_jacques(), FLUTE)

    assert [r["start"] for r in rows] == [0, 4, 8, 12, 16, 20, 24, 28]
    assert [len(r["blocks"]) for r in rows] == [4, 4, 3, 3, 6, 6, 3, 3]
    assert all(r["chord"] == "F" for r in rows)


def test_the_flute_rows_list_the_chord_tones_the_phrase_leaves_out():
    rows = wind_rows(_jacques(), FLUTE)

    def missing(row):
        return [
            (g["chord"], [(t["role"], t["note"]) for t in g["tones"]])
            for g in row["missing"]
        ]

    # Phrase 1 (F G A F) has no C: the fifth, shown at the C nearest
    # its notes (mean pitch 54.5; C5 at 60 is nearer than C4 at 48).
    assert missing(rows[0]) == [("F", [("5", "C5")])]
    # Phrase 3 (A Bb C) has no F: the root, F4 (53) nearest 58.3.
    assert missing(rows[2]) == [("F", [("R", "F4")])]
    # Phrase 5 plays F, A and C: nothing left out.
    assert missing(rows[4]) == []
    # Phrase 7 (F C F) has no A: the third, A4 (57) nearest 51.3.
    assert missing(rows[6]) == [("F", [("3", "A4")])]


def test_the_sax_rows_show_the_missing_tones_as_written_notes():
    rows = wind_rows(_jacques(), SAX)

    assert rows[0]["missing"][0]["tones"][0]["note"] == "A5"   # C5
    assert rows[2]["missing"][0]["tones"][0]["note"] == "D5"   # F4
    assert rows[6]["missing"][0]["tones"][0]["note"] == "F#5"  # A4
    # Roles stay the chord's, whichever instrument.
    assert rows[0]["missing"][0]["tones"][0]["role"] == "5"


def test_a_row_with_two_chords_reports_each_chord():
    piece = Piece.read(
        "F4 F4 D5 D5", "2 2 2 2", "a b\nc d", "F", "| F . . . | Dm . . . |"
    )
    rows = wind_rows(piece, FLUTE)

    # Row 1 (F F) under F: A and C are out. Row 2 (D D) under Dm:
    # F and A are out.
    assert [t["role"] for t in rows[0]["missing"][0]["tones"]] == ["3", "5"]
    assert rows[1]["missing"][0]["chord"] == "Dm"
    assert [t["role"] for t in rows[1]["missing"][0]["tones"]] == ["3", "5"]


def test_no_chart_means_nothing_to_leave_out():
    rows = wind_rows(_jacques(chart=""), FLUTE)

    assert all(r["missing"] == [] and r["chord"] is None for r in rows)


def test_repeated_phrases_fold_into_one_row_marked_twice():
    folded = fold_repeats(wind_rows(_jacques(), FLUTE))

    assert [r["start"] for r in folded] == [0, 8, 16, 24]
    assert [r["times"] for r in folded] == [2, 2, 2, 2]
    assert [r["last"] for r in folded] == [8, 16, 24, 32]


def test_a_phrase_under_a_different_chord_is_not_folded():
    piece = Piece.read(
        "F4 A4 F4 A4", "2 2 2 2", "a b\nc d", "F", "| F . . . | F . . . |"
    )
    same = fold_repeats(wind_rows(piece, FLUTE))
    other = fold_repeats(wind_rows(
        Piece.read("F4 A4 F4 A4", "2 2 2 2", "a b\nc d", "F", "| F . . . | Dm . . . |"),
        FLUTE,
    ))

    assert len(same) == 1 and same[0]["times"] == 2
    assert len(other) == 2


def test_rows_that_differ_in_a_note_are_not_folded():
    piece = Piece.read(
        "F4 A4 F4 G4", "2 2 2 2", "a b\nc d", "F", "| F . . . | F . . . |"
    )

    assert len(fold_repeats(wind_rows(piece, FLUTE))) == 2


# --- the page ---------------------------------------------------

def _count(html_text, needle):
    return html_text.count(needle)


def test_the_page_draws_a_ring_on_every_chord_tone_only():
    page = wind_view(_jacques(), FLUTE, fold=True)

    # Folded rows: F G A F | A Bb C | C D C Bb A F | F C F.
    # Chord tones: 3 + 2 + 4 + 3.
    assert _count(page, "wind-ring wind-tone") == 12
    assert _count(page, 'class="wind-ring"') == 4  # G, Bb, D, Bb


def test_not_folding_draws_every_phrase():
    page = wind_view(_jacques(), FLUTE, fold=False)

    assert _count(page, 'class="wind-row"') == 8
    assert "×2" not in page


def test_folding_marks_the_row_twice_and_names_both_phrases():
    page = wind_view(_jacques(), FLUTE, fold=True)

    assert _count(page, 'class="wind-row"') == 4
    assert _count(page, "×2") == 4
    assert "Phrases 1–2" in page and "Phrases 7–8" in page


def test_only_chord_tones_get_the_pink_ring():
    from instrument_diagrams import CHORD_TONE_COLOUR

    page = wind_view(_jacques(), FLUTE, fold=True)
    rings = re.findall(
        r'class="wind-ring( wind-tone)?" style="[^"]*?border:2px solid '
        r"(#[0-9a-fA-F]{6})",
        page,
    )

    assert len(rings) == 16
    for tone, colour in rings:
        assert (colour == CHORD_TONE_COLOUR) == bool(tone)
        assert tone or colour == "#ffffff"


def test_the_chord_name_opens_each_row_and_the_missing_column_follows():
    page = wind_view(_jacques(), FLUTE)

    assert _count(page, 'class="wind-chord"') == 4
    assert _count(page, "Not in this phrase") == 3  # phrase 5 leaves none


def test_melody_only_draws_no_rings_no_chord_and_no_missing_column():
    page = wind_view(_jacques(), FLUTE, show=["Melody"])

    assert "wind-tone" not in page
    assert "wind-chord" not in page
    assert "Not in this phrase" not in page
    assert "wind-cell" in page


def test_nothing_ticked_still_shows_the_melody():
    page = wind_view(_jacques(), FLUTE, show=[])

    assert "wind-cell" in page


def test_chords_only_still_shows_the_notes():
    # The chord layer annotates the notes; it never hides them.
    page = wind_view(_jacques(), FLUTE, show=["Chords"])

    assert "wind-cell" in page and "wind-chord" in page


def test_a_note_without_a_fingering_draws_the_grey_chart_and_says_so():
    page = wind_view(_jacques(), FLUTE, table=_table({53: ["L1"]}))

    assert "wind-unknown" in page
    assert "no fingering yet" in page
    # The one known note is drawn.
    assert "wind-down" in page


def test_the_keys_pressed_are_filled():
    table = _table({53: ["L1", "L2"]})
    page = wind_view(_piece("F4", chart=""), FLUTE, table=table)

    assert _count(page, "wind-key wind-down") == 2
    others = len(wind_fingerings.KEY_LAYOUT[FLUTE]) - 2
    assert _count(page, 'class="wind-key"') == others


def test_every_key_ring_is_drawn_for_a_known_note():
    page = wind_view(
        _piece("F4", chart=""), SAX, table=_sax_table({62: ["O"]})
    )
    drawn = re.findall(r'data-key="(\w+)"', page)

    assert drawn == [k["id"] for k in wind_fingerings.KEY_LAYOUT[SAX]]


def test_a_change_of_four_keys_or_more_gets_a_pill_with_the_count():
    piece = _piece("F4 G4", chart="")

    # L1 out, L2 L3 R1 in: four keys differ.
    four = _table({53: ["L1"], 55: ["L2", "L3", "R1"]})
    assert "4 keys" in wind_view(piece, FLUTE, table=four)

    # Six differ: the pill says six.
    six = _table({53: ["L1", "L2"], 55: ["L3", "R1", "R2", "R3"]})
    assert "6 keys" in wind_view(piece, FLUTE, table=six)


def test_a_change_of_three_keys_or_fewer_gets_no_pill():
    piece = _piece("F4 G4", chart="")
    three = _table({53: ["L1"], 55: ["L2", "L3"]})

    assert "wind-change" not in wind_view(piece, FLUTE, table=three)


def test_an_unknown_fingering_gets_no_pill():
    piece = _piece("F4 G4", chart="")
    one_known = _table({53: ["L1", "L2", "L3", "R1", "R2"]})

    assert "wind-change" not in wind_view(piece, FLUTE, table=one_known)


def test_a_moved_note_gets_the_amber_pill():
    page = wind_view(_piece("A3"), FLUTE)

    assert "wind-8va" in page and "8va" in page
    assert "moved by an octave" in page


def test_the_sax_shows_the_concert_note_and_says_so():
    page = wind_view(_jacques(), SAX)

    assert "wind-concert" in page and "F4 concert" in page
    assert "written pitch" in page


def test_the_flute_shows_no_concert_line():
    assert "wind-concert" not in wind_view(_jacques(), FLUTE)


def test_each_chart_has_a_spoken_label():
    page = wind_view(_jacques(), FLUTE, table=_table({53: ["L1", "L2"]}))

    assert (
        'aria-label="Flute F4: left index, left middle, chord tone R"'
        in page
    )
    assert 'aria-label="Flute G4: no fingering yet, passing note"' in page


def test_lyrics_are_escaped():
    piece = Piece.read("F4", "1", "a<b>", "F", "")

    assert "a&lt;b&gt;" in wind_view(piece, FLUTE)


def test_no_notes_says_so():
    piece = Piece.read("R", "1", "", "F", "")

    assert "No notes to show yet" in wind_view(piece, FLUTE)


# --- how the section uses it ------------------------------------

def test_the_winds_are_in_the_melody_section_after_the_others():
    assert list(supported_families())[-2:] == [FLUTE, SAX]


def test_the_melody_view_hands_the_winds_to_their_own_view():
    piece = _jacques()

    assert "wind-rows" in melody_view(piece, FLUTE)
    assert "wind-rows" in melody_view(piece, SAX)
    assert melody_view(piece, FLUTE, fold=False).count("wind-row\"") == 8


def test_the_page_has_a_view_for_each_wind_tab():
    page = melody_page(
        PITCHES, LENGTHS, WORDS, "F", CHART, "", [FLUTE, SAX]
    )

    assert len(page["views"]) == 2
    assert all("wind-rows" in view for view in page["views"])


def test_the_wind_view_never_touches_the_boxes():
    import ast

    with open("wind_melody.py") as source:
        tree = ast.parse(source.read())

    imported = {
        node.module for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    } | {
        alias.name for node in ast.walk(tree)
        if isinstance(node, ast.Import) for alias in node.names
    }

    assert "gradio" not in imported and "main" not in imported
