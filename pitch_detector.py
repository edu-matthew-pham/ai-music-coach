# pitch_detector.py

from typing import NamedTuple

import numpy as np
import librosa

from notes import (
    frequency_to_midi,
    midi_to_note,
    cents_from_nearest_note
)


class Pitch(NamedTuple):
    """
    One detected pitch.

    frequency  the measured frequency in hertz
    midi       the measured pitch as a decimal MIDI number
    note       the nearest note name, such as C4
    cents      how far from that note, between -50 and +50
    """

    frequency: float
    midi: float
    note: str
    cents: float

    def is_in_tune(self, tolerance=15):
        """
        Whether the pitch is close enough to count as correct.
        """

        return abs(self.cents) <= tolerance


def prepare_audio(sound):
    """
    Convert recorded audio to a simple mono floating-point signal.
    """

    if sound.ndim > 1:
        sound = sound.mean(axis=1)

    sound = sound.astype(float)

    # Gradio recordings may contain integer audio values.
    # Scale them into approximately -1 to 1 when necessary.
    largest_value = np.max(np.abs(sound))

    if largest_value > 1:
        sound = sound / largest_value

    return sound


def detect_pitch(sound, sample_rate):
    """
    Detect the main musical pitch in one chunk of audio.

    Returns a Pitch, or None when nothing musical is found.
    """

    frequencies, voiced, probabilities = librosa.pyin(
        sound,
        fmin=librosa.note_to_hz("C3"),
        fmax=librosa.note_to_hz("C6"),
        sr=sample_rate
    )

    detected_frequencies = frequencies[voiced]

    if len(detected_frequencies) == 0:
        return None

    # Median reduces the effect of occasional incorrect frames.
    frequency = float(
        np.median(detected_frequencies)
    )

    # Keep the decimal MIDI number. Rounding it away here
    # would throw out the tuning information.
    midi = frequency_to_midi(frequency)

    return Pitch(
        frequency=frequency,
        midi=midi,
        note=midi_to_note(midi),
        cents=cents_from_nearest_note(midi)
    )


def detect_single_note(audio):
    """
    Detect one main note from an entire Gradio recording.
    """

    if audio is None:
        return None

    sample_rate, sound = audio

    sound = prepare_audio(sound)

    return detect_pitch(
        sound,
        sample_rate
    )


def get_middle(
    sound,
    start_sample,
    end_sample,
    middle_amount=0.6
):
    """
    Take the middle portion of an expected note window.

    Using the central 60% avoids many note transitions.
    """

    window_length = end_sample - start_sample

    ignored_amount = (
        1 - middle_amount
    ) / 2

    middle_start = start_sample + int(
        window_length * ignored_amount
    )

    middle_end = end_sample - int(
        window_length * ignored_amount
    )

    return sound[
        middle_start:middle_end
    ]


def detect_sequence(
    audio,
    durations,
    bpm=120
):
    """
    Detect several notes from a completed recording.

    Expected durations tell us where each note should occur.
    Returns a list of Pitch objects, using None for any
    window where no pitch could be found.
    """

    if audio is None:
        return []

    sample_rate, sound = audio

    sound = prepare_audio(sound)

    detected_notes = []

    seconds_per_beat = 60 / bpm
    current_time = 0

    for beats in durations:

        duration_seconds = (
            beats * seconds_per_beat
        )

        start_time = current_time
        end_time = (
            current_time + duration_seconds
        )

        start_sample = int(
            start_time * sample_rate
        )

        end_sample = int(
            end_time * sample_rate
        )

        # Prevent windows extending beyond the recording.
        end_sample = min(
            end_sample,
            len(sound)
        )

        if start_sample >= len(sound):
            detected_notes.append(None)
            current_time = end_time
            continue

        middle_sound = get_middle(
            sound,
            start_sample,
            end_sample
        )

        if len(middle_sound) == 0:
            detected_notes.append(None)

        else:
            pitch = detect_pitch(
                middle_sound,
                sample_rate
            )

            detected_notes.append(pitch)

        current_time = end_time

    return detected_notes