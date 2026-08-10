"""
Score every chord-reading mechanism against the tab.

Ground truth is a published beginner chord sheet for the
Wellerman, read at function level and transposed into the
d_ML_10791 arrangement's C minor. Bars are compared at
root level, majority vote per true bar; true downbeats sit
one beat after the melody's pickup.

Run from the repo root:  python score_against_tab.py

The raw-grid mechanisms (per-beat detector, chorder) are
mapped onto the box grid by piecewise-linear interpolation
between the 129 melody onsets, matched note for note -
a global linear fit does not work because the raw file's
tempo drifts against the repaired grid.
"""

from fractions import Fraction
import bisect

import mido

from music import list_midi_tracks, import_midi_file, suggest_chords, load_wellerman
from midi_import import read_notes
from chords import read_chart, chord_at
from chord_detector import weigh_pitches, name_chord
from chorder import Dechorder
from miditoolkit import MidiFile as ToolkitFile

PATH = 'tests/fixtures/midi/d_ML_10791.mid'

VERSE = ['C', 'C', 'F', 'C', 'C', 'C', 'G', 'C']
CHORUS = ['G#', 'D#', 'F', 'C', 'G#', 'D#', 'G', 'C']
TRUTH = VERSE + VERSE + CHORUS


def root_of(name):
    name = str(name).split('/')[0]
    for quality in ['maj7', 'm7', 'dim', 'aug', 'sus4', 'sus2',
                    'M7', 'M', 'm', '7', 'o', '+', '6', '9']:
        if name.endswith(quality):
            name = name[:-len(quality)]
            break
    return {'Bb': 'A#', 'Eb': 'D#', 'Ab': 'G#',
            'Db': 'C#', 'Gb': 'F#'}.get(name.replace('-', 'b'), name)


def main():
    p, d, l, bpm, fb, chart, chart_notes, key = import_midi_file(
        PATH, list_midi_tracks(PATH)[0])
    imported, _ = read_chart(chart)
    suggested, _ = read_chart(suggest_chords(None, p, d, key))

    words_at = {}
    position = Fraction(0)
    tokens = iter(l.split())
    for pitch, dur in zip(p.split(), d.split()):
        if pitch != 'R':
            words_at[float(position)] = next(tokens)
        position += Fraction(dur)

    raw_melody, _ = read_notes(mido.MidiFile(PATH), track_number=0, channel=0)
    raw_all, _ = read_notes(mido.MidiFile(PATH))
    xs = sorted(words_at)
    ys = [onset for onset, dur, pitch in sorted(raw_melody)]

    def to_raw(beat):
        i = bisect.bisect_right(xs, beat) - 1
        i = max(0, min(i, len(xs) - 2))
        x0, x1 = xs[i], xs[i + 1]
        y0, y1 = ys[i], ys[i + 1]
        return y0 + (y1 - y0) * (beat - x0) / (x1 - x0)

    theirs = Dechorder.dechord(ToolkitFile(PATH))

    def votes_to_root(votes):
        return max(votes, key=votes.get) if votes else None

    def bar_chart(chords, k):
        votes = {}
        for beat in range(1 + 4 * k, 5 + 4 * k):
            name = chord_at(chords, beat + 0.01)
            if name:
                votes[root_of(name)] = votes.get(root_of(name), 0) + 1
        return votes_to_root(votes)

    def bar_raw(k):
        votes = {}
        for beat in range(1 + 4 * k, 5 + 4 * k):
            lo, hi = to_raw(beat), to_raw(beat + 1)
            weights, lowest = weigh_pitches(raw_all, lo, hi)
            name = name_chord(weights, lowest)
            if name:
                votes[root_of(name)] = votes.get(root_of(name), 0) + 1
        return votes_to_root(votes)

    def bar_chorder(k):
        votes = {}
        for beat in range(1 + 4 * k, 5 + 4 * k):
            lo, hi = to_raw(beat), to_raw(beat + 1)
            for raw in range(int(lo), max(int(lo) + 1, int(hi))):
                if 0 <= raw < len(theirs) and str(theirs[raw]) != 'None':
                    root = root_of(str(theirs[raw]))
                    votes[root] = votes.get(root, 0) + 1
        return votes_to_root(votes)

    mechanisms = {
        'chart': lambda k: bar_chart(imported, k),
        'beat': bar_raw,
        'chorder': bar_chorder,
        'suggest': lambda k: bar_chart(suggested, k),
    }

    results = {m: [fn(k) for k in range(24)] for m, fn in mechanisms.items()}

    header = f"{'bar':>3} {'truth':>6}"
    for m in mechanisms:
        header += f" {m:>8}"
    print(header + "   words")
    for k, truth in enumerate(TRUTH):
        row = []
        for m in mechanisms:
            got = results[m][k]
            row.append(f"{('*' if got == truth else ' ') + (got or '-'):>8}")
        words = ' '.join(words_at[o] for o in xs if 1 + 4 * k <= o < 5 + 4 * k)
        print(f"{k:>3} {truth:>6}", *row, f"  {words}")

    print("\nvs the tab (verse 0-15 | chorus 16-23 | all):")
    for m in mechanisms:
        verse = sum(results[m][k] == TRUTH[k] for k in range(16))
        chorus = sum(results[m][k] == TRUTH[k] for k in range(16, 24))
        print(f"  {m:>8}: {verse}/16 | {chorus}/8 | "
              f"{verse + chorus}/24 ({100 * (verse + chorus) // 24}%)")

    print("\npairwise agreement:")
    names = list(mechanisms)
    for i, m1 in enumerate(names):
        for m2 in names[i + 1:]:
            same = sum(results[m1][k] == results[m2][k] for k in range(24))
            print(f"  {m1} ~ {m2}: {same}/24")


if __name__ == '__main__':
    main()