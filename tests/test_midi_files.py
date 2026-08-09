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
    WRITABLE_LENGTHS as BEAT_FRACTIONS
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
    Whether a duration is one that can be written down.

    The text is read back with the app's own parser, so a
    length written as a fraction is checked the same way
    the music boxes would read it.

    Checked against everything writable rather than against
    the plain lengths a recording is rounded to: five
    quarters of a beat is a crotchet tied to a quaver, and
    a quantised part is full of them.
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

    from piece import Piece

    tracks = list_midi_tracks(path)

    (
        pitches,
        durations,
        lyrics,
        bpm,
        feedback,
        chart,
        chart_notes,
        key
    ) = import_midi_file(path, tracks[0])

    # The import brings the whole part, and the phrases
    # are the lines of the lyrics within it.
    whole = Piece.read(pitches, durations, lyrics, key, chart)

    assert len(whole.phrases()) >= 1

    for number in range(len(whole.phrases())):

        phrase = whole.phrase(number)

        assert len(phrase.pitches) > 0

        # A phrase is a piece in its own right: as many
        # lengths as notes, and its own words and chords.
        assert len(phrase.pitches) == len(phrase.durations)

        if phrase.lyrics:
            assert len(phrase.lyrics.split()) == phrase.sung()


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


def test_typed_lyrics_rename_the_phrases_at_once():
    """
    Lyrics need no saving: the box holds them.

    They used to be copied into a store keyed by phrase, so
    that a phrase could be named by what had been typed for
    it. That was necessary when the boxes held one phrase
    and the file held the rest. Now the box holds the whole
    part and the words in it are the only copy there is, so
    editing them changes the phrase names by definition.
    """

    from music import list_phrases

    notes = "C4 C4 G4 G4 A4 A4 G4 R"
    lengths = "1 1 1 1 1 1 3/2 1/2"

    named = list_phrases(
        notes, lengths, "Twin- kle twin- kle\nlit- tle star"
    )

    assert "Twinkle twinkle" in named[1]

    # Rewriting the words renames the phrase, with nothing
    # saved anywhere.
    renamed = list_phrases(
        notes, lengths, "My own words here\nlit- tle star"
    )

    assert "My own words here" in renamed[1]


def test_editing_the_lyrics_changes_how_many_phrases_there_are():
    from music import list_phrases

    notes = "C4 C4 G4 G4 A4 A4 G4 R"
    lengths = "1 1 1 1 1 1 3/2 1/2"

    one = list_phrases(notes, lengths, "Twin- kle twin- kle lit- tle star")

    three = list_phrases(
        notes, lengths, "Twin- kle\ntwin- kle\nlit- tle star"
    )

    assert len(one) == 1
    assert len(three) == 4