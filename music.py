# music.py

import numpy as np

from playback import (
    make_melody,
    make_layered_melody
)

from harmony import make_harmony

from pitch_detector import (
    detect_single_note,
    detect_sequence
)

from instrument_detector import (
    detect_instrument
)


# How far out of tune a note may be before it is worth
# mentioning. Around 15 cents is roughly where a listener
# starts to notice on a sustained note.
TUNING_TOLERANCE_CENTS = 15


def describe_tuning(pitch):
    """
    Turn a Pitch into a short readable tuning comment.
    """

    if pitch.is_in_tune(TUNING_TOLERANCE_CENTS):
        return "in tune"

    cents = round(pitch.cents)

    if cents > 0:
        return f"{cents} cents sharp"

    return f"{abs(cents)} cents flat"


def describe_pitch(pitch):
    """
    Format one detected pitch for display.

    Notes that are close enough are shown as just a name,
    so that only the notes worth attention are annotated.
    """

    if pitch is None:
        return "?"

    if pitch.is_in_tune(TUNING_TOLERANCE_CENTS):
        return pitch.note

    return f"{pitch.note}({round(pitch.cents):+d})"


def read_music(pitch_text, duration_text):
    """
    Turn textbox input into Python lists.
    """

    pitches = pitch_text.split()
    duration_strings = duration_text.split()

    durations = []

    for duration in duration_strings:
        durations.append(float(duration))

    if len(pitches) != len(durations):
        raise ValueError(
            "There must be one duration for every pitch."
        )

    return pitches, durations


def play_music(
    pitch_text,
    duration_text,
    key,
    playback_mode,
    bpm
):
    """
    Generate melody, harmony, or both.
    """

    pitches, durations = read_music(
        pitch_text,
        duration_text
    )

    bpm = float(bpm)

    if playback_mode == "Melody":

        sample_rate, sound = make_melody(
            pitches,
            durations,
            bpm
        )

    elif playback_mode == "Harmony":

        harmony = make_harmony(
            pitches,
            key=key
        )

        sample_rate, sound = make_melody(
            harmony,
            durations,
            bpm
        )

    elif playback_mode == "Melody + Harmony":

        harmony = make_harmony(
            pitches,
            key=key
        )

        sample_rate, sound = make_layered_melody(
            pitches,
            harmony,
            durations,
            bpm
        )

    else:
        raise ValueError(
            f"Unknown playback mode: {playback_mode}"
        )

    audio_data = np.array(
        sound,
        dtype=np.float32
    )

    return sample_rate, audio_data


def show_harmony(pitch_text, key):
    """
    Return the generated harmony notes as text.
    """

    pitches = pitch_text.split()

    harmony = make_harmony(
        pitches,
        key=key
    )

    return " ".join(harmony)


def analyse_single_note(audio):
    """
    Detect the main pitch in a recording.
    """

    pitch = detect_single_note(audio)

    if pitch is None:
        return "No clear pitch detected."

    return (
        f"Detected note: {pitch.note} "
        f"({describe_tuning(pitch)})"
    )


def analyse_sequence(
    audio,
    duration_text,
    bpm
):
    """
    Detect a sequence using the expected note durations.
    """

    duration_strings = duration_text.split()

    durations = []

    for duration in duration_strings:
        durations.append(float(duration))

    pitches = detect_sequence(
        audio,
        durations,
        float(bpm)
    )

    display_notes = []

    for pitch in pitches:
        display_notes.append(
            describe_pitch(pitch)
        )

    return " ".join(display_notes)


def analyse_instrument(audio):
    """
    Format the instrument detector's top predictions.
    """

    results = detect_instrument(audio)

    if len(results) == 0:
        return "No audio provided."

    lines = []

    for result in results:

        label = result["label"]

        confidence = round(
            result["score"] * 100,
            1
        )

        lines.append(
            f"{label}: {confidence}%"
        )

    return "\n".join(lines)


def load_twinkle_phrase():
    """
    Return the opening phrase of Twinkle Twinkle Little Star.
    """

    pitches = (
        "C4 C4 G4 G4 A4 A4 G4"
    )

    durations = (
        "1 1 1 1 1 1 2"
    )

    return pitches, durations