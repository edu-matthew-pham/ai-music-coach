import pytest

from notes import (
    split_note,
    note_to_midi,
    midi_to_frequency,
    note_to_frequency
)


def test_split_note():
    assert split_note("C4") == ("C", 4)
    assert split_note("F#4") == ("F#", 4)
    assert split_note("Bb3") == ("Bb", 3)


def test_split_note_rejects_unknown_pitch():
    with pytest.raises(ValueError):
        split_note("H4")


def test_middle_c_is_midi_60():
    assert note_to_midi("C4") == 60


def test_a4_is_midi_69():
    assert note_to_midi("A4") == 69


def test_enharmonic_names_agree():
    """
    Two spellings of the same pitch must give the
    same MIDI number.
    """

    assert note_to_midi("A#4") == note_to_midi("Bb4")
    assert note_to_midi("C#4") == note_to_midi("Db4")


def test_midi_to_frequency():
    assert midi_to_frequency(69) == pytest.approx(440, abs=0.01)


def test_octave_doubles_frequency():
    """
    Going up twelve semitones should double the frequency.
    """

    assert note_to_frequency("A5") == pytest.approx(
        note_to_frequency("A4") * 2,
        abs=0.01
    )


def test_note_to_frequency_matches_known_values():
    assert note_to_frequency("A4") == pytest.approx(440, abs=0.01)
    assert note_to_frequency("C4") == pytest.approx(261.63, abs=0.01)
