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