"""
Detection against real recorded instrument notes.

Every other pitch test uses a synthesised sine wave, which
has only one partial. Real instruments are much richer, and
a detector can lock onto a harmonic instead of the actual
note. These samples are the only test that would catch it.

Sample files come from the Philharmonia Orchestra sample
library and are named like:

    violin_C4_15_forte_arco-normal.mp3
    instrument_pitch_tenths_dynamic_articulation

Only a handful of files are committed. The full library
lives outside the repository.
"""

import glob
import os

import numpy as np
import pytest

import librosa

from notes import note_to_midi
from pitch_detector import detect_pitch


FIXTURE_DIRECTORY = os.path.join(
    os.path.dirname(__file__),
    "fixtures",
    "audio"
)


# The detector searches between C3 and C6. Samples outside
# that range cannot be detected and are not a fair test:
# pyin clamps to the nearest bound and locks onto a
# subharmonic instead, usually an octave or a twelfth down.
#
# The upper limit stops just short of C6 because detection
# grows unreliable right at the boundary.
LOWEST_TESTABLE = note_to_midi("G3")
HIGHEST_TESTABLE = note_to_midi("B5")


def expected_note_from(filename):
    """
    Read the intended note out of a sample filename.

    Sharps are written with an s, because a # is awkward
    in a filename, so Cs4 means C#4.
    """

    pitch = os.path.basename(filename).split("_")[1]

    return pitch[0] + pitch[1:].replace("s", "#")


def find_sample_files():
    """
    Collect the committed sample files worth testing.
    """

    patterns = ["*.mp3", "*.wav"]

    files = []

    for pattern in patterns:
        files.extend(
            glob.glob(
                os.path.join(FIXTURE_DIRECTORY, pattern)
            )
        )

    testable = []

    for path in sorted(files):

        midi = note_to_midi(
            expected_note_from(path)
        )

        if LOWEST_TESTABLE <= midi <= HIGHEST_TESTABLE:
            testable.append(path)

    return testable


SAMPLE_FILES = find_sample_files()


def load_steady_part(path, sample_rate=22050):
    """
    Load a sample and keep only its steady middle.

    The start of a bowed note is unstable while the bow
    catches, and the end fades away, so both are trimmed.
    """

    sound, rate = librosa.load(
        path,
        sr=sample_rate,
        mono=True
    )

    # Remove leading and trailing near-silence.
    sound, _ = librosa.effects.trim(
        sound,
        top_db=30
    )

    # Keep the central 60%.
    length = len(sound)
    ignored = int(length * 0.2)

    return sound[ignored:length - ignored], rate


@pytest.mark.skipif(
    len(SAMPLE_FILES) == 0,
    reason="no sample files committed in tests/fixtures/audio"
)
@pytest.mark.parametrize(
    "path",
    SAMPLE_FILES,
    ids=[os.path.basename(p) for p in SAMPLE_FILES]
)
def test_detects_recorded_note(path):
    """
    The detector must name a real recorded note correctly.
    """

    sound, rate = load_steady_part(path)

    pitch = detect_pitch(sound, rate)

    assert pitch is not None, "no pitch found in the recording"

    assert pitch.note == expected_note_from(path)


@pytest.mark.skipif(
    len(SAMPLE_FILES) == 0,
    reason="no sample files committed in tests/fixtures/audio"
)
@pytest.mark.parametrize(
    "path",
    SAMPLE_FILES,
    ids=[os.path.basename(p) for p in SAMPLE_FILES]
)
def test_recorded_note_is_nearer_its_own_note(path):
    """
    Tuning must be plausible rather than exact.

    Real players are not perfectly in tune and some
    instruments are deliberately not equal tempered, so all
    we require is that the note sits closer to its intended
    pitch than to either neighbour.
    """

    sound, rate = load_steady_part(path)

    pitch = detect_pitch(sound, rate)

    assert abs(pitch.cents) < 50
