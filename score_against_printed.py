"""
Score the chord detector against a score's own printed
symbols.

Any MusicXML file that prints chord symbols is a labelled
test: the importer reads the symbols as the chart (truth,
a human's own statement of the harmony) and the detector
reads the polyphony behind them (the guess). Bars are
compared at root level, majority vote per bar - the same
method score_against_tab.py uses, without the onset
interpolation, since a notation file's grid is clean.

A file with no printed symbols cannot serve: the importer
falls back to detection there, and the comparison would
be the detector agreeing with itself. The script says so
and scores nothing.

Run from the repo root:

    python score_against_printed.py song.mxl [more.mxl]
"""

"""
Score the chord detector against a score's own printed
symbols.

Any MusicXML file that prints chord symbols is a labelled
test: the importer reads the symbols as the chart (truth,
a human's own statement of the harmony) and the detector
reads the polyphony behind them (the guess).

Scoring uses mir_eval, the field's own standard chord
evaluation library, rather than a hand-rolled comparison.
This matters, found the hard way: an earlier version of
this script compared roots only, by majority vote per bar,
and that comparison silently counted a minor chord read as
major - the "man" third missing - as a correct answer,
because root_of() throws the third away before anything
gets compared. mir_eval's root/thirds/triads/mirex tiers
compare what a chord actually is, not just its letter name,
and are the same tiers a published chord recognizer reports
- so a number here means the same thing a paper's does.

A file with no printed symbols cannot serve: the importer
falls back to detection there, and the comparison would
be the detector agreeing with itself. The script says so
and scores nothing.

Run from the repo root:

    python score_against_printed.py song.mxl [more.mxl]
"""

import sys
import warnings

from musicxml_import import import_musicxml
from chord_detector import chart_from_notes
from chords import read_chart, CHORD_QUALITIES


# Our own quality suffixes to mir_eval's Harte-notation
# names. mir_eval knows "maj6"/"min6", we spell them "6"/
# "m6"; everything else already matches its own vocabulary.
HARTE_QUALITY = {
    "": "maj",
    "m": "min",
    "7": "7",
    "m7": "min7",
    "maj7": "maj7",
    "dim": "dim",
    "aug": "aug",
    "sus2": "sus2",
    "sus4": "sus4",
    "6": "maj6",
    "m6": "min6",
}


def to_harte(name):
    """
    Our own chord spelling ("Bbm7") to mir_eval's own
    ("Bb:min7"), by splitting off the longest quality
    suffix this app knows about.
    """

    for suffix in sorted(CHORD_QUALITIES, key=len, reverse=True):

        if suffix and name.endswith(suffix):

            root = name[:-len(suffix)]

            return f"{root}:{HARTE_QUALITY[suffix]}"

    return f"{name}:maj"


def to_intervals(chords, start_beat, end_beat):
    """
    (start, length, name) triples, clipped to the scored
    range, as the (intervals, labels) pair mir_eval wants.
    A gap becomes an explicit "N" (no chord), since mir_eval
    expects the timeline fully covered, not silently skipped.
    """

    intervals = []
    labels = []

    cursor = start_beat

    for start, length, name in sorted(chords):

        chord_start = max(start, start_beat)
        chord_end = min(start + length, end_beat)

        if chord_end <= chord_start:
            continue

        if chord_start > cursor:
            intervals.append((cursor, chord_start))
            labels.append("N")

        intervals.append((chord_start, chord_end))
        labels.append(to_harte(name))

        cursor = chord_end

    if cursor < end_beat:
        intervals.append((cursor, end_beat))
        labels.append("N")

    return intervals, labels


def score_file(path):
    """
    Compare printed truth to detection for one file, on
    mir_eval's standard tiers.
    """

    (
        pitches, durations, lyrics, bpm,
        feedback, chart, polyphony, key
    ) = import_musicxml(path)

    if "printed" not in feedback:
        print(f"{path}: no printed chord symbols - the "
              "chart was detected, so there is no truth "
              "to score against.")
        return

    total = max(
        (start + length for start, length, midi in polyphony),
        default=0
    )

    beats_per_bar = len(chart.split("|")[1].strip().split())

    truth, _ = read_chart(chart)

    detected, _ = read_chart(
        chart_from_notes(
            polyphony, float(total), beats_per_bar, key
        )
    )

    # Where the score actually prints symbols - a bar
    # before the first one was never really claimed as
    # that chord (see the module docstring history: an
    # earlier version invented truth for an unlabelled
    # intro by scoring against fill_gaps's own display-only
    # backfill).
    from music21 import converter, harmony

    score = converter.parse(path)

    symbol_offsets = [
        symbol.offset
        for part in score.parts
        for symbol in part.flatten().getElementsByClass(
            harmony.ChordSymbol
        )
    ]

    first_beat = min(symbol_offsets)
    last_beat = max(symbol_offsets) + beats_per_bar

    import mir_eval.chord as mc
    import numpy as np

    ref_intervals, ref_labels = to_intervals(
        truth, first_beat, last_beat
    )
    est_intervals, est_labels = to_intervals(
        detected, first_beat, last_beat
    )

    scores = mc.evaluate(
        np.array(ref_intervals), ref_labels,
        np.array(est_intervals), est_labels
    )

    bars = int(round((last_beat - first_beat) / beats_per_bar))

    print(f"{path}: key {key}, {beats_per_bar} beats to "
          f"the bar, {bars} bars carry a printed symbol")

    # thirds first: root and the major/minor third are the
    # two notes that actually decide what a chord is - the
    # fifth barely matters (same note either way), and a
    # jazz shell voicing drops it and keeps root+third+
    # seventh for exactly that reason. Root alone lets a
    # major/minor swap hide behind a correct letter name -
    # found directly, not hypothetically: it called 24 real
    # errors "correct" across two songs before this metric
    # was in use.
    for tier in ("thirds", "root", "triads", "sevenths",
                 "tetrads", "majmin", "mirex"):

        print(f"  {tier:>8}: {scores[tier]:.0%}")


if __name__ == "__main__":

    warnings.filterwarnings("ignore")

    paths = sys.argv[1:]

    if not paths:
        print(__doc__)
        sys.exit(1)

    for path in paths:
        score_file(path)
        print()
        print()
