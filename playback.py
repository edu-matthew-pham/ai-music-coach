# playback.py

import math


NOTE_SEMITONES = {
    "C": 0,
    "C#": 1,
    "Db": 1,
    "D": 2,
    "D#": 3,
    "Eb": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "Gb": 6,
    "G": 7,
    "G#": 8,
    "Ab": 8,
    "A": 9,
    "A#": 10,
    "Bb": 10,
    "B": 11
}


def note_to_frequency(note):
    """
    Convert a note such as C4, F#4 or Bb3 into a frequency.

    A4 is MIDI note 69 and has a frequency of 440 Hz.
    Each semitone changes frequency by the twelfth root of 2.
    """

    octave = int(note[-1])
    pitch = note[:-1]

    semitone = NOTE_SEMITONES[pitch]

    midi_number = (octave + 1) * 12 + semitone

    frequency = 440 * (2 ** ((midi_number - 69) / 12))

    return frequency


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