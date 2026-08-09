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

    (
        pitches,
        durations,
        lyrics,
        bpm,
        feedback,
        chart,
        chart_notes,
        key
        ) = (
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

        pitches, durations, lyrics, bpm, chart, chart_notes = import_midi(
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

        (
            pitches,
            durations,
            lyrics,
            bpm,
            feedback,
            chart,
            chart_notes,
            key
            ) = (
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

    pitches, durations, lyrics, bpm, chart, chart_notes = import_midi(
        path,
        track_number=1
    )

    opening = " ".join(pitches.split()[:6])

    assert opening == "F#4 F#4 F#4 A4 A4 B4"

    # The whole line, not a truncated part of it.
    assert len(pitches.split()) > 120


def test_a_file_that_divides_by_channel_finds_its_parts():
    """
    A notation program gives each voice its own track. A
    sequencer often puts everything on one track and
    separates the instruments by channel, which is how band
    and pop arrangements usually arrive. Looking only at
    tracks finds one part in such a file, containing all of
    them at once, and the import is an unsingable tangle.
    """

    import os

    from music import list_midi_tracks

    path = os.path.join(
        os.path.dirname(__file__),
        "fixtures", "midi", "d_ML_10791.mid"
    )

    if not os.path.exists(path):
        pytest.skip("the band arrangement fixture is absent")

    parts = list_midi_tracks(path)

    assert len(parts) > 5

    # Named by instrument, since a file rarely names its
    # parts but almost always says what plays them.
    joined = " ".join(parts)

    assert "Alto Sax" in joined
    assert "Bass" in joined


def test_the_likeliest_tune_is_offered_first():
    """
    Nothing is hidden, but the part most likely to be the
    tune is easiest to reach.
    """

    import os

    from music import list_midi_tracks

    for name, expected in [
        ("d_ML_10791.mid", "Alto Sax"),
        ("d_FR1924.mid", "Pan Flute"),
        ("o-holy-night-satb.mid", "Pan Flute")
    ]:

        path = os.path.join(
            os.path.dirname(__file__),
            "fixtures", "midi", name
        )

        if not os.path.exists(path):
            continue

        parts = list_midi_tracks(path)

        assert expected in parts[0], f"{name}: got {parts[0]}"
        assert "probably the tune" in parts[0]


def test_an_arpeggiated_accompaniment_is_not_mistaken_for_a_tune():
    """
    An arpeggio is one note at a time too, and looks
    exactly like a melody until the notes are counted. A
    sung line rarely passes two notes to the beat for long,
    while a broken chord figure runs at three or four.
    """

    import os

    from music import list_midi_tracks

    path = os.path.join(
        os.path.dirname(__file__),
        "fixtures", "midi", "o-holy-night-satb.mid"
    )

    if not os.path.exists(path):
        pytest.skip("the satb fixture is not present")

    parts = list_midi_tracks(path)

    busy = [label for label in parts if "too busy" in label]

    assert busy

    # And it is not the first thing offered.
    assert "too busy" not in parts[0]


def test_percussion_is_described_rather_than_hidden():
    """
    A drum part is worth practising, and this app will not
    always be only for singers. It is labelled for what it
    is and left available.
    """

    import os

    from music import list_midi_tracks

    path = os.path.join(
        os.path.dirname(__file__),
        "fixtures", "midi", "d_ML_10791.mid"
    )

    if not os.path.exists(path):
        pytest.skip("the band arrangement fixture is absent")

    parts = list_midi_tracks(path)

    drums = [label for label in parts if "Drums" in label]

    assert drums
    assert "not pitched" in drums[0]

    # But not put forward as something to sing.
    assert "Drums" not in parts[0]


def test_phrases_are_named_by_their_words():
    """
    "There once was a ship" tells a singer which phrase
    this is. The same phrase written as A#3 C4 C4 C4 C4
    tells them almost nothing, and they would have to load
    each one to find out.
    """

    import os

    from music import list_midi_tracks, list_midi_phrases

    path = os.path.join(
        os.path.dirname(__file__),
        "fixtures", "midi", "d_ML_10791.mid"
    )

    if not os.path.exists(path):
        pytest.skip("the band arrangement fixture is absent")

    parts = list_midi_tracks(path)

    phrases = list_midi_phrases(path, parts[0])

    joined = " ".join(phrases)

    assert "There once was a ship" in joined


def test_a_phrase_without_words_is_named_by_its_notes():
    import os

    from music import list_midi_tracks, list_midi_phrases

    path = os.path.join(
        os.path.dirname(__file__),
        "fixtures", "midi", "o-holy-night-satb.mid"
    )

    if not os.path.exists(path):
        pytest.skip("the satb fixture is not present")

    parts = list_midi_tracks(path)

    phrases = list_midi_phrases(path, parts[0])

    assert "F#4" in " ".join(phrases)


def test_typed_lyrics_name_the_phrase_they_belong_to():
    """
    A phrase the player has written words for is named by
    those words: their own working text rather than the
    notes, and their own corrections rather than whatever
    the file happened to carry.
    """

    import os

    from music import (
        list_midi_tracks,
        list_midi_phrases,
        remember_lyrics
    )

    path = os.path.join(
        os.path.dirname(__file__),
        "fixtures", "midi", "o-holy-night-satb.mid"
    )

    if not os.path.exists(path):
        pytest.skip("the satb fixture is not present")

    parts = list_midi_tracks(path)

    phrases = list_midi_phrases(path, parts[0])

    saved = remember_lyrics(
        {},
        parts[0],
        phrases[1],
        "O ho- ly night the stars are bright- ly shin- ing"
    )

    named = list_midi_phrases(path, parts[0], saved)

    # Hyphenated syllables are put back into words.
    assert "O holy night" in named[1]

    # And only that phrase is renamed.
    assert named[2] == phrases[2]


def test_lyrics_belong_to_a_phrase_of_a_part():
    """
    The third phrase of the bass line is a different
    stretch of music from the third of the tune.
    """

    from music import remember_lyrics, phrase_key

    saved = remember_lyrics({}, "0:0 Sax", "Phrase 3", "hello")

    assert phrase_key("0:0 Sax", "Phrase 3") in saved
    assert phrase_key("0:1 Bass", "Phrase 3") not in saved


def test_clearing_the_lyric_box_forgets_them():
    from music import remember_lyrics

    saved = remember_lyrics({}, "0:0", "Phrase 1", "words here")

    assert saved

    assert not remember_lyrics(saved, "0:0", "Phrase 1", "   ")


def test_importing_sets_the_key_the_music_is_in():
    """
    Everything else the import fills is set from the file.
    Leaving the key behind means the harmony, the chord
    spelling and the pitch axis all work from the wrong
    place until someone notices.
    """

    import os

    from music import list_midi_tracks, import_midi_file
    from harmony import MAJOR_SCALES

    expected = {
        "o-holy-night-satb.mid": "D",
        "d_ML_10791.mid": "Eb",
        "d_FR1924.mid": "Bb"
    }

    for name, key in expected.items():

        path = os.path.join(
            os.path.dirname(__file__),
            "fixtures", "midi", name
        )

        if not os.path.exists(path):
            continue

        parts = list_midi_tracks(path)

        imported = import_midi_file(path, parts[0])

        assert imported[7] == key, f"{name}: got {imported[7]}"

        # And it is a key the app can actually be set to.
        assert imported[7] in MAJOR_SCALES


def test_a_minor_piece_is_set_to_its_relative_major():
    """
    The key setting names a signature, so a piece in C
    minor arrives as E flat major: the same seven notes,
    and the setting harmony is built from.
    """

    import os

    from music import list_midi_tracks, import_midi_file

    path = os.path.join(
        os.path.dirname(__file__),
        "fixtures", "midi", "d_ML_10791.mid"
    )

    if not os.path.exists(path):
        pytest.skip("the band arrangement fixture is absent")

    parts = list_midi_tracks(path)

    imported = import_midi_file(path, parts[0])

    assert "C minor" in imported[4]
    assert imported[7] == "Eb"