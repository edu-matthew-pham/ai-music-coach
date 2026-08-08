from harmony import move_in_scale, make_harmony


def test_third_below_c():
    assert move_in_scale("C4", key="C") == "A3"


def test_third_below_g():
    assert move_in_scale("G4", key="C") == "E4"


def test_third_below_a():
    assert move_in_scale("A4", key="C") == "F4"


def test_harmony_sequence():
    melody = ["C4", "C4", "G4", "G4", "A4"]

    expected = ["A3", "A3", "E4", "E4", "F4"]

    assert make_harmony(melody, key="C") == expected

def test_every_major_key_is_available():
    """
    There are twelve major keys, and the app supports all
    of them: the original four were scaffolding, not a
    design.
    """

    from harmony import MAJOR_SCALES

    assert len(MAJOR_SCALES) == 12


def test_every_scale_note_parses_and_ascends():
    """
    Each scale must be seven real note names in ascending
    order, including the awkward spellings: F sharp major
    genuinely contains an E sharp.
    """

    from harmony import MAJOR_SCALES
    from notes import note_to_midi

    for key, scale in MAJOR_SCALES.items():

        semitones = [
            note_to_midi(name + "4") % 12
            for name in scale
        ]

        assert len(set(semitones)) == 7, key

        # Ascending from the tonic, wrapping at the octave.
        steps = [
            (semitones[i + 1] - semitones[i]) % 12
            for i in range(6)
        ]

        assert all(step in (1, 2) for step in steps), key


def test_harmony_works_in_a_flat_key():
    from harmony import make_harmony

    assert make_harmony(
        ["Eb4", "G4", "Bb4"], key="Eb"
    ) == ["C4", "Eb4", "G4"]