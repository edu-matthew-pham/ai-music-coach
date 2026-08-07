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
