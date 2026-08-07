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

    # pyin searches a grid of candidate pitches rather than
    # measuring continuously, and that grid does not line up
    # exactly with equal temperament at low sample rates.
    # At 8 kHz this leaves a small constant bias of a few
    # cents, so the tolerance here is deliberately loose.
    assert pitch.frequency == pytest.approx(440, abs=2)
    assert pitch.midi == pytest.approx(69, abs=0.1)


def test_in_tune_note_has_almost_no_cents():
    """
    A perfectly tuned tone should be reported as in tune.

    It will not read exactly zero cents at 8 kHz because of
    the search grid described above, but it must land well
    inside the tolerance we use to judge a note correct.
    """

    sound = make_sine(440)

    pitch = detect_pitch(sound, 8000)

    assert abs(pitch.cents) <= 6
    assert pitch.is_in_tune()


def test_badly_detuned_note_keeps_the_right_name():
    """
    A note 44 cents sharp is still nearer to A4 than to A#4,
    so it must not be named as the neighbouring semitone.

    The coarser pyin default used to fail this, naming the
    wrong note and reporting the error from there instead.
    """

    frequency = 440 * (2 ** (44 / 1200))

    pitch = detect_pitch(make_sine(frequency), 8000)

    assert pitch.note == "A4"
    assert pitch.cents == pytest.approx(44, abs=8)


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