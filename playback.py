# playback.py

import math

from notes import note_to_frequency


# How many beats of clicks are played before the music, so
# a player knows when to come in. Written as beats rather
# than clicks so that time signatures can change it later.
COUNT_IN_BEATS = 4

# The click itself: a short, high tick. High enough not to
# be mistaken for a note, short enough not to cover one.
# At extreme tempos a fixed length would outgrow the beat,
# so it is capped at a tenth of a beat.
CLICK_FREQUENCY = 1500
CLICK_SECONDS = 0.03
CLICK_SHARE_OF_BEAT = 0.1


def make_click(bpm=120, sample_rate=8000, loud=1.0):
    """
    One metronome click filling one beat.

    The click sounds at the start, and the rest of the beat
    is silence.
    """

    seconds_per_beat = 60 / bpm

    click_seconds = min(
        CLICK_SECONDS,
        seconds_per_beat * CLICK_SHARE_OF_BEAT
    )

    click_samples = int(click_seconds * sample_rate)
    beat_samples = int(seconds_per_beat * sample_rate)

    sound = []

    for sample_number in range(click_samples):
        time = sample_number / sample_rate

        # Fade the click out so it ticks rather than beeps.
        fade = 1 - (sample_number / click_samples)

        value = math.sin(
            2 * math.pi * CLICK_FREQUENCY * time
        )

        sound.append(value * fade * loud)

    for sample_number in range(beat_samples - click_samples):
        sound.append(0)

    return sound


def make_count_in(bpm=120, sample_rate=8000):
    """
    The clicks played before the music starts.
    """

    sound = []

    for beat in range(COUNT_IN_BEATS):
        sound.extend(
            make_click(bpm, sample_rate)
        )

    return sound


def add_metronome(sound, total_beats, bpm=120, sample_rate=8000):
    """
    Lay quiet clicks under an existing piece of music.

    The clicks are softer than the count-in, so they keep
    time without competing with the notes.
    """

    combined = list(sound)

    seconds_per_beat = 60 / bpm

    for beat in range(int(total_beats)):

        start = int(
            beat * seconds_per_beat * sample_rate
        )

        click = make_click(
            bpm,
            sample_rate,
            loud=0.3
        )

        for offset in range(len(click)):

            position = start + offset

            if position >= len(combined):
                break

            combined[position] += click[offset]

    return combined


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