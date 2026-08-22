"""
An imported score can land as several parts at once.

Splitting a staff's voices apart (test_musicxml_unfold.py's
bridge test) only ever gave a choice between them. These pin
the other half: a combined entry in parts_in() that lands the
split voices side by side as one divided song, in the same
"=== name ===" shape the hand-typed partner songs and rounds
are written in - and a second combined entry that does the
same for every sung staff of a score written on separate
staves.

Every number asserted here was measured on the file first.
The Mulan fixture is the only two-voice-in-one-staff file in
the repo; these tests skip rather than fail if it is removed.
"""

import os
from fractions import Fraction

import pytest

FIXTURES = os.path.join(
    os.path.dirname(__file__), "fixtures", "musicxml"
)

MULAN = "mulan-ill-make-a-man-out-of-you.mxl"
CAROL = "o-holy-night-satb.mxl"


def fixture(name):
    return os.path.join(FIXTURES, name)


def needs(name):
    if not os.path.exists(fixture(name)):
        pytest.skip(f"{name} not present")


def imported(name, label, verse=1):
    from musicxml_import import import_musicxml
    return import_musicxml(fixture(name), label, verse)


def tunes_of(result):
    from piece import Piece
    pitches, durations, lyrics, bpm, feedback, chart, poly, key = result
    return Piece.read_parts(pitches, durations, lyrics, key, chart, bpm)


def first_note_beat(piece):
    beat = 0.0
    for pitch, length in zip(piece.pitches, piece.durations):
        if pitch != "R":
            return beat
        beat += float(length)
    return None


def section(text, name):
    """One tune's box text, by divider name."""
    marker = f"=== {name} ===\n"
    assert marker in text
    body = text.split(marker, 1)[1]
    return body.split("\n===", 1)[0].strip()


# --- what parts_in offers -------------------------------------


def test_a_staffs_voices_are_offered_together_after_each_alone():
    """
    The individual voices keep their labels and indexes
    exactly as before; the combined entry comes after them,
    with the counts summed. Nothing a saved label referred to
    has moved.
    """

    needs(MULAN)

    from musicxml_import import parts_in

    labels = parts_in(fixture(MULAN))

    assert labels[0] == "0  Soprano, 343 notes, 281 with words"
    assert labels[1] == "1  Soprano, second voice, 22 notes, 16 with words"
    assert labels[2] == "2  Soprano, both voices, 365 notes, 297 with words"

    # One staff carries words, so there is no "all sung
    # parts" entry on top - that would only duplicate the
    # one above.
    assert not any("All sung parts" in label for label in labels)


def test_every_sung_staff_is_offered_together_last():
    """
    O Holy Night: four staves carry words, one (the piano
    accompaniment) does not. The combined entry takes the
    four and leaves the piano out, and comes last so the
    existing indexes stay put.
    """

    from musicxml_import import parts_in

    labels = parts_in(fixture(CAROL))

    assert labels[-1] == "5  All sung parts, 329 notes, 301 with words"
    assert labels[:5] == [
        "0  Piano, Piano, 458 notes",
        "1  Pan Flute, Soprano Solo, 137 notes, 125 with words",
        "2  Piano, SOPRANO, 67 notes, 60 with words",
        "3  Piano, ALTO, 61 notes, 58 with words",
        "4  Piano, TENOR, 64 notes, 58 with words",
    ]


# --- voices of one staff, landed together ---------------------


def test_both_voices_land_as_one_divided_song():
    """
    The combined import splits, through Piece.read_parts,
    into exactly two tunes of the same length, named the way
    the hand-typed round names its voices.
    """

    needs(MULAN)

    from musicxml_import import parts_in

    labels = parts_in(fixture(MULAN))
    tunes = tunes_of(imported(MULAN, labels[2]))

    assert [name for name, piece in tunes] == ["Voice 1", "Voice 2"]
    assert all(sum(piece.durations) == 348 for name, piece in tunes)


def test_the_main_voice_reads_identically_alone_or_together():
    """
    Landing a voice beside another changes nothing about how
    that voice itself is read: its box text is the same,
    token for token, as importing it on its own.
    """

    needs(MULAN)

    from musicxml_import import parts_in

    labels = parts_in(fixture(MULAN))

    alone = imported(MULAN, labels[0])
    together = imported(MULAN, labels[2])

    for box in range(3):
        assert section(together[box], "Voice 1") == alone[box].strip()


def test_a_voice_that_enters_late_is_placed_where_the_score_puts_it():
    """
    music21's voice split hands back only the bars a voice
    sounds in, with the silences between them missing rather
    than written. Imported alone that does not matter; landed
    beside the main line it would start the chorus at bar 1.
    The chorus's first note is at beat 174 in the unfolded
    score, and that is where it lands.
    """

    needs(MULAN)

    from musicxml_import import parts_in

    labels = parts_in(fixture(MULAN))
    tunes = dict(tunes_of(imported(MULAN, labels[2])))

    assert first_note_beat(tunes["Voice 2"]) == 174.0
    assert first_note_beat(tunes["Voice 1"]) == 8.5


def test_each_voice_takes_the_verse_its_words_are_in():
    """
    The chorus's "Be a man" sits under verse 2 in the file,
    with a single stray syllable under verse 1. Asked for
    verse 1, the combined import still gives the chorus its
    real words, and the feedback says so - an inference,
    written where it can be seen.
    """

    needs(MULAN)

    from musicxml_import import parts_in

    labels = parts_in(fixture(MULAN))
    result = imported(MULAN, labels[2], verse=1)
    tunes = dict(tunes_of(result))

    words = [
        token for token in tunes["Voice 2"].lyrics.split()
        if token != "_"
    ]

    assert words[:3] == ["Be", "a", "man"]
    assert "Voice 2 (verse 2)" in result[4]
    assert "Voice 1" not in result[4].split("Words for", 1)[1].split(".")[0]


def test_key_chart_and_tempo_are_shared_and_unchanged():
    """
    One chart, one key timeline, one tempo across the tunes -
    the same as the hand-typed examples, and the same values
    the main voice gets on its own.
    """

    needs(MULAN)

    from musicxml_import import parts_in

    labels = parts_in(fixture(MULAN))

    alone = imported(MULAN, labels[0])
    together = imported(MULAN, labels[2])

    assert together[3] == alone[3]
    assert together[5] == alone[5]
    assert together[7] == alone[7]


def test_verses_in_answers_for_a_combined_entry():
    needs(MULAN)

    from musicxml_import import parts_in, verses_in

    labels = parts_in(fixture(MULAN))

    assert verses_in(fixture(MULAN), labels[2]) == [1, 2, 3]


# --- sung staves, landed together -----------------------------


def test_all_sung_parts_land_as_four_tunes_each_as_alone():
    """
    Separate staves already sit at full length from beat 0,
    so each tune of the combined import carries exactly the
    words and notes its own solo import does.
    """

    from musicxml_import import parts_in

    labels = parts_in(fixture(CAROL))
    together = imported(CAROL, labels[-1])
    tunes = tunes_of(together)

    assert [name for name, piece in tunes] == [
        "Pan Flute, Soprano Solo",
        "Piano, SOPRANO",
        "Piano, ALTO",
        "Piano, TENOR",
    ]

    for (name, piece), label in zip(tunes, labels[1:5]):
        alone = imported(CAROL, label)
        assert sum(piece.durations) == 156
        assert " ".join(piece.lyrics.split()) == " ".join(alone[2].split())
        assert section(together[0], name) == alone[0].strip()

    assert together[5] == imported(CAROL, labels[1])[5]


def test_the_feedback_counts_every_tune():
    from musicxml_import import parts_in

    labels = parts_in(fixture(CAROL))
    feedback = imported(CAROL, labels[-1])[4]

    assert feedback.startswith("Read 4 parts together: 129 from")


# --- a latent bug this work uncovered -------------------------


def test_a_long_rest_with_a_part_bar_left_over_stays_writable():
    """
    _rests_as_bars took the metre as a float and subtracted
    it from a Fraction, so any remainder came back as a float
    the duration box cannot write. No fixture had a rest
    longer than a bar with a part-bar left over until a voice
    first entered partway through bar 12 after 46.5 beats of
    silence.
    """

    from musicxml_import import _rests_as_bars

    pieces = _rests_as_bars(Fraction(93, 2), 4.0)

    assert all(isinstance(piece, Fraction) for piece in pieces)
    assert sum(pieces) == Fraction(93, 2)
    assert pieces[-1] == Fraction(5, 2)


# --- what lands before anyone chooses --------------------------


def test_a_score_lands_with_every_sung_staff_by_default():
    """
    The built-in partner songs and rounds open with all their
    tunes loaded; an uploaded score should too. O Holy Night
    has four sung staves, so the most inclusive entry wins.
    """

    from musicxml_import import default_part_in

    needs(CAROL)

    assert default_part_in(fixture(CAROL)).startswith(
        "5  All sung parts"
    )


def test_a_staffs_voices_land_together_when_that_is_all_there_is():
    """
    Mulan has one sung staff carrying two voices and no
    second sung staff, so "both voices" is the most it
    can offer, and that is what lands.
    """

    from musicxml_import import default_part_in

    needs(MULAN)

    assert default_part_in(fixture(MULAN)).startswith(
        "2  Soprano, both voices"
    )


def test_a_one_voice_score_still_lands_on_its_first_part():
    """
    Nothing to combine: the first part listed, exactly as
    before this existed.
    """

    from musicxml_import import default_part_in, parts_in

    path = fixture("weber_concertino_clarinet.mxl")

    assert default_part_in(path) == parts_in(path)[0]


def test_the_default_is_always_one_of_the_parts_offered():
    """
    default_part_in and parts_in read the same description,
    so the dropdown's value is always one of its choices.
    """

    from musicxml_import import default_part_in, parts_in

    for name in (MULAN, CAROL, "weber_concertino_clarinet.mxl"):
        if not os.path.exists(fixture(name)):
            continue
        assert default_part_in(fixture(name)) in parts_in(fixture(name))


def test_the_app_asks_for_the_default_not_the_first():
    """
    The upload handler in main.py lands default_music_part,
    not list_music_parts()[0]. A score dispatches to
    default_part_in; a MIDI keeps its likeliest tune first.
    """

    from music import default_music_part, list_music_parts

    needs(CAROL)

    assert default_music_part(fixture(CAROL)) == (
        list_music_parts(fixture(CAROL))[-1]
    )

    midi = os.path.join(
        os.path.dirname(__file__), "fixtures", "midi",
        "o-holy-night-satb.mid"
    )
    if os.path.exists(midi):
        assert default_music_part(midi) == list_music_parts(midi)[0]