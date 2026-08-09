"""
Chord charts.

A chart is a grid: bars of beat slots saying what sounds
underneath. The melody is not a grid, and does not have to
agree with it note for note - a chord spans many notes, a
syncopated melody crosses the bar lines. The two only have
to last the same time.
"""

import pytest

from chords import (
    ChartError,
    read_chart,
    chart_beats,
    chord_at,
    chord_semitones,
    chord_root,
    split_chord,
    describe_chart
)
from music import read_chords, MusicInputError


def test_a_chord_lasts_as_long_as_its_dots():
    chords, bars = read_chart("| Dm . Bb . |")

    assert chords == [
        (0.0, 2.0, "Dm"),
        (2.0, 2.0, "Bb")
    ]


def test_a_chord_on_every_beat():
    chords, bars = read_chart("| C G Am F |")

    assert len(chords) == 4

    for start, length, name in chords:
        assert length == 1.0


def test_the_bars_declare_the_metre():
    """
    Three slots is three four and four slots is four four.
    Nothing has to be told the time signature separately.
    """

    chords, bars = read_chart("| Dm . . | F . . |")

    assert bars == [(0.0, 3.0), (3.0, 3.0)]

    assert "3 beats to the bar" in describe_chart(
        "| Dm . . | F . . |"
    )


def test_bars_may_change_length():
    chords, bars = read_chart("| C . . . | G . . |")

    assert bars == [(0.0, 4.0), (4.0, 3.0)]

    assert "changing" in describe_chart("| C . . . | G . . |")


def test_a_chart_must_begin_with_a_bar_line():
    with pytest.raises(ChartError, match="begins with a bar line"):
        read_chart("Dm . Bb .")


def test_a_chart_cannot_begin_with_a_dot():
    with pytest.raises(ChartError, match="no chord to carry on"):
        read_chart("| . Dm |")


def test_an_unknown_chord_is_reported():
    with pytest.raises(ChartError, match="not a chord this app knows"):
        read_chart("| Dwhatever . |")


def test_something_that_is_not_a_chord_at_all():
    with pytest.raises(ChartError, match="does not start with a note"):
        read_chart("| Hm . |")


def test_chord_names_split_into_root_and_quality():
    assert split_chord("Dm") == ("D", "m")
    assert split_chord("Bbmaj7") == ("Bb", "maj7")
    assert split_chord("F#m7") == ("F#", "m7")
    assert split_chord("C") == ("C", "")


def test_chord_tones():
    # D minor is D, F, A.
    assert sorted(chord_semitones("Dm")) == [2, 5, 9]

    # G7 is G, B, D, F.
    assert sorted(chord_semitones("G7")) == [2, 5, 7, 11]


def test_the_root_is_what_a_bass_line_sings():
    assert chord_root("Bb") == 10
    assert chord_root("F#m7") == 6


def test_the_chord_at_a_moment():
    chords, bars = read_chart("| Dm . Bb . |")

    assert chord_at(chords, 0.0) == "Dm"
    assert chord_at(chords, 1.9) == "Dm"
    assert chord_at(chords, 2.0) == "Bb"
    assert chord_at(chords, 99) is None


def test_a_note_takes_the_chord_it_begins_under():
    """
    A note held across a change keeps the identity it
    started with, which is what lets a suspension resolve
    rather than simply sound wrong.
    """

    chords, bars = read_chart("| Dm . Bb . |")

    # A note starting on beat one and lasting three beats
    # belongs to D minor, however far it runs.
    assert chord_at(chords, 1.0) == "Dm"


def test_the_chart_must_last_as_long_as_the_music():
    with pytest.raises(MusicInputError, match="same length"):
        read_chords("| C . . . |", [1.0, 1.0])


def test_the_mismatch_says_what_both_lengths_are():
    try:
        read_chords("| C . . . | G . . . |", [1.0, 1.0, 1.0])

    except MusicInputError as problem:
        assert "8 beats" in str(problem)
        assert "3 beats" in str(problem)
        assert "2 bars" in str(problem)


def test_chords_are_optional():
    assert read_chords("", [1.0, 1.0]) == ([], [])
    assert read_chords(None, [1.0, 1.0]) == ([], [])


def test_a_syncopated_melody_needs_no_alignment():
    """
    The chart is a grid and the melody is not. They only
    have to last the same time.
    """

    # Notes that begin off the beat and tie across the bar.
    durations = [0.5, 1.5, 2.0, 1.5, 2.5]

    chords, bars = read_chords(
        "| Dm . Bb . | F . . . |",
        durations
    )

    assert len(chords) == 3


def test_chart_beats_counts_the_whole_chart():
    assert chart_beats("| C . . . | G . . . |") == 8.0
    assert chart_beats("") == 0.0


def test_chord_symbols_are_drawn_above_the_music():
    """
    A chart belongs above the notes, as a lead sheet
    prints it.
    """

    from tuning_plot import make_performance_plot

    chords, bars = read_chart("| C . . . | F . C . |")

    figure = make_performance_plot(
        ["C4", "E4", "G4", "C5", "G4", "E4", "C4", "C4"],
        [1.0] * 8,
        120,
        None,
        chords=chords,
        bars=bars
    )

    axes = figure.axes[0]

    labels = [text.get_text() for text in axes.texts]

    assert labels.count("C") >= 2
    assert "F" in labels

    # Above the highest note, not among the boxes.
    lowest, highest = axes.get_ylim()

    for text in axes.texts:
        if text.get_text() in ("C", "F"):
            assert text.get_position()[1] > highest - 2


def test_bar_lines_are_drawn_for_every_bar():
    from tuning_plot import make_performance_plot

    chords, bars = read_chart("| C . . . | F . . . | G . . . |")

    figure = make_performance_plot(
        ["C4"] * 12,
        [1.0] * 12,
        120,
        None,
        chords=chords,
        bars=bars
    )

    axes = figure.axes[0]

    # One at the start of each bar and one at the end.
    assert len(axes.lines) >= len(bars) + 1


def test_a_picture_without_chords_is_unchanged():
    """
    Chords are optional, and music without them draws
    exactly as it did before.
    """

    from tuning_plot import make_performance_plot

    figure = make_performance_plot(
        ["C4", "E4"], [1.0, 1.0], 120, None
    )

    assert len(figure.axes[0].lines) == 0