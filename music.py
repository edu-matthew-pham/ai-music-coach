# music.py

import numpy as np

from playback import (
    make_melody,
    make_layered_melody
)

from harmony import make_harmony, keys_containing

from notes import split_note

from compare import (
    compare_sequence,
    summarise,
    suggest_transpose
)

from tuning_plot import make_tuning_plot

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


class MusicInputError(ValueError):
    """
    Something about the music the user typed does not work.

    The message is written to be shown to them directly, so
    it should say what is wrong and what would fix it.
    """


def check_note_names(pitches):
    """
    Make sure every pitch is a note name we understand.
    """

    for pitch in pitches:

        if len(pitch) < 2 or not pitch[-1].isdigit():
            raise MusicInputError(
                f"'{pitch}' is not a note. Notes look like "
                f"C4, F#4 or Bb3."
            )

        try:
            split_note(pitch)

        except ValueError:
            raise MusicInputError(
                f"'{pitch}' is not a note. Notes look like "
                f"C4, F#4 or Bb3."
            )


def check_bpm(bpm):
    """
    Make sure the tempo is a usable number.
    """

    try:
        bpm = float(bpm)

    except (TypeError, ValueError):
        raise MusicInputError(
            "The tempo must be a number."
        )

    if bpm <= 0:
        raise MusicInputError(
            "The tempo must be greater than zero."
        )

    return bpm


def check_key_fits(pitches, key):
    """
    Make sure a harmony can actually be built in this key.

    When it cannot, suggest a key that would work.
    """

    workable = keys_containing(pitches)

    if key in workable:
        return

    if len(workable) == 0:
        raise MusicInputError(
            "These notes do not fit any of the available "
            "keys, so no harmony can be built."
        )

    suggestion = " or ".join(workable)

    raise MusicInputError(
        f"These notes do not all fit in {key} major. "
        f"Try {suggestion}."
    )


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

    if len(pitches) == 0:
        raise MusicInputError(
            "Enter some notes first, such as C4 D4 E4."
        )

    check_note_names(pitches)

    durations = []

    for duration in duration_strings:

        try:
            beats = float(duration)

        except ValueError:
            raise MusicInputError(
                f"'{duration}' is not a number of beats."
            )

        if beats <= 0:
            raise MusicInputError(
                "Every note must last longer than zero beats."
            )

        durations.append(beats)

    if len(pitches) != len(durations):
        raise MusicInputError(
            f"There are {len(pitches)} notes but "
            f"{len(durations)} durations. "
            f"Each note needs one duration."
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

    bpm = check_bpm(bpm)

    if playback_mode == "Melody":

        sample_rate, sound = make_melody(
            pitches,
            durations,
            bpm
        )

    elif playback_mode == "Harmony":

        check_key_fits(pitches, key)

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

        check_key_fits(pitches, key)

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
        raise MusicInputError(
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

    if len(pitches) == 0:
        raise MusicInputError(
            "Enter some notes first, such as C4 D4 E4."
        )

    check_note_names(pitches)
    check_key_fits(pitches, key)

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


def describe_comparison(comparison):
    """
    Describe one compared note in words.

    The wording follows what a listener would notice: small
    errors are not worth mentioning, and a note that lands
    nearer a different note is named as that note instead.
    """

    if not comparison.was_detected:
        return f"{comparison.target}: nothing detected"

    label = comparison.target

    if comparison.expected != comparison.target:
        label = f"{comparison.target} (as {comparison.expected})"

    cents = comparison.cents_from_target
    direction = "sharp" if cents > 0 else "flat"

    if abs(cents) <= 10:
        return f"{label}: in tune"

    if not comparison.is_target_note:
        return (
            f"{label}: heard {comparison.heard}, "
            f"{abs(round(cents))} cents {direction}"
        )

    if abs(cents) <= 25:
        return (
            f"{label}: slightly {direction} "
            f"({round(cents):+d})"
        )

    return (
        f"{label}: clearly {direction} "
        f"({round(cents):+d})"
    )


def describe_summary(summary):
    """
    One line describing how the performance went overall.
    """

    if summary["detected"] == 0:
        return "No notes were detected in that recording."

    average = round(summary["average_cents_off"])

    return (
        f"{summary['on_target']} of {summary['total']} notes "
        f"on the right pitch. "
        f"Average {average} cents from target."
    )


def describe_shift(semitones):
    """
    Say what a shift means in words a musician would use.
    """

    if semitones % 12 == 0:

        octaves = abs(semitones) // 12
        direction = "below" if semitones < 0 else "above"

        if octaves == 1:
            return f"an octave {direction}"

        return f"{octaves} octaves {direction}"

    direction = "below" if semitones < 0 else "above"

    return f"{abs(semitones)} semitones {direction}"


def check_transpose(transpose):
    """
    Make sure the shift is a sensible number of semitones.
    """

    try:
        transpose = int(transpose)

    except (TypeError, ValueError):
        raise MusicInputError(
            "The shift must be a whole number of semitones."
        )

    if abs(transpose) > 36:
        raise MusicInputError(
            "The shift must be within three octaves."
        )

    return transpose


def analyse_performance(
    audio,
    pitch_text,
    duration_text,
    bpm,
    transpose=0
):
    """
    Compare a recording against the target music.

    Returns a written summary and a tuning chart.
    """

    if audio is None:
        raise MusicInputError(
            "Record or upload a performance first."
        )

    pitches, durations = read_music(
        pitch_text,
        duration_text
    )

    bpm = check_bpm(bpm)
    transpose = check_transpose(transpose)

    detected = detect_sequence(
        audio,
        durations,
        bpm
    )

    comparisons = compare_sequence(
        pitches,
        detected,
        transpose
    )

    lines = [
        describe_summary(summarise(comparisons))
    ]

    # If the whole performance sits at the same distance
    # from the music, the player is probably in a different
    # range rather than playing every note wrongly.
    suggestion = suggest_transpose(comparisons)

    if suggestion is not None:

        lines.append(
            f"That was all {describe_shift(suggestion)} "
            f"the written music. Set the shift to "
            f"{transpose + suggestion} to score it there."
        )

    if transpose != 0:
        lines.append(
            f"Scored {describe_shift(transpose)} "
            f"the written music."
        )

    lines.append("")

    for comparison in comparisons:
        lines.append(
            describe_comparison(comparison)
        )

    return (
        "\n".join(lines),
        make_tuning_plot(comparisons)
    )


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