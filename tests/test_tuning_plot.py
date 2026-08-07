import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from compare import compare_sequence
from tuning_plot import make_tuning_plot
from helpers import fake_played


def test_plot_has_one_bar_for_each_note():
    targets = ["C4", "E4", "G4"]

    performance = [
        fake_played("C4", 5),
        fake_played("E4", -30),
        None
    ]

    figure = make_tuning_plot(
        compare_sequence(targets, performance)
    )

    axes = figure.axes[0]

    # axes.patches also holds the shaded background bands,
    # so the bars themselves are read from the bar container.
    bars = axes.containers[0]

    assert len(bars) == len(targets)

    labels = [
        text.get_text()
        for text in axes.get_yticklabels()
    ]

    assert labels == targets


def test_plot_always_shows_the_whole_semitone():
    """
    A well played phrase should not be zoomed in so far that
    tiny errors look dramatic.
    """

    targets = ["C4", "E4"]

    performance = [
        fake_played("C4", 2),
        fake_played("E4", -3)
    ]

    figure = make_tuning_plot(
        compare_sequence(targets, performance)
    )

    left, right = figure.axes[0].get_xlim()

    assert left <= -50
    assert right >= 50


def test_plot_is_not_cut_short_by_a_bad_note():
    """
    A note that misses by a long way must still be drawn
    where it landed.
    """

    targets = ["C4"]

    figure = make_tuning_plot(
        compare_sequence(targets, [fake_played("C4", 300)])
    )

    left, right = figure.axes[0].get_xlim()

    assert right >= 300


def test_performance_plot_draws_written_notes_and_the_line():
    import numpy as np
    from tuning_plot import make_performance_plot

    times = np.array([0.0, 0.25, 0.5, 0.75])
    midi = np.array([60.0, 60.2, 64.0, np.nan])

    figure = make_performance_plot(
        ["C4", "E4"],
        [1.0, 1.0],
        120,
        (times, midi)
    )

    axes = figure.axes[0]

    # One box per written note, one line for the singing.
    assert len(axes.collections) == 2
    assert len(axes.lines) == 1

    # The picture spans the written music: two beats at
    # 120 BPM is one second.
    assert axes.get_xlim()[1] == 1.0


def test_performance_plot_shifts_boxes_with_the_octave():
    """
    When scoring an octave down, the boxes move to where
    the singer actually is, so the line lands on them.
    """

    import numpy as np
    from tuning_plot import make_performance_plot
    from notes import note_to_midi

    figure = make_performance_plot(
        ["C4"],
        [1.0],
        120,
        None,
        transpose=-12
    )

    axes = figure.axes[0]

    labels = [t.get_text() for t in axes.texts]

    assert labels == ["C3"]


def test_performance_plot_copes_with_no_trace():
    from tuning_plot import make_performance_plot

    figure = make_performance_plot(
        ["C4", "E4"],
        [1.0, 1.0],
        120,
        None
    )

    assert len(figure.axes[0].lines) == 0


def test_performance_plot_shows_syllables_under_notes():
    from tuning_plot import make_performance_plot

    figure = make_performance_plot(
        ["C4", "C4"],
        [1.0, 1.0],
        120,
        None,
        lyrics=["Twin-", "kle"]
    )

    texts = [t.get_text() for t in figure.axes[0].texts]

    assert "Twin-" in texts
    assert "kle" in texts


def test_melisma_is_drawn_as_a_line_not_an_underscore():
    from tuning_plot import make_performance_plot

    figure = make_performance_plot(
        ["C4", "E4"],
        [1.0, 1.0],
        120,
        None,
        lyrics=["star", "_"]
    )

    texts = [t.get_text() for t in figure.axes[0].texts]

    assert "star" in texts
    assert "_" not in texts
    assert "\u2014" in texts


def test_harmony_appears_as_a_second_voice():
    from tuning_plot import make_performance_plot

    figure = make_performance_plot(
        ["C4", "G4"],
        [1.0, 1.0],
        120,
        None,
        harmony=["A3", "E4"]
    )

    axes = figure.axes[0]

    # Two melody boxes and two harmony boxes.
    assert len(axes.collections) == 4

    labels = [t.get_text() for t in axes.texts]

    assert "A3" in labels
    assert "E4" in labels