# harmony.py

from notes import NOTE_SEMITONES, note_to_midi, is_rest


MAJOR_SCALES = {
    "C": ["C", "D", "E", "F", "G", "A", "B"],
    "G": ["G", "A", "B", "C", "D", "E", "F#"],
    "D": ["D", "E", "F#", "G", "A", "B", "C#"],
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


def move_in_scale(note, key="C", steps=-2):
    """
    Move a note through a major scale.

    steps=-2 means move down two scale positions,
    producing a third below.
    """

    scale_notes = build_scale_notes(key)

    note_midi = note_to_midi(note)

    current_position = None

    for i in range(len(scale_notes)):
        midi_number, note_name = scale_notes[i]

        if midi_number == note_midi:
            current_position = i
            break

    if current_position is None:
        raise ValueError(
            f"{note} is not in the key of {key} major."
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