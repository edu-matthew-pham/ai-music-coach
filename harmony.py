# harmony.py

from notes import NOTE_SEMITONES, note_to_midi, is_rest


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