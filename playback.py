# playback.py

import math

from notes import note_to_frequency


def make_note(pitch, beats, bpm=120, sample_rate=8000):
    """
    Turn one musical note into a list of sound values.
    """

    sound = []

    frequency = note_to_frequency(pitch)

    seconds_per_beat = 60 / bpm
    duration_seconds = beats * seconds_per_beat

    # Play sound for 90% of the note.
    sound_seconds = duration_seconds * 0.9
    number_of_sound_samples = int(sound_seconds * sample_rate)

    for sample_number in range(number_of_sound_samples):
        time = sample_number / sample_rate

        value = math.sin(
            2 * math.pi * frequency * time
        )

        sound.append(value)

    # Leave a small gap between notes.
    silence_seconds = duration_seconds * 0.1
    number_of_silence_samples = int(
        silence_seconds * sample_rate
    )

    for sample_number in range(number_of_silence_samples):
        sound.append(0)

    return sound


def make_melody(
    pitches,
    durations,
    bpm=120,
    sample_rate=8000
):
    """
    Join a sequence of notes together to make a melody.
    """

    melody = []

    for i in range(len(pitches)):
        note_sound = make_note(
            pitches[i],
            durations[i],
            bpm,
            sample_rate
        )

        melody.extend(note_sound)

    return sample_rate, melody


def mix_tracks(track_1, track_2):
    """
    Mix two tracks by combining matching sound samples.

    Dividing by 2 prevents the combined waveform
    from becoming twice as large.
    """

    mixed_track = []

    number_of_samples = min(
        len(track_1),
        len(track_2)
    )

    for i in range(number_of_samples):

        mixed_value = (
            track_1[i] + track_2[i]
        ) / 2

        mixed_track.append(mixed_value)

    return mixed_track


def make_layered_melody(
    melody_pitches,
    harmony_pitches,
    durations,
    bpm=120,
    sample_rate=8000
):
    """
    Generate a melody and harmony, then play them together.
    """

    sample_rate, melody = make_melody(
        melody_pitches,
        durations,
        bpm,
        sample_rate
    )

    sample_rate, harmony = make_melody(
        harmony_pitches,
        durations,
        bpm,
        sample_rate
    )

    combined = mix_tracks(
        melody,
        harmony
    )

    return sample_rate, combined