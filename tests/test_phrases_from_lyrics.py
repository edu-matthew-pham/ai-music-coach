"""
Phrases come from the lyrics.

A line of a song is a phrase. Nothing in a MIDI file says
reliably where those fall - some files have no rests, some
are not written to bars at all, and the same song arranged
twice divides differently - but anyone who knows the song
can see it at a glance.

So the splitter writes its guess as line breaks in the
lyrics box, and from then on the line breaks are the
phrasing. The algorithm stops being load-bearing: when it
is wrong it costs a keystroke instead of being unusable.
"""

import pytest

from music import (
    lyric_line_breaks,
    phrases_from_lyrics,
    read_lyrics,
    read_music,
    MusicInputError
)


WELLERMAN = "A3 D4 D4 D4 D4 F4 A4 A4 A4 R D4 D4 F4 A4 A4 G4 F4"
LENGTHS = "1 1 1/2 1/2 1 1 1 1 1 1 1 1 1 1 1 1 2"

# Sixteen syllables for sixteen sung notes, in two lines.
WORDS = """There once was a ship that put to sea
The name of the ship was Tea"""


def test_a_line_of_lyrics_is_a_phrase():
    pitches, durations = read_music(WELLERMAN, LENGTHS)

    phrases = phrases_from_lyrics(pitches, durations, WORDS)

    assert len(phrases) == 2


def test_line_breaks_are_counted_in_syllables():
    assert lyric_line_breaks("one two\nthree four five") == [2]

    assert lyric_line_breaks(
        "a b\nc d\ne f"
    ) == [2, 4]


def test_one_line_is_one_phrase():
    pitches, durations = read_music(WELLERMAN, LENGTHS)

    assert lyric_line_breaks("Twin- kle twin- kle") == []

    assert len(
        phrases_from_lyrics(pitches, durations, "all one line")
    ) == 1


def test_no_lyrics_means_no_division():
    pitches, durations = read_music(WELLERMAN, LENGTHS)

    phrases = phrases_from_lyrics(pitches, durations, "")

    assert phrases == [(0, len(pitches) - 1)]


def test_blank_lines_are_not_empty_phrases():
    """
    Pressing Enter twice is a typing accident, not a
    phrase with no words in it.
    """

    assert lyric_line_breaks("one two\n\n\nthree four") == [2]


def test_a_breath_belongs_to_the_line_before_it():
    """
    Syllables count only sung notes, so a rest between two
    lines stays with the line it follows: the breath at the
    end of a phrase is part of that phrase.
    """

    pitches, durations = read_music(WELLERMAN, LENGTHS)

    first, second = phrases_from_lyrics(pitches, durations, WORDS)

    # The rest is the tenth note, and closes the first
    # phrase rather than opening the second.
    assert pitches[first[1]] == "R"
    assert pitches[second[0]] != "R"


def test_line_breaks_do_not_disturb_the_syllable_count():
    """
    Newlines are whitespace, so the mapping of syllables to
    notes is exactly as it was before phrases lived here.
    """

    pitches, durations = read_music(WELLERMAN, LENGTHS)

    flat = WORDS.replace("\n", " ")

    sung = len([pitch for pitch in pitches if pitch != "R"])

    assert read_lyrics(WORDS, sung) == read_lyrics(flat, sung)


def test_a_miscount_is_still_reported():
    pitches, durations = read_music(WELLERMAN, LENGTHS)

    with pytest.raises(MusicInputError, match="syllable"):
        read_lyrics("too few words\nhere", len(pitches))


def test_the_guess_survives_being_written_and_read_back():
    """
    The splitter writes its phrasing as line breaks, and
    reading those back gives the same phrases. Anything
    else would mean the box and the dropdown disagreed
    from the moment a file was loaded.
    """

    import os

    import mido

    from midi_import import (
        read_notes,
        keep_melody,
        read_lyric_events,
        read_time_signature,
        split_into_phrases,
        lyrics_for,
        lyrics_with_line_breaks,
        find_parts,
        rank_parts
    )
    from notes import midi_to_note

    path = os.path.join(
        os.path.dirname(__file__),
        "fixtures", "midi", "d_ML_10791.mid"
    )

    if not os.path.exists(path):
        pytest.skip("the band arrangement fixture is absent")

    midi_file = mido.MidiFile(path)

    part = rank_parts(midi_file, find_parts(midi_file))[0]

    notes, bpm = read_notes(
        midi_file, part["track"], part["channel"]
    )

    melody = keep_melody(notes)

    events = read_lyric_events(midi_file, part["track"])

    guessed = split_into_phrases(
        melody, read_time_signature(midi_file), bpm
    )

    words = lyrics_with_line_breaks(
        melody, guessed, lyrics_for(melody, events)
    )

    pitches = [midi_to_note(n) for start, length, n in melody]
    durations = [length for start, length, n in melody]

    read_back = phrases_from_lyrics(pitches, durations, words)

    assert len(read_back) == len(guessed)

    for position in range(len(guessed)):

        first, last = read_back[position]

        assert last - first + 1 == len(guessed[position])


def test_a_correction_changes_the_phrasing():
    """
    The whole point: when the guess is wrong it costs a
    keystroke.
    """

    pitches, durations = read_music(WELLERMAN, LENGTHS)

    before = phrases_from_lyrics(
        pitches, durations, WORDS.replace("\n", " ")
    )

    after = phrases_from_lyrics(pitches, durations, WORDS)

    assert len(before) == 1
    assert len(after) == 2