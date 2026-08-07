# pitch_detector.py

import numpy as np
import librosa


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
    frequency = np.median(
        detected_frequencies
    )

    # Convert frequency to the nearest musical note.
    midi_number = round(
        float(librosa.hz_to_midi(frequency))
    )

    note = librosa.midi_to_note(
        midi_number,
        unicode=False
    )

    return note


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
            note = detect_pitch(
                middle_sound,
                sample_rate
            )

            detected_notes.append(note)

        current_time = end_time

    return detected_notes