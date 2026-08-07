import pytest

from pitch_detector import Pitch
from notes import note_to_midi, midi_to_frequency
from compare import (
    compare_note,
    compare_sequence,
    summarise
)


def played(note, cents=0.0):
    """
    Build a Pitch as if this note had been played, without
    going anywhere near real audio.

    cents shifts the performance away from that note, so
    played("C4", 70) is seventy cents above middle C.
    """

    midi = note_to_midi(note) + cents / 100

    # The name and cents a detector would report: these are
    # measured from the nearest note, not from any target.
    nearest = round(midi)

    from notes import midi_to_note

    return Pitch(
        frequency=midi_to_frequency(midi),
        midi=midi,
        note=midi_to_note(midi),
        cents=(midi - nearest) * 100
    )


def test_perfect_note():
    result = compare_note("C4", played("C4"))

    assert result.target == "C4"
    assert result.heard == "C4"
    assert result.cents_from_target == pytest.approx(0)
    assert result.is_target_note
    assert result.was_detected


def test_slightly_sharp_is_still_the_target_note():
    """
    Forty cents sharp is still nearer C4 than C#4, so the
    player is on the right note and just needs to come down.
    """

    result = compare_note("C4", played("C4", 40))

    assert result.heard == "C4"
    assert result.cents_from_target == pytest.approx(40)
    assert result.is_target_note


def test_badly_sharp_is_named_as_the_neighbour():
    """
    Seventy cents sharp of C4 is nearer C#4, so that is what
    a listener would hear, but the distance from the target
    is still reported in full.
    """

    result = compare_note("C4", played("C4", 70))

    assert result.heard == "C#4"
    assert result.heard_cents == pytest.approx(-30)
    assert result.cents_from_target == pytest.approx(70)
    assert not result.is_target_note


def test_flat_notes_are_negative():
    result = compare_note("C4", played("C4", -35))

    assert result.cents_from_target == pytest.approx(-35)
    assert result.is_target_note


def test_distance_is_not_limited_to_a_semitone():
    """
    A note an octave high is reported as an octave high,
    not folded back into the nearest semitone.
    """

    result = compare_note("C4", played("C5"))

    assert result.heard == "C5"
    assert result.cents_from_target == pytest.approx(1200)
    assert not result.is_target_note


def test_undetected_note():
    result = compare_note("C4", None)

    assert result.target == "C4"
    assert result.heard is None
    assert result.cents_from_target is None
    assert not result.was_detected
    assert not result.is_target_note


def test_compare_sequence():
    targets = ["C4", "E4", "G4"]

    pitches = [
        played("C4"),
        played("E4", 25),
        None
    ]

    results = compare_sequence(targets, pitches)

    assert len(results) == 3
    assert results[0].is_target_note
    assert results[1].cents_from_target == pytest.approx(25)
    assert not results[2].was_detected


def test_compare_sequence_pads_a_short_performance():
    """
    A performance that stops early still reports every note
    that was asked for.
    """

    targets = ["C4", "E4", "G4"]

    results = compare_sequence(targets, [played("C4")])

    assert len(results) == 3
    assert results[0].was_detected
    assert not results[1].was_detected
    assert not results[2].was_detected


def test_summarise():
    targets = ["C4", "E4", "G4", "B4"]

    pitches = [
        played("C4", 10),
        played("E4", -20),
        played("G4", 70),
        None
    ]

    summary = summarise(
        compare_sequence(targets, pitches)
    )

    assert summary["total"] == 4
    assert summary["detected"] == 3
    assert summary["on_target"] == 2

    # Average of 10, 20 and 70.
    assert summary["average_cents_off"] == pytest.approx(
        100 / 3
    )


def test_summarise_with_nothing_detected():
    summary = summarise(
        compare_sequence(["C4", "E4"], [None, None])
    )

    assert summary["detected"] == 0
    assert summary["on_target"] == 0
    assert summary["average_cents_off"] is None


def test_transpose_shifts_the_target():
    """
    Someone singing an octave below is playing the right
    note in their own range, once the music is shifted.
    """

    result = compare_note("C4", played("C3"), transpose=-12)

    assert result.target == "C4"
    assert result.expected == "C3"
    assert result.cents_from_target == pytest.approx(0)
    assert result.is_target_note


def test_transpose_of_zero_changes_nothing():
    result = compare_note("C4", played("C4"), transpose=0)

    assert result.expected == "C4"
    assert result.is_target_note


def test_suggests_an_octave_when_everything_is_low():
    targets = ["C4", "E4", "G4"]

    performance = [
        played("C3", 10),
        played("E3", -20),
        played("G3", 5)
    ]

    from compare import suggest_transpose

    assert suggest_transpose(
        compare_sequence(targets, performance)
    ) == -12


def test_suggests_nothing_when_the_notes_are_right():
    from compare import suggest_transpose

    targets = ["C4", "E4"]

    performance = [played("C4", 8), played("E4", -12)]

    assert suggest_transpose(
        compare_sequence(targets, performance)
    ) is None


def test_suggests_nothing_when_mistakes_disagree():
    """
    A performance that is wrong in different ways each time
    is not shifted, it is just wrong.
    """

    from compare import suggest_transpose

    targets = ["C4", "E4", "G4"]

    performance = [
        played("C3"),
        played("E4"),
        played("G5")
    ]

    assert suggest_transpose(
        compare_sequence(targets, performance)
    ) is None


def test_suggests_nothing_from_a_single_note():
    from compare import suggest_transpose

    assert suggest_transpose(
        compare_sequence(["C4"], [played("C3")])
    ) is None