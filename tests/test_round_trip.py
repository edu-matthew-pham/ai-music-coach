import numpy as np
import pytest

from notes import note_to_midi
from playback import make_melody
from pitch_detector import detect_sequence


def round_trip(pitches, durations, bpm=120, sample_rate=8000):
    """
    Synthesise a melody, then run it back through the detector.

    This closes the loop between the two halves of the app
    without needing a microphone or a recorded file.
    """

    rate, melody = make_melody(
        pitches,
        durations,
        bpm,
        sample_rate
    )

    audio = (rate, np.array(melody))

    detected = detect_sequence(
        audio,
        durations,
        bpm
    )

    # Compare on MIDI numbers rather than names, so that
    # a different spelling of the same pitch still matches.
    return [
        None if pitch is None else round(pitch.midi)
        for pitch in detected
    ]


def as_midi(pitches):
    """
    The MIDI numbers we expect a melody to come back as.
    """

    return [note_to_midi(pitch) for pitch in pitches]


def test_round_trip_simple_triad():
    pitches = ["C4", "E4", "G4"]
    durations = [1.0, 1.0, 1.0]

    assert round_trip(pitches, durations) == as_midi(pitches)


def test_round_trip_twinkle_phrase():
    pitches = ["C4", "C4", "G4", "G4", "A4", "A4", "G4"]
    durations = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 2.0]

    assert round_trip(pitches, durations) == as_midi(pitches)


def test_round_trip_mixed_durations():
    """
    Uneven note lengths mean each analysis window is a
    different size, so the windowing maths has to be right.
    """

    pitches = ["C4", "E4", "G4"]
    durations = [2.0, 0.5, 1.0]

    assert round_trip(pitches, durations) == as_midi(pitches)


@pytest.mark.parametrize("bpm", [60, 120, 180])
def test_round_trip_survives_tempo_changes(bpm):
    pitches = ["C4", "E4", "G4"]
    durations = [1.0, 1.0, 1.0]

    assert round_trip(pitches, durations, bpm=bpm) == as_midi(pitches)


@pytest.mark.parametrize(
    "pitches",
    [
        ["C3", "E3", "G3"],
        ["C4", "E4", "G4"],
        ["C5", "E5", "G5"]
    ]
)
def test_round_trip_across_the_register(pitches):
    """
    The detector is limited to C3 - C6, so these three
    triads cover most of its usable range.
    """

    durations = [1.0, 1.0, 1.0]

    assert round_trip(pitches, durations) == as_midi(pitches)


def test_round_trip_with_short_notes():
    """
    Quarter beats at 120 BPM give roughly 600 samples per
    analysis window at 8 kHz. This is close to the shortest
    note the detector can currently resolve, so it guards
    the lower limit.
    """

    pitches = ["C4", "E4", "G4"]
    durations = [0.25, 0.25, 0.25]

    assert round_trip(pitches, durations) == as_midi(pitches)


def round_trip_with_delay(
    pitches,
    durations,
    delay_seconds,
    bpm=120,
    sample_rate=8000
):
    """
    Synthesise a melody with silence in front of it.

    This is what a real recording looks like: the player
    does not start the instant recording begins.
    """

    rate, melody = make_melody(
        pitches,
        durations,
        bpm,
        sample_rate
    )

    silence = np.zeros(
        int(delay_seconds * sample_rate)
    )

    delayed = np.concatenate([
        silence,
        np.array(melody)
    ])

    detected = detect_sequence(
        (rate, delayed),
        durations,
        bpm
    )

    return [
        None if pitch is None else round(pitch.midi)
        for pitch in detected
    ]


@pytest.mark.parametrize(
    "delay_seconds",
    [0.3, 1.0, 2.5]
)
def test_round_trip_survives_a_late_start(delay_seconds):
    """
    Waiting before playing must not shift every note out of
    its window. Without trimming, a delay of a second at
    120 BPM pushes the whole performance two notes along.
    """

    pitches = ["C4", "E4", "G4", "C4"]
    durations = [1.0, 1.0, 1.0, 1.0]

    detected = round_trip_with_delay(
        pitches,
        durations,
        delay_seconds
    )

    assert detected == as_midi(pitches)