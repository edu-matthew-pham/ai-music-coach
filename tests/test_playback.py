import pytest

from playback import (
    note_to_frequency,
    make_note,
    mix_tracks
)


def test_a4_frequency():
    assert note_to_frequency("A4") == pytest.approx(
        440,
        abs=0.01
    )


def test_c4_frequency():
    assert note_to_frequency("C4") == pytest.approx(
        261.63,
        abs=0.01
    )


def test_one_beat_length():
    sound = make_note(
        "A4",
        beats=1,
        bpm=120,
        sample_rate=8000
    )

    # 120 BPM = 0.5 seconds per beat.
    assert len(sound) == 4000


def test_mix_tracks():
    track_1 = [1, 0, -1]
    track_2 = [-1, 0, 1]

    assert mix_tracks(
        track_1,
        track_2
    ) == [0, 0, 0]