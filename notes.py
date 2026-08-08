# notes.py

"""
Shared musical note conversions.

Every other module gets its note names, MIDI numbers and
frequencies from here, so there is only one place where
the twelve semitones are ever written down.

MIDI numbers are the common language. A decimal MIDI number
carries tuning information that a note name cannot: 60.0 is
middle C exactly, while 60.4 is middle C played sharp.
"""

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


# The twelve pitch names used when a MIDI number has to be
# turned back into text. Sharps are chosen because that is
# what most detectors report, but this is only a spelling
# decision: comparison always happens on MIDI numbers.
SHARP_NAMES = [
    "C", "C#", "D", "D#", "E", "F",
    "F#", "G", "G#", "A", "A#", "B"
]


# How a silence is written in a line of music. Rests take
# a place among the notes: they have a length, they just
# have no pitch. Music without them cannot hold a phrase
# apart or leave a singer room to breathe.
REST = "R"

REST_MARKERS = {"R", "r", "-"}


def is_rest(pitch):
    """
    Whether this entry in a line of music is a silence.
    """

    return pitch in REST_MARKERS


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


def midi_to_note(midi_number):
    """
    Convert a MIDI number into a note name such as C4.

    Decimal MIDI numbers are rounded to the nearest note.
    """

    midi_number = int(round(midi_number))

    pitch = SHARP_NAMES[midi_number % 12]
    octave = (midi_number // 12) - 1

    return pitch + str(octave)


def midi_to_frequency(midi_number):
    """
    Convert a MIDI number into a frequency in hertz.

    A4 is MIDI note 69 and has a frequency of 440 Hz.
    Each semitone changes frequency by the twelfth root of 2.
    """

    return 440 * (2 ** ((midi_number - 69) / 12))


def frequency_to_midi(frequency):
    """
    Convert a frequency in hertz into a MIDI number.

    The result is a decimal, so 60.4 means slightly
    sharper than middle C.
    """

    return 69 + 12 * math.log2(frequency / 440)


def note_to_frequency(note):
    """
    Convert a note such as C4, F#4 or Bb3 into a frequency.
    """

    return midi_to_frequency(
        note_to_midi(note)
    )


def cents_from_nearest_note(midi_number):
    """
    How far a decimal MIDI number sits from the nearest note.

    One semitone is 100 cents, so the result is always
    between -50 and +50. Positive means sharp.
    """

    difference = midi_number - round(midi_number)

    return difference * 100