import pytest

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


def test_harmony_respects_a_key_change():
    """
    Each note harmonises against whichever key was actually
    in force at its own beat - a piece opening in G and
    modulating to Ab partway through harmonises its first
    notes in G and everything from the change onward in Ab,
    not one key for the whole line.
    """

    melody = ["Ab4", "Bb4", "C5", "Db5", "Eb5"]
    durations = [1.0, 1.0, 1.0, 1.0, 1.0]

    changed = make_harmony(
        melody, durations, key=[(0.0, "G"), (0.5, "Ab")]
    )

    # Piecing the same melody together from two single-key
    # calls, split at the same boundary, must give exactly
    # the same answer - the timeline is not a different
    # mechanism from calling make_harmony twice, it is the
    # same lookup automated.
    first_in_g = make_harmony(melody[:1], durations[:1], key="G")
    rest_in_ab = make_harmony(melody[1:], durations[1:], key="Ab")

    assert changed == first_in_g + rest_in_ab


def test_harmony_with_no_durations_assumes_one_beat_each():
    """
    Regression pin for the common case: a caller that never
    knew about key changes and never passed durations (every
    caller before this format existed) must still work
    exactly as before.
    """

    melody = ["C4", "C4", "G4", "G4", "A4"]

    assert make_harmony(melody, key="C") == [
        "A3", "A3", "E4", "E4", "F4"
    ]


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


def test_a_note_outside_the_key_is_harmonised_anyway():
    """
    Music borrows notes from outside its key constantly.
    Refusing to harmonise a whole piece over one passing
    sharp would be useless, so such a note is treated as
    the nearest note in the scale.
    """

    from harmony import make_harmony

    # G sharp does not belong to D major.
    harmony = make_harmony(["F#4", "G#4", "A4"], key="D")

    assert len(harmony) == 3

    for note in harmony:
        assert note != "R"


def test_notes_outside_the_key_are_named():
    from harmony import notes_outside

    assert notes_outside(
        ["F#4", "G#4", "A4"], key="D"
    ) == ["G#4"]

    assert notes_outside(["D4", "F#4", "A4"], key="D") == []


def test_notes_outside_respects_a_key_change():
    """
    Each note is checked against whichever key was actually
    in force at its own beat, not one key for the whole
    piece: F# fits D but not Eb, and Bb fits Eb but not D -
    a piece opening in D and modulating to Eb correctly
    finds nothing outside either half, where checking the
    whole piece against just D would wrongly flag the Bb.
    """

    from harmony import notes_outside

    pitches = ["F#4", "F#4", "Bb4", "Bb4"]
    durations = [1.0, 1.0, 1.0, 1.0]

    assert notes_outside(pitches, durations, key="D") == ["Bb4"]

    assert notes_outside(
        pitches, durations, key=[(0.0, "D"), (2.0, "Eb")]
    ) == []


def test_a_chromatic_line_still_harmonises():
    from harmony import make_harmony

    harmony = make_harmony(
        ["C4", "C#4", "D4", "D#4", "E4"],
        key="C"
    )

    assert len(harmony) == 5


def test_every_key_is_offered_by_both_its_names():
    """
    A key signature belongs to a major key and its
    relative minor equally, and a singer working from a
    minor piece should not have to know which major to
    ask for.
    """

    from harmony import key_choices, MAJOR_SCALES

    choices = key_choices()

    assert len(choices) == len(MAJOR_SCALES)

    for label, value in choices:

        assert value in MAJOR_SCALES
        assert "major" in label
        assert "minor" in label

        # The value the rest of the app receives is the
        # major key, whatever the label says.
        assert label.startswith(value)


def test_relative_minors_are_a_third_below():
    """
    The relative minor sits three semitones below its
    major, sharing all seven notes.
    """

    from harmony import RELATIVE_MINORS
    from notes import note_to_midi

    for major, minor in RELATIVE_MINORS.items():

        distance = (
            note_to_midi(major + "4")
            - note_to_midi(minor + "4")
        ) % 12

        assert distance == 3, f"{major} and {minor}"


# Multi-key: the key box's own timeline syntax. Beats, not
# bars, since a Piece has no bars of its own outside a
# chart - checked directly (piece.py's beats_per_bar only
# ever appears inside chart_between, read off the chart)
# before committing to the grammar.

def test_a_single_key_round_trips_unchanged():
    from harmony import read_key, format_key

    assert read_key("G") == [(0.0, "G")]
    assert format_key(read_key("G")) == "G"


def test_a_key_change_round_trips_exactly():
    from harmony import read_key, format_key

    changes = read_key("G, Ab from beat 156")

    assert changes == [(0.0, "G"), (156.0, "Ab")]
    assert format_key(changes) == "G, Ab from beat 156"


def test_several_key_changes_round_trip():
    from harmony import read_key, format_key

    text = "C, G from beat 16, D from beat 40"

    assert format_key(read_key(text)) == text


def test_an_empty_key_box_is_an_error():
    from harmony import read_key, KeyError_

    with pytest.raises(KeyError_, match="Choose a key"):
        read_key("")


def test_an_unknown_key_name_is_an_error():
    from harmony import read_key, KeyError_

    with pytest.raises(KeyError_, match="not a key"):
        read_key("Z")

    with pytest.raises(KeyError_, match="not a key"):
        read_key("G, Z from beat 16")


def test_key_changes_must_arrive_in_order():
    from harmony import read_key, KeyError_

    with pytest.raises(KeyError_, match="later than"):
        read_key("G, Ab from beat 16, D from beat 10")

    with pytest.raises(KeyError_, match="later than"):
        read_key("G, Ab from beat 16, D from beat 16")


def test_the_opening_key_cannot_have_a_from_clause():
    from harmony import read_key, KeyError_

    with pytest.raises(KeyError_, match="no 'from beat'"):
        read_key("G from beat 0")


def test_a_later_key_must_state_its_own_beat():
    from harmony import read_key, KeyError_

    with pytest.raises(KeyError_, match="from beat"):
        read_key("G, Ab")