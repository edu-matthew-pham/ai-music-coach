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

    pitches, durations, lyrics, bpm, chart, chart_notes = import_midi(path)

    assert pitches == "C4 R E4"
    assert durations == "1 1 1"


def test_triplets_are_written_as_fractions():
    """
    A third of a beat has no exact decimal, so it is
    written the way a musician reads it.
    """

    from music import read_beats

    assert read_beats("1/3") == pytest.approx(1 / 3)
    assert read_beats("2/3") == pytest.approx(2 / 3)
    assert read_beats("4/3") == pytest.approx(4 / 3)


def test_a_triplet_fills_its_beat_exactly():
    """
    Three triplet notes make one beat, which decimals
    written into a textbox cannot quite manage.
    """

    pitches, durations = read_music(
        "C4 E4 G4",
        "1/3 1/3 1/3"
    )

    assert sum(durations) == pytest.approx(1.0)


def test_plain_lengths_still_read():
    from music import read_beats

    assert read_beats("1") == 1.0
    assert read_beats("0.75") == 0.75


def test_nonsense_fractions_are_rejected():
    from music import read_beats

    with pytest.raises(MusicInputError, match="Fractions look like"):
        read_beats("1/0")

    with pytest.raises(MusicInputError, match="Fractions look like"):
        read_beats("a/3")


def test_every_way_in_reads_fractions():
    """
    Durations are parsed in more than one place, and a
    fraction that works when the music is played must also
    work when the recording is compared. This checks each
    way in rather than trusting them to agree.
    """

    import numpy as np

    from playback import make_melody
    from music import play_music, analyse_sequence, analyse_performance

    pitches = "C4 E4 G4"
    durations = "1/2 1/2 1"

    # Playing it.
    rate, audio = play_music(
        pitches, durations, "C",
        melody_level=1, harmony_below_level=0, bpm=120
    )

    assert len(audio) > 0

    # Detecting a recording of it.
    rate, sound = make_melody(
        ["C4", "E4", "G4"], [0.5, 0.5, 1.0], 120, 8000
    )

    recording = (rate, np.array(sound))

    heard = analyse_sequence(recording, durations, 120)

    assert "C4" in heard

    # Comparing a performance of it.
    text, performance, tuning = analyse_performance(
        recording, pitches, durations, 120
    )

    assert "3 of 3" in text


def test_a_long_silence_is_written_as_bars_of_rest():
    """
    Nobody writes fourteen and a quarter beats of nothing
    as one mark, and nobody could read it. A singer
    counting through an instrumental verse counts bars, and
    the box should say what they would count.
    """

    from midi_import import write_rest

    durations = []
    pitches = []

    write_rest(durations, pitches, 14.25, 4)

    # Three whole bars and what is left of a fourth.
    assert durations == [4, 4, 4, 2.25]
    assert pitches == ["R"] * 4


def test_a_short_silence_stays_one_rest():
    from midi_import import write_rest

    durations = []
    pitches = []

    write_rest(durations, pitches, 1.5, 4)

    assert durations == [1.5]


def test_no_imported_length_is_longer_than_a_bar():
    import os

    from midi_import import import_midi

    from fractions import Fraction

    path = os.path.join(
        os.path.dirname(__file__),
        "fixtures", "midi", "d_ML_10791.mid"
    )

    if not os.path.exists(path):
        pytest.skip("the band arrangement fixture is absent")

    pitches, durations, lyrics, bpm, chart, notes = import_midi(
        path, track_number=0, channel=0
    )

    longest = max(
        float(Fraction(text)) for text in durations.split()
    )

    assert longest <= 4