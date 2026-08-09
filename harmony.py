# harmony.py

from notes import (
    NOTE_SEMITONES,
    note_to_midi,
    midi_to_note,
    is_rest
)


# Every major key, each spelled the way its key signature
# spells it: sharp keys in sharps, flat keys in flats. F
# sharp major genuinely contains an E sharp, which is the
# same sound as F but not the same note name.
MAJOR_SCALES = {
    "C": ["C", "D", "E", "F", "G", "A", "B"],
    "G": ["G", "A", "B", "C", "D", "E", "F#"],
    "D": ["D", "E", "F#", "G", "A", "B", "C#"],
    "A": ["A", "B", "C#", "D", "E", "F#", "G#"],
    "E": ["E", "F#", "G#", "A", "B", "C#", "D#"],
    "B": ["B", "C#", "D#", "E", "F#", "G#", "A#"],
    "F#": ["F#", "G#", "A#", "B", "C#", "D#", "E#"],
    "Db": ["Db", "Eb", "F", "Gb", "Ab", "Bb", "C"],
    "Ab": ["Ab", "Bb", "C", "Db", "Eb", "F", "G"],
    "Eb": ["Eb", "F", "G", "Ab", "Bb", "C", "D"],
    "Bb": ["Bb", "C", "D", "Eb", "F", "G", "A"],
    "F": ["F", "G", "A", "Bb", "C", "D", "E"]
}


# The minor key that shares each major key's notes. A
# piece in D minor uses the notes of F major, which is why
# the app can harmonise minor music without knowing
# anything about minor keys: the scale is the same seven
# notes started in a different place.
RELATIVE_MINORS = {
    "C": "A",
    "G": "E",
    "D": "B",
    "A": "F#",
    "E": "C#",
    "B": "G#",
    "F#": "D#",
    "Db": "Bb",
    "Ab": "F",
    "Eb": "C",
    "Bb": "G",
    "F": "D"
}


def key_choices():
    """
    How the keys are offered, as (label, value) pairs.

    Each key is named both ways, since a key signature
    belongs to a major key and its relative minor equally,
    and a singer working from a minor piece should not
    have to know which major to ask for.
    """

    return [
        (f"{major} major / {RELATIVE_MINORS[major]} minor", major)
        for major in MAJOR_SCALES
    ]


def build_scale_notes(key, lowest=24, highest=108):
    """
    Build all notes belonging to a major key across
    a useful range of octaves.
    """

    scale = MAJOR_SCALES[key]

    # Match each scale pitch name to its semitone.
    scale_by_semitone = {}

    for pitch in scale:
        semitone = NOTE_SEMITONES[pitch]
        scale_by_semitone[semitone] = pitch

    notes = []

    for midi_number in range(lowest, highest + 1):

        semitone = midi_number % 12

        if semitone in scale_by_semitone:

            pitch = scale_by_semitone[semitone]
            octave = (midi_number // 12) - 1

            notes.append(
                (midi_number, pitch + str(octave))
            )

    return notes


def keys_containing(pitches):
    """
    Which of the supported keys contain every one of
    these notes.

    Used to suggest a workable key when the chosen one
    does not fit the music.
    """

    workable = []

    for key in MAJOR_SCALES:

        scale_semitones = set()

        for pitch in MAJOR_SCALES[key]:
            scale_semitones.add(NOTE_SEMITONES[pitch])

        fits = True

        for pitch in pitches:
            if is_rest(pitch):
                continue
            if note_to_midi(pitch) % 12 not in scale_semitones:
                fits = False
                break

        if fits:
            workable.append(key)

    return workable


def nearest_position(scale_notes, note_midi):
    """
    Where a note sits in a scale, or where it sits closest.

    Music borrows notes from outside its key all the time:
    a passing sharp, a blue seventh. Rather than refuse to
    harmonise the whole piece over one of them, such a note
    is treated as the nearest scale note. The harmony keeps
    moving in parallel and one interval comes out slightly
    unusual, which is what a singer improvising a line
    would do anyway.
    """

    best = None
    best_distance = None

    for position in range(len(scale_notes)):

        midi_number, note_name = scale_notes[position]

        distance = abs(midi_number - note_midi)

        if best_distance is None or distance < best_distance:
            best = position
            best_distance = distance

    return best


def notes_outside(pitches, key):
    """
    The notes of this music that the key does not contain.

    They can still be harmonised, at the nearest note in
    the scale, but they are worth naming so nobody is
    surprised by the interval that results.
    """

    scale_semitones = {
        NOTE_SEMITONES[pitch]
        for pitch in MAJOR_SCALES[key]
    }

    outside = []

    for pitch in pitches:

        if is_rest(pitch):
            continue

        if note_to_midi(pitch) % 12 not in scale_semitones:
            if pitch not in outside:
                outside.append(pitch)

    return outside


def move_in_scale(note, key="C", steps=-2):
    """
    Move a note through a major scale.

    steps=-2 means move down two scale positions,
    producing a third below.
    """

    scale_notes = build_scale_notes(key)

    note_midi = note_to_midi(note)

    current_position = nearest_position(
        scale_notes,
        note_midi
    )

    if current_position is None:
        raise ValueError(
            "That key has no notes to harmonise with."
        )

    new_position = current_position + steps

    if new_position < 0 or new_position >= len(scale_notes):
        raise ValueError(
            "Harmony note is outside the supported range."
        )

    new_midi, new_note = scale_notes[new_position]

    return new_note


def make_harmony(pitches, key="C", steps=-2):
    """
    Create a harmony line for a sequence of pitches.

    Default:
    a third below in the selected major key.
    """

    harmony = []

    for pitch in pitches:

        # A silence in the melody is a silence in the
        # harmony: both parts breathe together.
        if is_rest(pitch):
            harmony.append(pitch)
            continue

        harmony_note = move_in_scale(
            pitch,
            key,
            steps
        )

        harmony.append(harmony_note)

    return harmony


def is_chord_tone(midi_number, chord_tones):
    """
    Whether a note belongs to the chord underneath it.
    """

    return midi_number % 12 in chord_tones


def nearest_chord_tone_below(midi_number, chord_tones):
    """
    The closest chord tone strictly below a note.

    Where a harmony voice sings when it draws from the
    chord rather than from parallel motion.
    """

    candidate = midi_number - 1

    while candidate > midi_number - 13:

        if candidate % 12 in chord_tones:
            return candidate

        candidate -= 1

    return midi_number - 12


def chord_tones_at(chords, beat):
    """
    The pitch classes of the chord sounding at a moment,
    or None when nothing is.
    """

    for start, length, tones in chords:

        if start <= beat < start + length:
            return tones

    return None


def make_chord_harmony(
    pitches,
    durations,
    chords,
    key="C",
    steps=-2,
    style="Thirds, chord-corrected"
):
    """
    A harmony line that knows the chords.

    Two ways of choosing each note, neither more correct
    than the other - they are different sounds:

    Thirds, chord-corrected: parallel thirds as usual,
    except where the third lands outside the chord, when
    the nearest chord tone below the melody is taken
    instead. First principles: in diatonic music the third
    below a melody note usually is a chord tone, because
    triads are stacked thirds. The departures are exactly
    the moments a duet singer would bend their line to
    avoid a clash, so this is the duet sound with the sour
    moments repaired.

    Chord tones: every note drawn from the chord, nearest
    below the melody. The line follows the harmony rather
    than shadowing the tune, which is the sound of an
    arranged inner voice.

    A third way, holding a note while it still fits the
    chord, was tried and taken out again: on a short
    phrase over changing chords it is forced to move
    almost at once, and what it produces is barely
    distinguishable from chord tones. Holding common tones
    is only the first rule of voice leading, and a line
    with no shape of its own is not really an independent
    voice. Worth returning to with the rest of the rules,
    and with music long enough for it to matter.

    Notes with no chord under them fall back to the
    parallel third, and a melody note that is itself
    outside the chord keeps its parallel third too, since
    correcting an intentional dissonance would flatten
    what the composer wrote.
    """

    harmony = []

    beat = 0.0

    previous = None

    for position in range(len(pitches)):

        pitch = pitches[position]

        length = durations[position]

        if is_rest(pitch):
            harmony.append(pitch)
            beat += length
            continue

        melody_midi = note_to_midi(pitch)

        tones = chord_tones_at(chords, beat)

        parallel = note_to_midi(
            move_in_scale(pitch, key, steps)
        )

        if tones is None:
            chosen = parallel

        elif style == "Chord tones":
            chosen = nearest_chord_tone_below(
                melody_midi, tones
            )

        else:

            # Thirds, corrected at the clashes. A melody
            # note outside its own chord is left with its
            # parallel third: the dissonance is the
            # composer's, not ours to repair.
            melody_in_chord = is_chord_tone(
                melody_midi, tones
            )

            if melody_in_chord and not is_chord_tone(
                parallel, tones
            ):
                chosen = nearest_chord_tone_below(
                    melody_midi, tones
                )

            else:
                chosen = parallel

        harmony.append(midi_to_note(chosen))

        previous = chosen

        beat += length

    return harmony


# Where a bass line sings. Low enough to be heard as the
# bottom of the harmony rather than as a second tune, and
# inside what a bass voice can actually reach.
BASS_LOWEST_MIDI = 40
BASS_HIGHEST_MIDI = 55


def make_bass(pitches, durations, chords):
    """
    A bass line: the root of each chord, held.

    A bass part does not follow the melody at all. Where a
    harmony voice sings a note for every note of the tune,
    a bass sings one note per chord and holds it while the
    melody moves above. That is what a bass line is for:
    it says where the harmony is, which is what lets
    everyone else hear whether they are in the right place.

    Returned as one entry per melody note, since that is
    what the rest of the app reads, but consecutive notes
    over one chord are the same note repeated rather than
    a line of their own.
    """

    line = []

    beat = 0.0

    for position in range(len(pitches)):

        pitch = pitches[position]

        length = durations[position]

        if is_rest(pitch):
            line.append(pitch)
            beat += length
            continue

        tones = chord_tones_at(chords, beat)

        if tones is None:

            # Nothing to sing the root of, so the bass
            # rests rather than inventing a harmony.
            line.append("R")

        else:

            root = tones[0]

            midi_number = BASS_LOWEST_MIDI + (
                (root - BASS_LOWEST_MIDI) % 12
            )

            if midi_number > BASS_HIGHEST_MIDI:
                midi_number -= 12

            line.append(midi_to_note(midi_number))

        beat += length

    return line