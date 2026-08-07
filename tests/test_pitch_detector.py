import math

import numpy as np
import pytest

from playback import make_note
from pitch_detector import detect_pitch, Pitch


def make_sine(frequency, seconds=1.0, sample_rate=8000):
    """
    Build a plain sine wave at an exact frequency.

    This lets us test tuning against a signal whose pitch
    we control precisely, rather than a named note.
    """

    return np.array([
        math.sin(2 * math.pi * frequency * t / sample_rate)
        for t in range(int(seconds * sample_rate))
    ])


def test_detect_generated_a4():
    sample_rate = 8000

    sound = np.array(
        make_note(
            "A4",
            beats=2,
            bpm=120,
            sample_rate=sample_rate
        )
    )

    pitch = detect_pitch(sound, sample_rate)

    assert isinstance(pitch, Pitch)
    assert pitch.note == "A4"
    assert pitch.frequency == pytest.approx(440, abs=1)
    assert pitch.midi == pytest.approx(69, abs=0.1)


def test_in_tune_note_has_almost_no_cents():
    sound = make_sine(440)

    pitch = detect_pitch(sound, 8000)

    assert abs(pitch.cents) < 5
    assert pitch.is_in_tune()


def test_sharp_note_is_reported_as_sharp():
    """
    A4 raised by 40 cents should still be named A4,
    but reported as sharp.
    """

    frequency = 440 * (2 ** (40 / 1200))

    pitch = detect_pitch(make_sine(frequency), 8000)

    assert pitch.note == "A4"
    assert pitch.cents == pytest.approx(40, abs=5)
    assert not pitch.is_in_tune()


def test_flat_note_is_reported_as_flat():
    frequency = 440 * (2 ** (-40 / 1200))

    pitch = detect_pitch(make_sine(frequency), 8000)

    assert pitch.note == "A4"
    assert pitch.cents == pytest.approx(-40, abs=5)
    assert not pitch.is_in_tune()


def test_silence_detects_nothing():
    silence = np.zeros(8000)

    assert detect_pitch(silence, 8000) is None