# notes.py

"""
Shared musical note conversions.

Every other module gets its note names, MIDI numbers and
frequencies from here, so there is only one place where
the twelve semitones are ever written down.
"""


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


def split_note(note):
    """
    Split a note such as C4, F#4 or Bb3 into its
    pitch name and its octave number.
    """

    pitch = note[:-1]
    octave = int(note[-1])

    if pitch not in NOTE_SEMITONES:
        raise ValueError(
            f"{note} is not a note name I understand."
        )

    return pitch, octave


def note_to_midi(note):
    """
    Convert a note such as C4 or F#4 into a MIDI number.

    C4 is MIDI note 60.
    """

    pitch, octave = split_note(note)

    semitone = NOTE_SEMITONES[pitch]

    return (octave + 1) * 12 + semitone


def midi_to_frequency(midi_number):
    """
    Convert a MIDI number into a frequency in hertz.

    A4 is MIDI note 69 and has a frequency of 440 Hz.
    Each semitone changes frequency by the twelfth root of 2.
    """

    return 440 * (2 ** ((midi_number - 69) / 12))


def note_to_frequency(note):
    """
    Convert a note such as C4, F#4 or Bb3 into a frequency.
    """

    return midi_to_frequency(
        note_to_midi(note)
    )
