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

from midi_import import (
    describe_tracks,
    import_midi,
    BEAT_FRACTIONS
)
from music import (
    import_midi_file,
    list_midi_tracks,
    list_midi_phrases,
    read_beats
)


FIXTURE_DIRECTORY = os.path.join(
    os.path.dirname(__file__),
    "fixtures",
    "midi"
)


MIDI_FILES = sorted(
    glob.glob(os.path.join(FIXTURE_DIRECTORY, "*.mid"))
)


def allowed_duration(text):
    """
    Whether a duration is one the importer can produce.

    The text is read back with the app's own parser, so a
    length written as a fraction is checked the same way
    the music boxes would read it.
    """

    value = read_beats(text)

    return any(
        abs(value - fraction) < 0.001
        for fraction in BEAT_FRACTIONS
    )


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
        assert allowed_duration(duration), (
            f"{duration} is not a note length"
        )

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


@pytest.mark.skipif(
    len(MIDI_FILES) == 0,
    reason="no midi files in tests/fixtures/midi"
)
@pytest.mark.parametrize(
    "path",
    MIDI_FILES,
    ids=[os.path.basename(p) for p in MIDI_FILES]
)
def test_every_phrase_of_a_real_file_imports(path):
    """
    A real piece divides into phrases, each of which must
    stand on its own as music the app can use.
    """

    tracks = list_midi_tracks(path)

    phrases = list_midi_phrases(path, tracks[0])

    # The whole track, plus at least one phrase.
    assert len(phrases) >= 2

    for label in phrases:

        pitches, durations, lyrics, bpm, feedback = (
            import_midi_file(path, tracks[0], label)
        )

        pitch_list = pitches.split()

        assert len(pitch_list) > 0
        assert len(pitch_list) == len(durations.split())


def test_o_holy_night_divides_into_singable_phrases():
    """
    The soprano line runs to 129 notes, which is far more
    than anyone practises at once. It should arrive in
    phrases of a sensible length, broken where the music
    rests rather than at an arbitrary count.
    """

    path = os.path.join(
        FIXTURE_DIRECTORY,
        "o-holy-night-satb.mid"
    )

    if not os.path.exists(path):
        pytest.skip("o holy night fixture not present")

    from midi_import import describe_phrases

    described = describe_phrases(path, track_number=1)

    assert len(described) > 3

    for number, label in described:
        assert "Phrase" in label
        assert "bars" in label


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

    # The whole line, not a truncated part of it.
    assert len(pitches.split()) > 120