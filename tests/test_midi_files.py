"""
Import real MIDI files.

Every other MIDI test builds its file in memory, which
means every file is exactly as tidy as the test that made
it. Real files are not: they carry piano reductions beside
the voices, tempo changes, key signatures, and note lengths
that never quite land on the beat.

Only files that are free to redistribute belong here.
O Holy Night is from 1847 and long out of copyright, and
the arrangement is our own.
"""

import glob
import os

import pytest

from midi_import import describe_tracks, import_midi
from music import import_midi_file, list_midi_tracks


FIXTURE_DIRECTORY = os.path.join(
    os.path.dirname(__file__),
    "fixtures",
    "midi"
)


MIDI_FILES = sorted(
    glob.glob(os.path.join(FIXTURE_DIRECTORY, "*.mid"))
)


DURATIONS_ALLOWED = {
    "0.25", "0.5", "0.75", "1", "1.5", "2", "3", "4", "6", "8"
}


@pytest.mark.skipif(
    len(MIDI_FILES) == 0,
    reason="no midi files in tests/fixtures/midi"
)
@pytest.mark.parametrize(
    "path",
    MIDI_FILES,
    ids=[os.path.basename(p) for p in MIDI_FILES]
)
def test_real_file_imports_into_playable_music(path):
    """
    Whatever the file holds, what comes out must be music
    the rest of the app can use.
    """

    labels = list_midi_tracks(path)

    assert len(labels) > 0

    pitches, durations, lyrics, bpm, feedback = (
        import_midi_file(path, labels[0])
    )

    pitch_list = pitches.split()
    duration_list = durations.split()

    assert len(pitch_list) == len(duration_list)
    assert len(pitch_list) > 0

    # Every duration must be a length the app understands.
    for duration in duration_list:
        assert duration in DURATIONS_ALLOWED

    assert 20 <= bpm <= 300

    assert "Imported" in feedback


@pytest.mark.skipif(
    len(MIDI_FILES) == 0,
    reason="no midi files in tests/fixtures/midi"
)
@pytest.mark.parametrize(
    "path",
    MIDI_FILES,
    ids=[os.path.basename(p) for p in MIDI_FILES]
)
def test_every_track_of_a_real_file_imports(path):
    """
    Each part must import on its own, not just the first.
    """

    for number, label in describe_tracks(path):

        pitches, durations, lyrics, bpm = import_midi(
            path,
            track_number=number
        )

        assert len(pitches.split()) > 0
        assert len(pitches.split()) == len(durations.split())


def test_the_soprano_line_of_o_holy_night():
    """
    The melody sits on track 1. Track 0 is a piano
    reduction, which is why the track cannot simply be
    guessed at by picking the highest or the busiest.
    """

    path = os.path.join(
        FIXTURE_DIRECTORY,
        "o-holy-night-satb.mid"
    )

    if not os.path.exists(path):
        pytest.skip("o holy night fixture not present")

    pitches, durations, lyrics, bpm = import_midi(
        path,
        track_number=1
    )

    opening = " ".join(pitches.split()[:6])

    assert opening == "F#4 F#4 F#4 A4 A4 B4"
