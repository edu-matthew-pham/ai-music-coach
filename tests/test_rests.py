"""
Rests: silence that is part of the music.

A rest has a length but no pitch. It keeps the timing of
everything after it, gives a singer somewhere to breathe,
and is never something to get right or wrong.
"""

import numpy as np
import pytest

from notes import is_rest, REST
from playback import make_note, make_melody
from harmony import make_harmony, keys_containing
from compare import compare_sequence, summarise
from music import read_music, read_lyrics, sung_count, MusicInputError
from helpers import fake_played


def test_rest_markers():
    assert is_rest("R")
    assert is_rest("r")
    assert is_rest("-")
    assert not is_rest("C4")


def test_a_rest_is_silence_of_the_right_length():
    rest = make_note(REST, beats=1, bpm=120, sample_rate=8000)

    assert len(rest) == 4000
    assert max(rest) == 0
    assert min(rest) == 0


def test_a_rest_keeps_the_timing_of_what_follows():
    """
    The note after a rest must start later, not earlier.
    """

    rate, without = make_melody(
        ["C4", "E4"], [1, 1], 120, 8000
    )

    rate, with_rest = make_melody(
        ["C4", REST, "E4"], [1, 1, 1], 120, 8000
    )

    assert len(with_rest) == len(without) + 4000


def test_harmony_rests_where_the_melody_rests():
    assert make_harmony(
        ["C4", REST, "G4"], key="C"
    ) == ["A3", REST, "E4"]


def test_keys_ignore_rests():
    assert "C" in keys_containing(["C4", REST, "G4"])


def test_a_rest_is_not_marked():
    """
    Nothing was meant to be sung, so a rest is neither
    right nor wrong, and does not count in the score.
    """

    comparisons = compare_sequence(
        ["C4", REST, "G4"],
        [fake_played("C4"), None, fake_played("G4")]
    )

    assert comparisons[1].is_rest
    assert not comparisons[1].is_target_note

    summary = summarise(comparisons)

    assert summary["total"] == 2
    assert summary["on_target"] == 2


def test_silence_during_a_rest_is_not_a_missed_note():
    """
    A singer who correctly sings nothing scores the same
    as one who sings everything.
    """

    comparisons = compare_sequence(
        ["C4", REST],
        [fake_played("C4"), None]
    )

    summary = summarise(comparisons)

    assert summary["total"] == 1
    assert summary["detected"] == 1


def test_rests_are_accepted_in_the_music_box():
    pitches, durations = read_music("C4 R G4", "1 1 1")

    assert pitches == ["C4", "R", "G4"]


def test_rests_take_no_syllable():
    pitches, durations = read_music("C4 R G4", "1 1 1")

    assert sung_count(pitches) == 2

    assert read_lyrics("la la", sung_count(pitches)) == ["la", "la"]


def test_lyric_mismatch_mentions_sung_notes():
    with pytest.raises(MusicInputError, match="sung notes"):
        read_lyrics("la la la", 2)


def test_imported_gaps_become_rests(tmp_path):
    """
    A gap in a MIDI file is silence the composer wrote,
    and must survive the import or everything after it
    arrives too early.
    """

    import mido
    from midi_import import import_midi

    midi_file = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    midi_file.tracks.append(track)

    # A note, a beat of silence, then another note.
    track.append(
        mido.Message("note_on", note=60, velocity=80, time=0)
    )
    track.append(
        mido.Message("note_off", note=60, velocity=0, time=480)
    )
    track.append(
        mido.Message("note_on", note=64, velocity=80, time=480)
    )
    track.append(
        mido.Message("note_off", note=64, velocity=0, time=480)
    )

    path = str(tmp_path / "gap.mid")
    midi_file.save(path)

    pitches, durations, lyrics, bpm = import_midi(path)

    assert pitches == "C4 R E4"
    assert durations == "1 1 1"
