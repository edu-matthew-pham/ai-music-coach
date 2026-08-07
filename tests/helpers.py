"""
Small builders shared by the tests.
"""

from notes import note_to_midi, midi_to_note, midi_to_frequency
from pitch_detector import Pitch


def fake_played(note, cents=0.0):
    """
    Build a Pitch as if this note had been played, without
    going anywhere near real audio.
    """

    midi = note_to_midi(note) + cents / 100

    return Pitch(
        frequency=midi_to_frequency(midi),
        midi=midi,
        note=midi_to_note(midi),
        cents=(midi - round(midi)) * 100
    )
