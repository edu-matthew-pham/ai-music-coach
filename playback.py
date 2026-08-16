# playback.py

import math

from notes import note_to_frequency, is_rest, midi_to_frequency


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

# The first beat of a bar gets a higher, louder tick, the
# way a metronome marks the downbeat. Without it a run of
# clicks says how fast but not where, and a singer counting
# a phrase in has nothing to count from.
DOWNBEAT_FREQUENCY = 2200
DOWNBEAT_LOUDER = 1.8


def make_click(bpm=120, sample_rate=8000, loud=1.0,
               frequency=CLICK_FREQUENCY):
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
            2 * math.pi * frequency * time
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


def add_metronome(sound, total_beats, bpm=120, sample_rate=8000,
                  bars=None):
    """
    Lay quiet clicks under an existing piece of music.

    The clicks are softer than the count-in, so they keep
    time without competing with the notes.

    Given the bars, the first beat of each is marked with a
    higher, louder tick. That is what turns a stream of
    clicks into a bar you can count: the same information a
    conductor's downbeat carries.
    """

    combined = list(sound)

    seconds_per_beat = 60 / bpm

    downbeats = set()

    if bars:
        for bar_start, bar_length in bars:
            downbeats.add(round(bar_start, 3))

    for beat in range(int(total_beats)):

        start = int(
            beat * seconds_per_beat * sample_rate
        )

        on_a_downbeat = round(float(beat), 3) in downbeats

        click = make_click(
            bpm,
            sample_rate,
            loud=0.3 * (DOWNBEAT_LOUDER if on_a_downbeat else 1),
            frequency=(
                DOWNBEAT_FREQUENCY if on_a_downbeat
                else CLICK_FREQUENCY
            )
        )

        for offset in range(len(click)):

            position = start + offset

            if position >= len(combined):
                break

            combined[position] += click[offset]

    return combined


# Where the accompaniment sits. Chords in the singer's own
# octave muddy the line they are meant to support, so they
# are voiced below it, in a guitar's range.
CHORD_LOWEST_MIDI = 40
CHORD_HIGHEST_MIDI = 64

# A strummed chord does not sound all at once: the pick
# crosses the strings, and that small stagger is most of
# what makes it sound plucked rather than pressed.
STRUM_SECONDS = 0.018

# A string still ringing when the chord changes has to be
# damped rather than cut, or the waveform jumps and the
# change arrives with a click on it. This is a hand landing
# on the strings: brief, and the reason a chord change
# sounds like a chord change rather than a fault.
CHORD_RELEASE_SECONDS = 0.02


# How a plucked string decays, and the harmonics that give
# it a body rather than the hollow tone of a bare sine.
PLUCK_DECAY = 1.1
PLUCK_HARMONICS = [
    (1, 1.0),
    (2, 0.4),
    (3, 0.22),
    (4, 0.12),
    (5, 0.06)
]


def make_pluck(frequency, seconds, sample_rate=8000, loud=1.0):
    """
    One plucked string.

    A sine alone sounds like a test tone. A string sounds
    like a string because it starts loud and dies away, and
    because it sounds several harmonics at once, quieter
    the higher they go.
    """

    samples = int(seconds * sample_rate)

    sound = []

    for sample_number in range(samples):

        time = sample_number / sample_rate

        # Dying away is what makes it a pluck rather than
        # a held note.
        fade = math.exp(-PLUCK_DECAY * time)

        value = 0.0

        for multiple, strength in PLUCK_HARMONICS:

            value += strength * math.sin(
                2 * math.pi * frequency * multiple * time
            )

        sound.append(loud * fade * value / 2.2)

    return sound


def voice_chord(semitones):
    """
    Choose which notes of a chord to actually sound.

    A chord is a set of pitch classes, not pitches. Voicing
    it means picking an octave for each, low enough to sit
    under a singer and spread enough not to sound muddy.
    """

    voiced = []

    previous = CHORD_LOWEST_MIDI

    for semitone in semitones:

        # Take the next note of the chord above the last
        # one, so the chord opens upward rather than
        # bunching at the bottom.
        midi_number = previous + (
            (semitone - previous) % 12
        )

        if midi_number == previous:
            midi_number += 12

        if midi_number > CHORD_HIGHEST_MIDI:
            break

        voiced.append(midi_number)

        previous = midi_number

    return voiced


def make_chord(semitones, beats, bpm=120, sample_rate=8000,
               loud=0.8):
    """
    One strummed chord, filling the time given.

    The strings are struck a moment apart, low to high, as
    a hand crossing them would, and damped at the end so
    that a chord still ringing when the next arrives stops
    cleanly instead of clicking.
    """

    seconds_per_beat = 60 / bpm

    total_seconds = beats * seconds_per_beat

    samples = int(total_seconds * sample_rate)

    sound = [0.0] * samples

    voiced = voice_chord(semitones)

    for position in range(len(voiced)):

        frequency = midi_to_frequency(voiced[position])

        start = int(
            position * STRUM_SECONDS * sample_rate
        )

        string = make_pluck(
            frequency,
            total_seconds,
            sample_rate,
            loud=loud
        )

        for offset in range(len(string)):

            index = start + offset

            if index >= samples:
                break

            sound[index] += string[offset]

    # Damp whatever is still ringing at the end.
    release_samples = min(
        int(CHORD_RELEASE_SECONDS * sample_rate),
        len(sound)
    )

    for offset in range(release_samples):

        index = len(sound) - release_samples + offset

        fade = 1 - (offset / release_samples)

        sound[index] *= fade

    return sound


def make_accompaniment(chords, bars, total_beats, bpm=120,
                       sample_rate=8000):
    """
    A chord part to sing over.

    The chord sounds when it arrives and again on each bar
    line it lasts through, provided it was already sounding
    a full beat or more before that bar line. Struck only
    on the changes, a chord held for four bars would ring
    once and then leave the singer with nothing underneath
    at exactly the point a long note is hardest to hold.
    Struck every bar, the harmony and the beat both stay
    present.

    The one-beat guard exists for a chord that arrives just
    before a bar line - a syncopated push onto the "and" of
    the last beat, say. Without it, the chord is struck once
    on its own true arrival and then struck again almost
    immediately by the very next bar line, audibly doubling
    a note that was never meant to repeat: real evidence
    against real recordings, not a guess (BUILDNOTES.md, the
    stage-1 half-beat session). A chord that has genuinely
    been sounding for a while still gets reinforced exactly
    as before; only an arrival too recent to need reinforcing
    is skipped.
    """

    seconds_per_beat = 60 / bpm

    samples = int(total_beats * seconds_per_beat * sample_rate)

    sound = [0.0] * samples

    if not chords:
        return sound

    bar_starts = [start for start, length in bars or []]

    for chord_start, chord_length, semitones in chords:

        chord_end = chord_start + chord_length

        # Where this chord is struck: when it arrives, and
        # on any bar line before it ends that the chord had
        # already been sounding for at least a beat by.
        moments = [chord_start]

        for bar_start in bar_starts:
            if (
                chord_start < bar_start < chord_end
                and bar_start - chord_start >= 1.0
            ):
                moments.append(bar_start)

        for position in range(len(moments)):

            moment = moments[position]

            if position + 1 < len(moments):
                ring_until = moments[position + 1]

            else:
                ring_until = chord_end

            struck = make_chord(
                semitones,
                ring_until - moment,
                bpm,
                sample_rate
            )

            start = int(moment * seconds_per_beat * sample_rate)

            for offset in range(len(struck)):

                index = start + offset

                if index >= samples:
                    break

                sound[index] += struck[offset]

    return sound


def make_note(pitch, beats, bpm=120, sample_rate=8000):
    """
    Turn one musical note into a list of sound values.

    A rest is silence of the same length, so a line of
    music keeps its shape whether or not it is sounding.

    Plain sine, on purpose. A richer version (several
    harmonics, a sustain envelope, tanh soft-clipping to
    stay safe without a fixed divisor) was built and pulled
    back out: real, and it did sound better, but it turned
    out to cost about 4.5x the compute on its own, on top of
    another ~5.5x from the sample-rate increase tried
    alongside it - together a real, measured 25x slower
    Generate Playback (0.9s to 22.5s on the whole Wellerman
    fixture), which is too much to spend on this specific
    lever. The cost lives in this being a plain per-sample
    Python loop, not in the harmonic idea itself - a
    numpy-vectorised version of the same richness would
    likely have recovered most of that, unexplored so far.
    Real sampled instrument audio is the better long-term
    answer regardless (see the parked-proposal note); this
    was the cheap synthesis-only attempt at closing the gap
    before that, and it wasn't cheap enough.
    """

    sound = []

    seconds_per_beat = 60 / bpm
    duration_seconds = beats * seconds_per_beat

    if is_rest(pitch):

        return [0.0] * int(
            duration_seconds * sample_rate
        )

    frequency = note_to_frequency(pitch)

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

    Padded or trimmed to the exact same total length every
    other layer computes directly from the piece's whole
    duration (make_accompaniment, add_metronome) - summing
    each note's own separately-rounded length instead drifts
    from that single calculation by up to a sample per note,
    which stayed invisible at a coarser sample rate and
    became a real mismatch between layers once it did not
    (caught directly, not assumed: the Wellerman fixture's
    Chords layer landed 152 samples ahead of Melody's own at
    44100Hz, the two having always been computed two
    different ways and only coincidentally agreeing before).
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

    seconds_per_beat = 60 / bpm
    total_samples = int(
        sum(durations) * seconds_per_beat * sample_rate
    )

    if len(melody) < total_samples:
        melody.extend([0.0] * (total_samples - len(melody)))

    elif len(melody) > total_samples:
        melody = melody[:total_samples]

    return sample_rate, melody


def keep_in_range(sound, ceiling=0.95):
    """
    Quieten a mix that would otherwise clip.

    Layers add up: melody, harmony, chords and clicks
    together can pass what the speaker can play, and the
    result is not loud but broken. Scaling the whole mix
    down keeps the balance between the parts.
    """

    loudest = max(
        (abs(value) for value in sound),
        default=0.0
    )

    if loudest <= ceiling:
        return sound

    scale = ceiling / loudest

    return [value * scale for value in sound]


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