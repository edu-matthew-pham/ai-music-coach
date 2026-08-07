# tuning_plot.py

"""
Draw a performance as a tuning chart.

Each note gets a bar showing how far it landed from the note
that was intended. The centre line is the target, and the
shaded band either side is the region where the note is still
nearer the target than either of its neighbours.

Bars are not cut short. A note that misses badly is drawn
where it actually landed, so a large mistake looks large.
"""

import matplotlib

# Draw without needing a window, which a web app has no use for.
matplotlib.use("Agg")

import matplotlib.pyplot as plt

import numpy as np

from notes import note_to_midi, midi_to_note


# Anything inside this is close enough that a listener would
# not comment on it.
COMFORTABLE_CENTS = 15

# Past this the note is nearer a neighbouring semitone.
SEMITONE_EDGE = 50


def make_performance_plot(
    targets,
    durations,
    bpm,
    trace,
    transpose=0
):
    """
    Draw what was sung over what was written.

    The written music appears as boxes: each note occupies
    its time slot at its pitch. The performance is the line
    running through them, one point per moment, so a late
    entry, a slide between notes, or a wobble is simply
    visible rather than inferred.
    """

    seconds_per_beat = 60 / bpm

    figure, axes = plt.subplots(figsize=(8, 4))

    # The written notes, shifted into the octave actually
    # being sung in, so the line lands on the boxes.
    lowest = None
    highest = None

    start_time = 0.0

    for position in range(len(targets)):

        midi = note_to_midi(targets[position]) + transpose

        length = durations[position] * seconds_per_beat

        axes.broken_barh(
            [(start_time, length)],
            (midi - 0.5, 1.0),
            facecolors="#2e7d32",
            alpha=0.15,
            edgecolor="#2e7d32",
            linewidth=1
        )

        axes.text(
            start_time + length / 2,
            midi,
            midi_to_note(midi),
            ha="center",
            va="center",
            fontsize=8,
            color="#2e7d32"
        )

        start_time += length

        if lowest is None or midi < lowest:
            lowest = midi

        if highest is None or midi > highest:
            highest = midi

    # The performance itself.
    if trace is not None:

        times, midi_line = trace

        axes.plot(
            times,
            midi_line,
            color="#1565c0",
            linewidth=2
        )

        sung = midi_line[~np.isnan(midi_line)]

        if len(sung) > 0:
            lowest = min(lowest, float(np.min(sung)))
            highest = max(highest, float(np.max(sung)))

    axes.set_xlim(0, start_time)
    axes.set_ylim(lowest - 2, highest + 2)

    # Label the pitch axis with note names rather than
    # MIDI numbers, since players think in notes.
    tick_values = range(
        int(lowest) - 1,
        int(highest) + 2
    )

    axes.set_yticks(list(tick_values))
    axes.set_yticklabels(
        [midi_to_note(value) for value in tick_values],
        fontsize=8
    )

    axes.set_xlabel("seconds")
    axes.set_title("What you sang, over what was written")

    axes.spines["top"].set_visible(False)
    axes.spines["right"].set_visible(False)

    figure.tight_layout()

    return figure


def make_tuning_plot(comparisons):
    """
    Turn a list of NoteComparison into a matplotlib figure.
    """

    height = max(2.5, 0.5 * len(comparisons) + 1.2)

    figure, axes = plt.subplots(figsize=(8, height))

    positions = list(
        range(len(comparisons))
    )

    labels = []
    values = []
    colours = []

    for comparison in comparisons:

        labels.append(comparison.target)

        if not comparison.was_detected:
            values.append(0)
            colours.append("#cccccc")
            continue

        values.append(comparison.cents_from_target)

        if abs(comparison.cents_from_target) <= COMFORTABLE_CENTS:
            colours.append("#2e7d32")

        elif comparison.is_target_note:
            colours.append("#f9a825")

        else:
            colours.append("#c62828")

    # The band where the note still counts as the target.
    axes.axvspan(
        -SEMITONE_EDGE,
        SEMITONE_EDGE,
        color="#000000",
        alpha=0.04
    )

    axes.axvspan(
        -COMFORTABLE_CENTS,
        COMFORTABLE_CENTS,
        color="#2e7d32",
        alpha=0.08
    )

    axes.barh(
        positions,
        values,
        color=colours,
        height=0.6
    )

    # Mark the notes where nothing was heard.
    for position in positions:

        if not comparisons[position].was_detected:

            axes.text(
                0,
                position,
                "  not detected",
                va="center",
                fontsize=8,
                color="#777777"
            )

    axes.axvline(0, color="#333333", linewidth=1)

    axes.set_yticks(positions)
    axes.set_yticklabels(labels)
    axes.invert_yaxis()

    axes.set_xlabel("cents from the target note")
    axes.set_title("Tuning")

    # Always show at least the full semitone either side, so
    # a good performance does not look dramatic just because
    # the errors were small.
    largest = max(
        [abs(value) for value in values] + [SEMITONE_EDGE]
    )

    axes.set_xlim(
        -largest * 1.15 - 5,
        largest * 1.15 + 5
    )

    axes.spines["top"].set_visible(False)
    axes.spines["right"].set_visible(False)

    figure.tight_layout()

    return figure