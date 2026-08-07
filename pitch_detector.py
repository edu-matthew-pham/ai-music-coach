# pitch_detector.py

from typing import NamedTuple

import numpy as np
import librosa

from notes import (
    frequency_to_midi,
    midi_to_note,
    cents_from_nearest_note
)

import debug


# How much quieter than the loudest part of a recording
# something has to be before we treat it as silence.
SILENCE_THRESHOLD_DB = 30


# How finely pyin is allowed to measure, in semitones.
# The default of 0.1 means readings can only ever land on
# multiples of 10 cents, which is too coarse when we are
# telling someone how far out of tune they are.
PITCH_RESOLUTION = 0.05


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


def measure_pitch(sound, sample_rate):
    """
    Detect a pitch and report how the detection went.

    Returns the Pitch along with the number of frames that
    held a steady pitch, the number examined, and the
    average confidence in those frames. The extra numbers
    are only used for debug output.
    """

    frequencies, voiced, probabilities = librosa.pyin(
        sound,
        fmin=librosa.note_to_hz("C3"),
        fmax=librosa.note_to_hz("C6"),
        sr=sample_rate,
        resolution=PITCH_RESOLUTION
    )

    total_frames = len(frequencies)
    detected_frequencies = frequencies[voiced]

    voiced_frames = len(detected_frequencies)

    if voiced_frames == 0:
        confidence = 0.0

    else:
        confidence = float(
            np.mean(probabilities[voiced])
        )

    if voiced_frames == 0:
        return None, 0, total_frames, 0.0

    # Median reduces the effect of occasional incorrect frames.
    frequency = float(
        np.median(detected_frequencies)
    )

    # Keep the decimal MIDI number. Rounding it away here
    # would throw out the tuning information.
    midi = frequency_to_midi(frequency)

    pitch = Pitch(
        frequency=frequency,
        midi=midi,
        note=midi_to_note(midi),
        cents=cents_from_nearest_note(midi)
    )

    return pitch, voiced_frames, total_frames, confidence


def detect_pitch(sound, sample_rate):
    """
    Detect the main musical pitch in one chunk of audio.

    Returns a Pitch, or None when nothing musical is found.
    """

    pitch, voiced, total, confidence = measure_pitch(
        sound,
        sample_rate
    )

    return pitch


def trace_pitch(sound, sample_rate):
    """
    Follow the pitch through a whole recording.

    Where detect_pitch answers "what note was this", this
    answers "what happened over time": one measurement per
    frame, with gaps where nothing was sounding. It is what
    a drawn pitch line is made of.

    Returns two arrays of equal length: times in seconds,
    and MIDI numbers, with NaN where no pitch was found.
    """

    frequencies, voiced, probabilities = librosa.pyin(
        sound,
        fmin=librosa.note_to_hz("C3"),
        fmax=librosa.note_to_hz("C6"),
        sr=sample_rate,
        resolution=PITCH_RESOLUTION
    )

    times = librosa.times_like(
        frequencies,
        sr=sample_rate
    )

    midi = np.full(len(frequencies), np.nan)

    for frame in range(len(frequencies)):

        if voiced[frame]:
            midi[frame] = frequency_to_midi(
                frequencies[frame]
            )

    return times, midi


def trace_performance(audio):
    """
    Trace the pitch of a Gradio recording, trimmed the same
    way detect_sequence trims it, so the two line up.
    """

    if audio is None:
        return None

    sample_rate, sound = audio

    sound = prepare_audio(sound)
    sound = trim_leading_silence(sound)

    return trace_pitch(sound, sample_rate)


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


def trim_leading_silence(sound):
    """
    Remove quiet audio from the start of a recording.

    A performance rarely begins the instant recording does.
    Without this, every note window is shifted by however
    long the player waited, and the later notes drift out of
    their slots completely.

    Only the start is trimmed. Trailing silence is harmless,
    and cutting it could shorten the final note.
    """

    trimmed, interval = librosa.effects.trim(
        sound,
        top_db=SILENCE_THRESHOLD_DB
    )

    if len(trimmed) == 0:
        return sound

    start = interval[0]

    return sound[start:]


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

    recorded_samples = len(sound)

    # Line the recording up with the first thing played,
    # rather than with the moment recording started.
    sound = trim_leading_silence(sound)

    seconds_per_beat = 60 / bpm

    debug.describe_recording(
        total_samples=recorded_samples,
        sample_rate=sample_rate,
        trimmed_samples=len(sound),
        expected_seconds=sum(durations) * seconds_per_beat
    )

    detected_notes = []

    current_time = 0

    for position, beats in enumerate(durations):

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

            debug.say(
                f"  note {position + 1:>2}  "
                f"window {start_time:5.2f}s to {end_time:5.2f}s  "
                f"past the end of the recording"
            )

            current_time = end_time
            continue

        middle_sound = get_middle(
            sound,
            start_sample,
            end_sample
        )

        if len(middle_sound) == 0:

            detected_notes.append(None)

            debug.say(
                f"  note {position + 1:>2}  "
                f"window {start_time:5.2f}s to {end_time:5.2f}s  "
                f"nothing left to listen to"
            )

        else:
            pitch, voiced, total, confidence = measure_pitch(
                middle_sound,
                sample_rate
            )

            detected_notes.append(pitch)

            debug.describe_window(
                position=position,
                start_time=start_time,
                end_time=end_time,
                listened_samples=len(middle_sound),
                sample_rate=sample_rate,
                voiced_frames=voiced,
                total_frames=total,
                frequency=None if pitch is None else pitch.frequency,
                confidence=confidence
            )

        current_time = end_time

    return detected_notes