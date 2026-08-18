"""
A piece of music as one object.

The point of it is slicing. Everything the app does to a
stretch of music - play it, sing it, judge it, draw it -
needs the notes, the words under those notes and the chords
over them, cut to the same place. Doing that conversion in
several functions is how the same bug keeps arriving, so it
is done here and tested here.
"""

import pytest

from piece import Piece
from music import MusicInputError


TWINKLE = Piece.read(
    "C4 C4 G4 G4 A4 A4 G4 R",
    "1 1 1 1 1 1 3/2 1/2",
    "Twin- kle twin- kle lit- tle star",
    "C",
    "| C . . . | F . C . |"
)


def test_a_piece_knows_how_long_it_is():
    assert len(TWINKLE) == 8
    assert TWINKLE.beats() == 8
    assert TWINKLE.sung() == 7


def test_length_in_seconds_needs_a_tempo():
    """
    Rhythm is kept in beats, so nothing about the music
    depends on how fast it is sung.
    """

    assert TWINKLE.seconds(120) == 4.0
    assert TWINKLE.seconds(60) == 8.0


def test_slicing_takes_the_words_with_it():
    opening = TWINKLE.slice(0, 3)

    assert opening.pitches == ["C4", "C4", "G4", "G4"]
    assert opening.lyrics == "Twin- kle twin- kle"


def test_slicing_takes_the_chords_with_it():
    """
    Chords are cut in beats while notes are counted one by
    one, and getting that conversion wrong is what this
    object exists to prevent.
    """

    assert TWINKLE.slice(0, 3).chart == "| C . . . |"
    assert TWINKLE.slice(4, 7).chart == "| F . C . |"


def test_a_slice_beginning_mid_chord_still_names_it():
    """
    A phrase starting halfway through a bar of D minor is
    still in D minor, and a chart may not open with a dot.
    """

    piece = Piece.read(
        "D4 E4 F4 G4 A4 B4 C5 D5",
        "1 1 1 1 1 1 1 1",
        "",
        "C",
        "| Dm . . . | G . . . |"
    )

    middle = piece.slice(2, 5)

    assert middle.chart.startswith("| Dm")


def test_a_rest_between_lines_stays_with_the_line_before():
    assert TWINKLE.slice(4, 7).pitches[-1] == "R"

    # And the words are only those of the sung notes.
    assert TWINKLE.slice(4, 7).lyrics == "lit- tle star"


def test_a_piece_without_chords_slices_without_them():
    plain = Piece.read("C4 E4 G4", "1 1 1")

    assert plain.slice(0, 1).chart == ""


def test_phrases_come_from_the_lines_of_the_lyrics():
    piece = Piece.read(
        "C4 C4 G4 G4 A4 A4 G4 R",
        "1 1 1 1 1 1 3/2 1/2",
        "Twin- kle twin- kle\nlit- tle star",
        "C",
        "| C . . . | F . C . |"
    )

    assert len(piece.phrases()) == 2

    first = piece.phrase(0)

    assert first.lyrics == "Twin- kle twin- kle"
    assert first.chart == "| C . . . |"


def test_asking_for_a_phrase_that_is_not_there():
    with pytest.raises(MusicInputError, match="no phrase"):
        TWINKLE.phrase(9)


def test_the_song_tempo_is_not_the_playing_tempo():
    """
    The tempo of the song is part of the song, as a
    marking on a score is. How fast you are singing it
    today is not: a piece slowed down to learn a harmony
    line is the same piece.
    """

    piece = Piece.read(
        "C4 E4", "1 1", "", "C", "", tempo=192
    )

    assert piece.tempo == 192

    # And it travels with a slice, since it belongs to the
    # music rather than to the moment.
    assert piece.slice(0, 0).tempo == 192

    # But it decides nothing about length in beats.
    assert piece.beats() == 2


def test_reading_reports_the_same_mistakes_as_before():
    with pytest.raises(MusicInputError, match="syllable"):
        Piece.read("C4 E4", "1 1", "only-one-word")

    with pytest.raises(MusicInputError, match="same length"):
        Piece.read("C4 E4", "1 1", "", "C", "| C . . . |")


def test_line_breaks_survive_being_read():
    """
    The line breaks in the lyrics are the phrasing, so
    reading a piece must not flatten them.
    """

    piece = Piece.read(
        "C4 E4 G4 C5",
        "1 1 1 1",
        "one two\nthree four"
    )

    assert "\n" in piece.lyrics
    assert len(piece.phrases()) == 2


# Half-beat chords: a syncopated chart entry (A>B, or >B
# carrying the first half) has to survive being sliced the
# same way any other chord does - chart_between reuses
# write_chart to reconstruct a windowed chart rather than
# duplicating its token-building logic, so this is really a
# test that the two stay in agreement.

SYNCOPATED = Piece.read(
    "C4 C4 C4 C4 A4 A4 A4 A4",
    "1 1 1 1 1 1 1 1",
    "",
    "C",
    "| C . . D>G | Am . . . |"
)


def test_a_split_chord_survives_a_slice_that_contains_it():
    assert SYNCOPATED.slice(0, 3).chart == "| C . . D>G |"
    assert SYNCOPATED.slice(4, 7).chart == "| Am . . . |"


def test_a_slice_opening_exactly_on_the_split_names_its_own_half():
    """
    A slice that opens right where a beat splits still
    follows the same rule as any other chord: the beat it
    opens on names itself rather than starting with a dot,
    even though that beat is itself half of a split token.
    """

    middle = SYNCOPATED.slice(3, 7)

    assert middle.chart == "| D>G Am . . | . |"


# Multi-key: Piece.key stays a plain string for every
# unmigrated caller (a computed view of the timeline's own
# first entry, never a second fact that construction could
# leave out of step with it - checked directly: nothing
# anywhere mutates piece.key after construction, which is
# what makes the property safe). key_at and slicing are the
# two things that actually need the full timeline.

MODULATING = Piece.read(
    "C4 C4 C4 C4 G4 G4 G4 G4",
    "1 1 1 1 1 1 1 1",
    "",
    "C, G from beat 4"
)


def test_key_stays_a_plain_string_for_backward_compatibility():
    assert MODULATING.key == "C"
    assert isinstance(MODULATING.key, str)


def test_a_single_key_piece_has_a_one_entry_timeline():
    plain = Piece.read("C4 D4", "1 1", "", "C")

    assert plain.key_changes == [(0.0, "C")]
    assert plain.key_at(0) == "C"
    assert plain.key_at(100) == "C"


def test_key_at_resolves_the_real_change():
    assert MODULATING.key_at(0) == "C"
    assert MODULATING.key_at(3) == "C"
    assert MODULATING.key_at(4) == "G"
    assert MODULATING.key_at(7) == "G"


def test_a_slice_entirely_before_the_change_stays_in_the_first_key():
    before = MODULATING.slice(0, 3)

    assert before.key == "C"
    assert before.key_changes == [(0.0, "C")]


def test_a_slice_entirely_after_the_change_opens_in_the_new_key():
    """
    Not just resolvable via key_at - the sliced piece's own
    .key (what every unmigrated consumer still reads) must
    already be the right one, not the whole piece's opening
    key.
    """

    after = MODULATING.slice(4, 7)

    assert after.key == "G"
    assert after.key_changes == [(0.0, "G")]


def test_a_slice_straddling_the_change_carries_both_keys():
    middle = MODULATING.slice(2, 5)

    assert middle.key_changes == [(0.0, "C"), (2.0, "G")]
    assert middle.key == "C"

# Several tunes in one set of boxes, divided by
# "=== name ===" lines - PLAN-multi-part.md, stage 1.

def test_no_divider_is_still_one_part():
    """
    A box with no "=== name ===" line reads as one section,
    name None - every song the app had before this exists.
    """

    from piece import split_parts

    sections = split_parts(
        "C4 C4 G4 G4", "1 1 1 1", "Twin- kle twin- kle"
    )

    assert len(sections) == 1

    name, pitch_text, duration_text, lyric_text = sections[0]

    assert name is None
    assert pitch_text == "C4 C4 G4 G4"
    assert duration_text == "1 1 1 1"
    assert lyric_text == "Twin- kle twin- kle"


def test_read_parts_on_undivided_boxes_matches_read():
    """
    read_parts on a plain, undivided song returns exactly
    what Piece.read already returns for it - the single-
    tune path is not a special case, it is what the general
    mechanism does with one section.
    """

    parts = Piece.read_parts(
        "C4 C4 G4 G4 A4 A4 G4 R",
        "1 1 1 1 1 1 3/2 1/2",
        "Twin- kle twin- kle lit- tle star",
        "C",
        "| C . . . | F . C . |"
    )

    assert len(parts) == 1

    name, piece = parts[0]

    assert name is None
    assert piece.pitches == TWINKLE.pitches
    assert piece.durations == TWINKLE.durations
    assert piece.lyrics == TWINKLE.lyrics
    assert piece.key == TWINKLE.key
    assert piece.chart == TWINKLE.chart


def test_a_partner_song_reads_as_three_named_parts():
    """
    Three tunes, three names, in the order written - the
    shape a partner song (Frere Jacques / Three Blind Mice
    / Hot Cross Buns) needs.
    """

    pitch_text = (
        "=== Frere Jacques ===\n"
        "C4 D4 E4 C4\n"
        "=== Three Blind Mice ===\n"
        "E4 D4 C4 R\n"
        "=== Hot Cross Buns ===\n"
        "E4 D4 C4 R\n"
    )

    duration_text = (
        "=== Frere Jacques ===\n"
        "1 1 1 1\n"
        "=== Three Blind Mice ===\n"
        "1 1 1 1\n"
        "=== Hot Cross Buns ===\n"
        "1 1 1 1\n"
    )

    lyric_text = (
        "=== Frere Jacques ===\n"
        "Fre- re Jac- ques\n"
        "=== Three Blind Mice ===\n"
        "Three blind mice\n"
        "=== Hot Cross Buns ===\n"
        "Hot cross buns\n"
    )

    parts = Piece.read_parts(
        pitch_text, duration_text, lyric_text, "C"
    )

    assert [name for name, _ in parts] == [
        "Frere Jacques", "Three Blind Mice", "Hot Cross Buns"
    ]

    names_to_pieces = dict(parts)

    assert names_to_pieces["Frere Jacques"].pitches == [
        "C4", "D4", "E4", "C4"
    ]
    assert names_to_pieces["Three Blind Mice"].lyrics == \
        "Three blind mice"

    # Key and chart are shared, not repeated per part.
    for _, piece in parts:
        assert piece.key == "C"


def test_a_response_part_keeps_its_leading_rests():
    """
    A duet's answering line is silent until it enters - the
    rests must survive exactly as written, not be trimmed,
    or the part drifts out of time with the others.
    """

    pitch_text = (
        "=== Lead ===\n"
        "C4 D4 E4 F4\n"
        "=== Response ===\n"
        "R R E4 F4\n"
    )

    duration_text = (
        "=== Lead ===\n"
        "1 1 1 1\n"
        "=== Response ===\n"
        "1 1 1 1\n"
    )

    parts = Piece.read_parts(pitch_text, duration_text)

    names_to_pieces = dict(parts)

    assert names_to_pieces["Response"].pitches == [
        "R", "R", "E4", "F4"
    ]
    assert names_to_pieces["Response"].beats() == 4


def test_mismatched_part_names_between_pitch_and_duration_raise():
    pitch_text = "=== A ===\nC4 D4\n=== B ===\nE4 F4\n"
    duration_text = "=== A ===\n1 1\n=== C ===\n1 1\n"

    with pytest.raises(MusicInputError):
        Piece.read_parts(pitch_text, duration_text)


def test_a_missing_divider_in_one_box_raises():
    pitch_text = "=== A ===\nC4 D4\n=== B ===\nE4 F4\n"
    duration_text = "1 1 1 1"

    with pytest.raises(MusicInputError):
        Piece.read_parts(pitch_text, duration_text)


def test_undivided_lyrics_are_fine_with_one_part():
    parts = Piece.read_parts(
        "C4 D4 E4 F4", "1 1 1 1", "Doe a deer a"
    )

    assert parts[0][1].lyrics == "Doe a deer a"


def test_undivided_lyrics_with_several_parts_needs_dividers():
    pitch_text = "=== A ===\nC4 D4\n=== B ===\nE4 F4\n"
    duration_text = "=== A ===\n1 1\n=== B ===\n1 1\n"

    with pytest.raises(MusicInputError):
        Piece.read_parts(pitch_text, duration_text, "some words")


def test_empty_lyrics_with_several_parts_is_fine():
    pitch_text = "=== A ===\nC4 D4\n=== B ===\nE4 F4\n"
    duration_text = "=== A ===\n1 1\n=== B ===\n1 1\n"

    parts = Piece.read_parts(pitch_text, duration_text, "")

    assert dict(parts)["A"].lyrics is None
    assert dict(parts)["B"].lyrics is None


# The partner-song example: the first thing in the app to
# use the divider at all, so it is pinned here as well as
# in the examples' own tests.

def test_the_partner_song_reads_as_two_parts_of_equal_length():
    """
    Both tunes must run the full twenty bars (six-eight, two
    beats a bar, so forty beats), or they drift out of time
    with each other the moment both are heard at once.
    """

    from examples import load_partner_songs

    pitches, durations, lyrics, key, chart, tempo = load_partner_songs()

    parts = Piece.read_parts(
        pitches, durations, lyrics, key, chart, tempo
    )

    assert [name for name, _ in parts] == [
        "Three Blind Mice", "Frere Jacques"
    ]

    for _, piece in parts:
        assert abs(piece.beats() - 40.0) < 1e-9
        assert piece.key == "F"


def test_frere_jacques_enters_under_three_blind_mice_at_bar_five():
    """
    The rests are literal, so a part that enters late still
    enters in the right bar - four bars of rest is eight
    beats, and Frere Jacques' first note falls exactly there.
    Three Blind Mice opens the song.
    """

    from examples import load_partner_songs
    from notes import is_rest

    pitches, durations, lyrics, key, chart, tempo = load_partner_songs()

    parts = dict(Piece.read_parts(
        pitches, durations, lyrics, key, chart, tempo
    ))

    frere = parts["Frere Jacques"]

    first_sung = next(
        start for start, pitch in zip(frere.starts(), frere.pitches)
        if not is_rest(pitch)
    )

    assert abs(first_sung - 8.0) < 1e-9

    assert not is_rest(parts["Three Blind Mice"].pitches[0])


def test_no_partner_song_note_clashes_with_its_chord():
    """
    Checked with chord_semitones rather than by ear or by
    memory: every note landing on a beat is a tone of
    whatever chord the chart has sounding there.
    """

    from examples import load_partner_songs
    from chords import chord_semitones
    from notes import is_rest, note_to_midi

    pitches, durations, lyrics, key, chart, tempo = load_partner_songs()

    parts = Piece.read_parts(
        pitches, durations, lyrics, key, chart, tempo
    )

    for name, piece in parts:

        beat = 0.0

        for pitch, length in zip(piece.pitches, piece.durations):

            # Six-eight beats accumulate thirds; round before
            # asking which chord is sounding, or 15.9999 lands
            # in the previous bar.
            here = round(beat, 6)
            on_beat = abs(here - round(here)) < 1e-6

            if not is_rest(pitch) and on_beat:

                chord = piece.chord_at(round(here))

                assert chord is not None, (
                    f"{name}: no chord under beat {here}"
                )

                assert note_to_midi(pitch) % 12 in chord_semitones(chord), (
                    f"{name}: {pitch} on beat {here} clashes with {chord}"
                )

            beat += length


# Row Row Row Your Boat, as a round - three voices on the
# same tune, offset - the divider mechanism's simplest case.
# Values pinned here are transcribed from a real four-part
# MusicXML source, not guessed.

def test_row_your_boat_is_three_voices_of_the_same_tune():
    from examples import load_row_your_boat

    pitches, durations, lyrics, key, chart, tempo = load_row_your_boat()

    parts = dict(Piece.read_parts(
        pitches, durations, lyrics, key, chart, tempo
    ))

    assert set(parts) == {"Voice 1", "Voice 2", "Voice 3"}

    sung = {
        name: [p for p in piece.pitches if p != "R"]
        for name, piece in parts.items()
    }

    assert abs(parts["Voice 1"].beats() - 36.0) < 1e-9
    assert abs(parts["Voice 2"].beats() - 36.0) < 1e-9
    assert abs(parts["Voice 3"].beats() - 36.0) < 1e-9

    # Same tune - identical once rests are discounted.
    assert sung["Voice 1"] == sung["Voice 2"] == sung["Voice 3"]


def test_each_voice_enters_two_bars_behind_the_last():
    from examples import load_row_your_boat
    from notes import is_rest

    pitches, durations, lyrics, key, chart, tempo = load_row_your_boat()

    parts = dict(Piece.read_parts(
        pitches, durations, lyrics, key, chart, tempo
    ))

    def first_sung(piece):
        return next(
            start for start, pitch in zip(piece.starts(), piece.pitches)
            if not is_rest(pitch)
        )

    assert first_sung(parts["Voice 1"]) == 0.0
    assert abs(first_sung(parts["Voice 2"]) - 6.0) < 1e-9
    assert abs(first_sung(parts["Voice 3"]) - 12.0) < 1e-9