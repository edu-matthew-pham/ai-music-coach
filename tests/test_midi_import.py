import mido
import pytest

from midi_import import (
    MidiImportError,
    import_midi,
    snap_to_beat,
    keep_melody
)


def write_midi(path, notes, bpm=120, lyrics=None):
    """
    Build a simple MIDI file for a test.

    notes is a list of (midi_number, beats).
    """

    ticks = 480

    midi_file = mido.MidiFile(ticks_per_beat=ticks)
    track = mido.MidiTrack()
    midi_file.tracks.append(track)

    track.append(
        mido.MetaMessage(
            "set_tempo",
            tempo=mido.bpm2tempo(bpm),
            time=0
        )
    )

    for position, (number, beats) in enumerate(notes):

        if lyrics is not None and position < len(lyrics):
            track.append(
                mido.MetaMessage(
                    "lyrics",
                    text=lyrics[position],
                    time=0
                )
            )

        track.append(
            mido.Message(
                "note_on", note=number, velocity=80, time=0
            )
        )

        track.append(
            mido.Message(
                "note_off",
                note=number,
                velocity=0,
                time=int(beats * ticks)
            )
        )

    midi_file.save(path)

    return path


def test_imports_a_simple_melody(tmp_path):
    path = write_midi(
        str(tmp_path / "simple.mid"),
        [(60, 1), (64, 1), (67, 2)],
        bpm=100
    )

    pitches, durations, lyric_text, bpm = import_midi(path)

    assert pitches == "C4 E4 G4"
    assert durations == "1 1 2"
    assert bpm == 100


def test_imports_karaoke_lyrics(tmp_path):
    path = write_midi(
        str(tmp_path / "lyrics.mid"),
        [(60, 1), (64, 1)],
        lyrics=["la", "la"]
    )

    pitches, durations, lyric_text, bpm = import_midi(path)

    assert lyric_text == "la la"


def test_mismatched_lyrics_are_left_out(tmp_path):
    """
    A file whose lyric count does not match its notes is
    imported without lyrics rather than misaligned.
    """

    path = write_midi(
        str(tmp_path / "odd.mid"),
        [(60, 1), (64, 1), (67, 1)],
        lyrics=["only", "two"]
    )

    # Two lyric events against three notes.
    midi_file = mido.MidiFile(path)
    events = [
        m for t in midi_file.tracks for m in t
        if m.type == "lyrics"
    ]
    assert len(events) == 2

    pitches, durations, lyric_text, bpm = import_midi(path)

    assert lyric_text == ""


def test_chords_keep_the_top_note():
    """
    When notes start together, the melody is taken to be
    the highest.
    """

    together = [
        (0.0, 1.0, 60),
        (0.0, 1.0, 64),
        (0.0, 1.0, 67),
        (1.0, 1.0, 65)
    ]

    melody = keep_melody(together)

    assert [number for _, _, number in melody] == [67, 65]


def test_awkward_lengths_snap_to_beats():
    assert snap_to_beat(0.98) == 1.0
    assert snap_to_beat(0.52) == 0.5
    assert snap_to_beat(1.7) == 1.5
    assert snap_to_beat(7.0) == 6.0


def test_unreadable_file_is_reported(tmp_path):
    path = tmp_path / "noise.mid"
    path.write_bytes(b"this is not midi")

    with pytest.raises(MidiImportError, match="could not be read"):
        import_midi(str(path))


def test_empty_file_is_reported(tmp_path):
    midi_file = mido.MidiFile()
    midi_file.tracks.append(mido.MidiTrack())

    path = str(tmp_path / "empty.mid")
    midi_file.save(path)

    with pytest.raises(MidiImportError, match="No notes"):
        import_midi(path)


def test_describe_tracks_lists_each_voice(tmp_path):
    """
    A file with a part per track describes them all, so
    the player can pick the line they are singing.
    """

    from midi_import import describe_tracks

    midi_file = mido.MidiFile(ticks_per_beat=480)

    voices = [
        [(72, 1), (74, 1)],
        [(60, 1), (62, 1)]
    ]

    for voice in voices:

        track = mido.MidiTrack()
        midi_file.tracks.append(track)

        for number, beats in voice:
            track.append(
                mido.Message(
                    "note_on", note=number, velocity=80, time=0
                )
            )
            track.append(
                mido.Message(
                    "note_off",
                    note=number,
                    velocity=0,
                    time=int(beats * 480)
                )
            )

    path = str(tmp_path / "satb.mid")
    midi_file.save(path)

    described = describe_tracks(path)

    assert len(described) == 2

    assert described[0][0] == 0
    assert "C5" in described[0][1]
    assert "C4" in described[1][1]


def test_importing_one_track_ignores_the_others(tmp_path):
    """
    Choosing a track imports that line alone, not the
    highest note of everything sounding at once.
    """

    midi_file = mido.MidiFile(ticks_per_beat=480)

    for numbers in ([72, 74], [60, 62]):

        track = mido.MidiTrack()
        midi_file.tracks.append(track)

        for number in numbers:
            track.append(
                mido.Message(
                    "note_on", note=number, velocity=80, time=0
                )
            )
            track.append(
                mido.Message(
                    "note_off", note=number, velocity=0, time=480
                )
            )

    path = str(tmp_path / "two.mid")
    midi_file.save(path)

    lower, durations, lyrics, bpm = import_midi(
        path,
        track_number=1
    )

    assert lower == "C4 D4"

    upper, durations, lyrics, bpm = import_midi(
        path,
        track_number=0
    )

    assert upper == "C5 D5"