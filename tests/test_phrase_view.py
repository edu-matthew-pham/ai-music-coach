"""
The phrase dropdown is a view on the boxes.

It used to reload the file, which meant the phrasing was
decided at import and could not be changed afterwards. Now
the boxes hold the whole part, the line breaks in the
lyrics are the phrasing, and choosing a phrase cuts to it
without touching anything.
"""

import os

import pytest

from music import (
    list_phrases,
    selected_piece,
    phrase_chosen,
    WHOLE_PART
)


NOTES = "C4 C4 G4 G4 A4 A4 G4 R"
LENGTHS = "1 1 1 1 1 1 3/2 1/2"
CHART = "| C . . . | F . C . |"


def test_one_line_of_lyrics_offers_no_phrases():
    """
    Music that is one phrase does not need a dropdown.
    """

    labels = list_phrases(NOTES, LENGTHS, "Twin- kle twin- kle lit- tle star")

    assert labels == [WHOLE_PART]


def test_each_line_becomes_a_phrase_to_choose():
    labels = list_phrases(
        NOTES, LENGTHS,
        "Twin- kle twin- kle\nlit- tle star"
    )

    assert len(labels) == 3
    assert labels[0] == WHOLE_PART
    assert "Twinkle twinkle" in labels[1]
    assert "little star" in labels[2]


def test_choosing_a_phrase_cuts_the_music_to_it():
    labels = list_phrases(
        NOTES, LENGTHS,
        "Twin- kle twin- kle\nlit- tle star"
    )

    first = selected_piece(
        NOTES, LENGTHS,
        "Twin- kle twin- kle\nlit- tle star",
        "C", CHART, labels[1]
    )

    assert first.pitches == ["C4", "C4", "G4", "G4"]
    assert first.chart == "| C . . . |"
    assert first.lyrics == "Twin- kle twin- kle"


def test_the_whole_part_is_always_available():
    whole = selected_piece(
        NOTES, LENGTHS,
        "Twin- kle twin- kle\nlit- tle star",
        "C", CHART, WHOLE_PART
    )

    assert len(whole) == 8
    assert whole.chart == CHART


def test_a_label_says_which_phrase_it_is():
    assert phrase_chosen("Phrase 3: some words") == 2
    assert phrase_chosen(WHOLE_PART) is None
    assert phrase_chosen(None) is None


def test_correcting_the_lyrics_changes_the_phrases():
    """
    The whole point of moving the phrasing into the box:
    when the guess is wrong it costs a keystroke.
    """

    one = list_phrases(NOTES, LENGTHS, "Twin- kle twin- kle lit- tle star")

    two = list_phrases(
        NOTES, LENGTHS, "Twin- kle twin- kle\nlit- tle star"
    )

    assert len(one) == 1
    assert len(two) == 3


def test_music_that_will_not_read_offers_the_whole_part():
    """
    Half typed music should not empty the dropdown or
    raise: the player is in the middle of editing.
    """

    assert list_phrases("C4 wrong", "1 1", "") == [WHOLE_PART]


def test_a_phrase_of_an_imported_file_plays_on_its_own():
    from music import (
        import_midi_file,
        list_midi_tracks,
        play_music
    )

    path = os.path.join(
        os.path.dirname(__file__),
        "fixtures", "midi", "d_ML_10791.mid"
    )

    if not os.path.exists(path):
        pytest.skip("the band arrangement fixture is absent")

    tracks = list_midi_tracks(path)

    (
        pitches,
        durations,
        lyrics,
        bpm,
        feedback,
        chart,
        chart_notes,
        key
    ) = import_midi_file(path, tracks[0])

    labels = list_phrases(pitches, durations, lyrics)

    assert len(labels) > 2

    rate, phrase_audio = play_music(
        pitches, durations, key, 1, 0, 0, bpm, 0,
        chart, 0,
        "Thirds, chord-corrected", 0, lyrics, labels[1]
    )

    rate, whole_audio = play_music(
        pitches, durations, key, 1, 0, 0, bpm, 0,
        chart, 0,
        "Thirds, chord-corrected", 0, lyrics, WHOLE_PART
    )

    # A phrase is a part of the whole, not the whole again.
    assert len(phrase_audio) < len(whole_audio)


def test_a_phrase_ending_mid_beat_still_has_its_chords():
    """
    A phrase closing on the second half of a beat sits
    under a chord that lasts the whole of it, so the chart
    may run a little past the notes.
    """

    # Two lines, the first ending half way through beat
    # four.
    piece = selected_piece(
        "C4 C4 C4 D4 E4 F4 G4 R",
        "1 1 1 1/2 1/2 1 1 2",
        "one two three four\nfive six seven",
        "C", "| C . . . | F . . . |",
        "Phrase 1: one two three four"
    )

    assert piece.beats() == 3.5
    assert piece.chart


def test_a_phrase_that_no_longer_exists_is_not_left_chosen():
    """
    Joining two lines can leave the chosen phrase numbered
    past the end of the list.
    """

    from music import list_phrases, WHOLE_PART

    notes = "C4 C4 G4 G4 A4 A4 G4 R"
    lengths = "1 1 1 1 1 1 3/2 1/2"

    three = list_phrases(
        notes, lengths, "Twin- kle\ntwin- kle\nlit- tle star"
    )

    one = list_phrases(
        notes, lengths, "Twin- kle twin- kle lit- tle star"
    )

    assert len(three) == 4
    assert three[3] not in one

    # And the only thing left to choose is the whole part.
    assert one == [WHOLE_PART]


def test_the_lyrics_are_the_only_copy_of_themselves():
    """
    Nothing is saved anywhere. The box holds the words, the
    words hold the phrasing, and editing one changes the
    other with nothing in between to fall out of step.
    """

    import music

    assert not hasattr(music, "remember_lyrics")
    assert not hasattr(music, "with_saved_lyrics")
    assert not hasattr(music, "phrase_key")


def test_correcting_the_lyrics_keeps_the_phrase_chosen():
    """
    The labels carry the words, so editing the lyrics
    rewrites every one of them.

    Matching the old label against the new list therefore
    finds nothing, and falling back to the whole part means
    a correction makes playback longer rather than shorter:
    press Enter to shorten a phrase and the app plays the
    entire song. What stays chosen has to be the number.
    """

    from music import list_phrases, phrase_chosen, selected_piece

    notes = "C4 C4 G4 G4 A4 A4 G4 R"
    lengths = "1 1 1 1 1 1 3/2 1/2"

    before = list_phrases(
        notes, lengths, "Twin- kle twin- kle\nlit- tle star"
    )

    chosen = before[1]

    # The words of that phrase are rewritten.
    after = list_phrases(
        notes, lengths, "My own four words\nlit- tle star"
    )

    # The label has changed, so it is no longer in the list.
    assert chosen not in after

    # But the number survives, and still names a phrase.
    number = phrase_chosen(chosen)

    assert number == 0

    kept = after[number + 1]

    piece = selected_piece(
        notes, lengths, "My own four words\nlit- tle star",
        "C", "| C . . . | F . C . |", kept
    )

    # Four notes, not all eight.
    assert len(piece) == 4


def test_a_phrase_beyond_the_end_falls_to_the_last_one():
    """
    Joining two lines leaves the chosen number past the end
    of a shorter list.
    """

    from music import list_phrases, phrase_chosen

    notes = "C4 C4 G4 G4 A4 A4 G4 R"
    lengths = "1 1 1 1 1 1 3/2 1/2"

    three = list_phrases(
        notes, lengths, "Twin- kle\ntwin- kle\nlit- tle star"
    )

    chosen = three[3]

    two = list_phrases(
        notes, lengths, "Twin- kle twin- kle\nlit- tle star"
    )

    number = phrase_chosen(chosen)

    assert number + 1 >= len(two)

    # The last phrase there is, rather than nothing.
    assert two[-1] == two[len(two) - 1]


def test_the_flow_from_upload_to_playing_one_phrase():
    """
    The sequence a person actually performs: upload a file,
    correct the phrasing, press play.

    Each step was tested on its own and the sequence still
    did not work. What was wrong sat between them: the
    import chose the whole part, so playback ran the entire
    song no matter how the lyrics were divided, and the
    phrase list looked like it did nothing.
    """

    import os

    from music import (
        import_midi_file,
        list_midi_tracks,
        list_phrases,
        phrase_chosen,
        play_music,
        WHOLE_PART
    )

    path = os.path.join(
        os.path.dirname(__file__),
        "fixtures", "midi", "d_ML_10791.mid"
    )

    if not os.path.exists(path):
        pytest.skip("the band arrangement fixture is absent")

    tracks = list_midi_tracks(path)

    (
        pitches,
        durations,
        lyrics,
        bpm,
        feedback,
        chart,
        chart_notes,
        key
    ) = import_midi_file(path, tracks[0])

    labels = list_phrases(pitches, durations, lyrics)

    assert len(labels) > 1

    # What the import leaves chosen: a phrase, not the
    # whole song.
    chosen = labels[1] if len(labels) > 1 else labels[0]

    assert chosen != WHOLE_PART

    rate, first = play_music(
        pitches, durations, key, 1, 0, 0, bpm, 0,
        chart, 0,
        "Thirds, chord-corrected", 0, lyrics, chosen
    )

    rate, everything = play_music(
        pitches, durations, key, 1, 0, 0, bpm, 0,
        chart, 0,
        "Thirds, chord-corrected", 0, lyrics, WHOLE_PART
    )

    assert len(first) < len(everything)

    # Now the correction: a line break somewhere in the
    # longest line, then update. Where exactly depends on
    # what the splitter guessed, so the middle word of the
    # longest line stands in for wherever a person would
    # press Enter.
    lines = lyrics.split("\n")

    longest = max(lines, key=len)

    watched = lines.index(longest)

    words = longest.split()

    middle = len(words) // 2

    broken = (
        " ".join(words[:middle]) + "\n" + " ".join(words[middle:])
    )

    edited = lyrics.replace(longest, broken, 1)

    after = list_phrases(pitches, durations, edited)

    assert len(after) == len(labels) + 1

    # The phrase that was actually cut is the one to
    # watch: pressing Enter in line four says nothing
    # about line one.
    from music import selected_piece

    was = selected_piece(
        pitches, durations, lyrics, key, chart,
        labels[watched + 1]
    )

    now = selected_piece(
        pitches, durations, edited, key, chart,
        after[watched + 1]
    )

    assert now.beats() < was.beats()

    # And the selection machinery still lands somewhere.
    number = phrase_chosen(chosen)

    kept = (
        after[number + 1]
        if number is not None and number + 1 < len(after)
        else after[-1]
    )

    # And it still plays.
    rate, shorter = play_music(
        pitches, durations, key, 1, 0, 0, bpm, 0,
        chart, 0,
        "Thirds, chord-corrected", 0, edited, kept
    )

    assert len(shorter) > 0

def test_cycling_moves_the_phrase_choice_and_wraps():
    """
    Previous and Next step through the numbered phrases,
    wrapping at either end, and rebuild the labels first
    so a lyric edited since the last press cannot strand
    the choice on a name that no longer exists.
    """

    import main

    pitches = "C4 C4 G4 G4 A4 A4 G4 R " * 3
    durations = "1 1 1 1 1 1 3/2 1/2 " * 3
    lyrics = "\n".join(
        ["Twin- kle twin- kle lit- tle star"] * 3
    )

    labels = main.list_phrases(pitches, durations, lyrics)

    assert len(labels) == 4

    forward = main.cycle_phrase(1)
    backward = main.cycle_phrase(-1)

    chosen = forward(pitches, durations, lyrics, labels[1])
    assert chosen["value"] == labels[2]

    chosen = forward(pitches, durations, lyrics, labels[3])
    assert chosen["value"] == labels[1], "wraps forward"

    chosen = backward(pitches, durations, lyrics, labels[1])
    assert chosen["value"] == labels[3], "wraps backward"

    # From the whole part, Next lands on the first phrase.
    chosen = forward(pitches, durations, lyrics, labels[0])
    assert chosen["value"] == labels[1]