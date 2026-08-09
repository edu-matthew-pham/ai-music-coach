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

from notes import note_to_midi, midi_to_note, is_rest


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
    transpose=0,
    lyrics=None,
    title="What you sang, over what was written",
    harmony=None,
    chords=None,
    bars=None
):
    """
    Draw what was sung over what was written.

    The written music appears as boxes: each note occupies
    its time slot at its pitch. The performance is the line
    running through them, one point per moment, so a late
    entry, a slide between notes, or a wobble is simply
    visible rather than inferred.

    When a harmony line is given, it appears as a second
    voice in its own colour, sharing the same time axis so
    the two parts read together the way a duet is printed.

    Chords and bar lines are drawn where a lead sheet puts
    them: symbols above the music, bar lines behind it. The
    melody is not obliged to agree with either, since a
    note may begin off the beat and run across a change.
    """

    seconds_per_beat = 60 / bpm

    figure, axes = plt.subplots(figsize=(8, 4))

    # The written notes, shifted into the octave actually
    # being sung in, so the line lands on the boxes.
    lowest = None
    highest = None

    start_time = 0.0

    lyric_position = 0

    for position in range(len(targets)):

        length = durations[position] * seconds_per_beat

        # A rest leaves a gap: no box, no label, but the
        # time still passes.
        if is_rest(targets[position]):
            start_time += length
            continue

        midi = note_to_midi(targets[position]) + transpose

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

        # The syllable sung on this note, under its box.
        # An underscore is a held syllable and shows as a
        # continuation line rather than text, following
        # engraving convention.
        if lyrics is not None and lyric_position < len(lyrics):

            syllable = lyrics[lyric_position]
            lyric_position += 1

            if syllable == "_":
                shown = "—"

            else:
                shown = syllable

            axes.text(
                start_time + length / 2,
                midi - 0.95,
                shown,
                ha="center",
                va="top",
                fontsize=9,
                color="#555555"
            )

        start_time += length

        if lowest is None or midi < lowest:
            lowest = midi

        if highest is None or midi > highest:
            highest = midi

    # The harmony, as a second voice under the melody.
    if harmony is not None:

        harmony_start = 0.0

        for position in range(len(harmony)):

            length = durations[position] * seconds_per_beat

            if is_rest(harmony[position]):
                harmony_start += length
                continue

            midi = note_to_midi(harmony[position]) + transpose

            axes.broken_barh(
                [(harmony_start, length)],
                (midi - 0.5, 1.0),
                facecolors="#6a1b9a",
                alpha=0.12,
                edgecolor="#6a1b9a",
                linewidth=1
            )

            axes.text(
                harmony_start + length / 2,
                midi,
                midi_to_note(midi),
                ha="center",
                va="center",
                fontsize=8,
                color="#6a1b9a"
            )

            harmony_start += length

            if midi < lowest:
                lowest = midi

            if midi > highest:
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

    # Room above the music for the chord symbols.
    headroom = 4 if chords else 2

    axes.set_ylim(lowest - 2, highest + headroom)

    # Bar lines behind everything, faint enough to read
    # the music through.
    if bars:
        for bar_start, bar_length in bars:
            axes.axvline(
                bar_start * seconds_per_beat,
                color="#90a4ae",
                linewidth=0.8,
                linestyle="-",
                alpha=0.5,
                zorder=0
            )

        last_start, last_length = bars[-1]

        axes.axvline(
            (last_start + last_length) * seconds_per_beat,
            color="#90a4ae",
            linewidth=0.8,
            alpha=0.5,
            zorder=0
        )

    # Chord symbols above the music, at the moment each
    # chord arrives, as a lead sheet prints them.
    if chords:
        for chord_start, chord_length, name in chords:
            axes.text(
                chord_start * seconds_per_beat + 0.05,
                highest + headroom - 1,
                name,
                fontsize=9,
                fontweight="bold",
                color="#37474f",
                va="center"
            )

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
    axes.set_title(title)

    axes.spines["top"].set_visible(False)
    axes.spines["right"].set_visible(False)

    figure.tight_layout()

    return figure


def make_tuning_plot(comparisons):
    """
    Turn a list of NoteComparison into a matplotlib figure.
    """

    height = max(
        2.5,
        0.5 * len([c for c in comparisons if not c.is_rest]) + 1.2
    )

    figure, axes = plt.subplots(figsize=(8, height))

    sung = [
        comparison for comparison in comparisons
        if not comparison.is_rest
    ]

    positions = list(
        range(len(sung))
    )

    labels = []
    values = []
    colours = []

    for comparison in comparisons:

        if comparison.is_rest:
            continue

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

        if not sung[position].was_detected:

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