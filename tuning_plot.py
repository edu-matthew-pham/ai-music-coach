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
from harmony import MAJOR_SCALES


# Anything inside this is close enough that a listener would
# not comment on it.
COMFORTABLE_CENTS = 15

# Past this the note is nearer a neighbouring semitone.
SEMITONE_EDGE = 50


# Each voice has its own colour, dark enough to read the
# note name inside its box.
HARMONY_COLOUR = "#6a1b9a"
BASS_COLOUR = "#00695c"


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
    bars=None,
    bass=None,
    key=None,
    chord_asides=None
):
    """
    Draw what was sung over what was written.

    The written music appears as boxes: each note occupies
    its time slot at its pitch. The performance is the line
    running through them, one point per moment, so a late
    entry, a slide between notes, or a wobble is simply
    visible rather than inferred.

    A harmony or bass line given alongside appears as a
    further voice in its own colour, sharing the same time
    axis so the parts read together the way a score prints
    them. A bass holds one note through several of the
    melody's, which is exactly how it looks: long boxes
    below short ones.

    Chords and bar lines are drawn where a lead sheet puts
    them: symbols above the music, bar lines behind it. The
    melody is not obliged to agree with either, since a
    note may begin off the beat and run across a change.
    """

    seconds_per_beat = 60 / bpm

    def name_at(beat):
        return round(float(beat), 3)

    figure, axes = plt.subplots(figsize=(8, 4))
    # Resized once the range of the voices is known.

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
            midi_to_note(midi, key),
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

    # The other voices, each in its own colour, sharing
    # the melody's time axis so the parts read together
    # the way a score prints them.
    for notes, colour in (
        (harmony, HARMONY_COLOUR),
        (bass, BASS_COLOUR)
    ):

        if notes is None:
            continue

        voice_start = 0.0

        for position in range(len(notes)):

            length = durations[position] * seconds_per_beat

            if is_rest(notes[position]):
                voice_start += length
                continue

            midi = note_to_midi(notes[position]) + transpose

            axes.broken_barh(
                [(voice_start, length)],
                (midi - 0.5, 1.0),
                facecolors=colour,
                alpha=0.12,
                edgecolor=colour,
                linewidth=1
            )

            axes.text(
                voice_start + length / 2,
                midi,
                midi_to_note(midi, key),
                ha="center",
                va="center",
                fontsize=8,
                color=colour
            )

            voice_start += length

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

    # Room above the music for the chord symbols, and more
    # again when they carry a bracket underneath.
    headroom = 2

    if chords:
        headroom = 5 if chord_asides else 4

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
    #
    # A bracket underneath carries what the chart cannot
    # say: the note the chord is played over, and a name
    # that fits the same notes equally well. Information
    # rather than instruction, the way a key is offered as
    # F major / D minor without either being the answer.
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

            aside = (chord_asides or {}).get(name_at(chord_start))

            if aside:
                axes.text(
                    chord_start * seconds_per_beat + 0.05,
                    highest + headroom - 1.9,
                    aside,
                    fontsize=7,
                    color="#78909c",
                    va="center"
                )

    # Label the pitch axis with note names rather than
    # MIDI numbers, since players think in notes.
    #
    # With a key, the labels are the notes of its scale:
    # seven to the octave, every one meaningful, and the
    # axis itself becomes a picture of where the key sits.
    # Without one, every semitone is named.
    #
    # A wide range gets a taller figure rather than fewer
    # labels, so three voices spread out instead of being
    # squeezed into the same four inches as one.
    span = int(highest) - int(lowest)

    height = 4 + max(0, (span - 14) * 0.15)

    figure.set_size_inches(8, min(height, 9))

    all_values = range(int(lowest) - 1, int(highest) + 2)

    if key in MAJOR_SCALES:

        scale = {
            note_to_midi(name + "4") % 12
            for name in MAJOR_SCALES[key]
        }

        tick_values = [
            value for value in all_values
            if value % 12 in scale
        ]

    else:
        tick_values = list(all_values)

    axes.set_yticks(tick_values)
    axes.set_yticklabels(
        [midi_to_note(value, key) for value in tick_values],
        fontsize=8
    )

    # The axis speaks the language of what is drawn on it.
    #
    # With a chord chart the music is in bars: the ticks
    # sit on the bar lines and count them, with beats as
    # smaller marks between, the way anyone counting the
    # music counts. Seconds remain when there is no chart,
    # because a bare recording is genuinely in seconds and
    # bars would be an invention.
    if bars:

        from matplotlib.ticker import FixedLocator

        bar_edges = [
            bar_start * seconds_per_beat
            for bar_start, bar_length in bars
        ]

        last_start, last_length = bars[-1]

        bar_edges.append(
            (last_start + last_length) * seconds_per_beat
        )

        axes.set_xticks(bar_edges)

        axes.set_xticklabels(
            [str(number + 1) for number in range(len(bars))]
            + [""]
        )

        beat_marks = []

        for bar_start, bar_length in bars:

            for beat in range(1, int(round(bar_length))):

                beat_marks.append(
                    (bar_start + beat) * seconds_per_beat
                )

        axes.xaxis.set_minor_locator(FixedLocator(beat_marks))

        axes.tick_params(axis="x", which="minor", length=2)

        axes.set_xlabel("bars")

    else:
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