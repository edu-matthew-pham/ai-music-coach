# tests/test_music.py

import numpy as np
import pytest

from music import (
    read_music,
    play_music,
    show_harmony,
    analyse_single_note,
    analyse_sequence,
    analyse_instrument,
    load_twinkle_phrase
)


def test_read_music():
    pitches, durations = read_music(
        "C4 D4 E4",
        "1 1 2"
    )

    assert pitches == ["C4", "D4", "E4"]
    assert durations == [1.0, 1.0, 2.0]


def test_read_music_requires_matching_lengths():
    with pytest.raises(ValueError):
        read_music(
            "C4 D4 E4",
            "1 1"
        )


def test_show_harmony():
    harmony = show_harmony(
        "C4 G4 A4",
        "C"
    )

    assert harmony == "A3 E4 F4"


def test_play_music_returns_gradio_audio():
    sample_rate, audio = play_music(
        "C4 C4",
        "1 1",
        "C",
        "Melody",
        120
    )

    assert sample_rate == 8000
    assert isinstance(audio, np.ndarray)

    # Two beats at 120 BPM = one second.
    assert len(audio) == 8000


def test_play_music_rejects_unknown_mode():
    with pytest.raises(ValueError):
        play_music(
            "C4",
            "1",
            "C",
            "Unknown",
            120
        )


def test_load_twinkle_phrase():
    pitches, durations = load_twinkle_phrase()

    assert pitches == "C4 C4 G4 G4 A4 A4 G4"
    assert durations == "1 1 1 1 1 1 2"


def test_analyse_single_note_no_pitch(monkeypatch):
    monkeypatch.setattr(
        "music.detect_single_note",
        lambda audio: None
    )

    result = analyse_single_note(
        "fake audio"
    )

    assert result == "No clear pitch detected."


def test_analyse_single_note(monkeypatch):
    monkeypatch.setattr(
        "music.detect_single_note",
        lambda audio: "A4"
    )

    result = analyse_single_note(
        "fake audio"
    )

    assert result == "Detected note: A4"


def test_analyse_sequence(monkeypatch):
    monkeypatch.setattr(
        "music.detect_sequence",
        lambda audio, durations, bpm: [
            "C4",
            "G4",
            None
        ]
    )

    result = analyse_sequence(
        "fake audio",
        "1 1 2",
        120
    )

    assert result == "C4 G4 ?"


def test_analyse_instrument(monkeypatch):
    fake_results = [
        {
            "label": "violin",
            "score": 0.82
        },
        {
            "label": "flute",
            "score": 0.11
        },
        {
            "label": "keyboard",
            "score": 0.07
        }
    ]

    monkeypatch.setattr(
        "music.detect_instrument",
        lambda audio: fake_results
    )

    result = analyse_instrument(
        "fake audio"
    )

    assert result == (
        "violin: 82.0%\n"
        "flute: 11.0%\n"
        "keyboard: 7.0%"
    )