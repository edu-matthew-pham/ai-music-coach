# tests/test_music.py

import numpy as np
import pytest

from pitch_detector import Pitch
from music import (
    MusicInputError,
    read_music,
    play_music,
    show_harmony,
    analyse_single_note,
    analyse_sequence,
    analyse_instrument,
    load_twinkle_phrase
)


def test_read_music():
    pitches, durations = read_music(
        "C4 D4 E4",
        "1 1 2"
    )

    assert pitches == ["C4", "D4", "E4"]
    assert durations == [1.0, 1.0, 2.0]


def test_read_music_requires_matching_lengths():
    with pytest.raises(ValueError):
        read_music(
            "C4 D4 E4",
            "1 1"
        )


def test_show_harmony():
    harmony = show_harmony(
        "C4 G4 A4",
        "C"
    )

    assert harmony == "A3 E4 F4"


def test_play_music_returns_gradio_audio():
    sample_rate, audio = play_music(
        "C4 C4",
        "1 1",
        "C",
        melody_on=True,
        harmony_on=False,
        bpm=120
    )

    assert sample_rate == 8000
    assert isinstance(audio, np.ndarray)

    # Two beats at 120 BPM = one second. Listening modes
    # start straight away, with no count-in.
    assert len(audio) == 8000


def test_everything_off_still_clicks():
    """
    Melody and harmony both off gives a click track, not
    silence that looks like the app failed.
    """

    sample_rate, audio = play_music(
        "C4 C4",
        "1 1",
        "C",
        melody_on=False,
        harmony_on=False,
        bpm=120,
        metronome=False
    )

    assert float(np.max(np.abs(audio))) > 0.1


def test_melody_and_harmony_mix_together():
    sample_rate, together = play_music(
        "C4 C4",
        "1 1",
        "C",
        melody_on=True,
        harmony_on=True,
        bpm=120,
        metronome=False
    )

    sample_rate, alone = play_music(
        "C4 C4",
        "1 1",
        "C",
        melody_on=True,
        harmony_on=False,
        bpm=120,
        metronome=False
    )

    # The mixed track is a different signal, not just the
    # melody again.
    shared = min(len(together), len(alone))

    assert not np.allclose(
        together[:shared],
        alone[:shared]
    )


def test_load_twinkle_phrase():
    pitches, durations, lyrics = load_twinkle_phrase()

    assert pitches == "C4 C4 G4 G4 A4 A4 G4"
    assert durations == "1 1 1 1 1 1 2"
    assert lyrics == "Twin- kle twin- kle lit- tle star"


def test_analyse_single_note_no_pitch(monkeypatch):
    monkeypatch.setattr(
        "music.detect_single_note",
        lambda audio: None
    )

    result = analyse_single_note(
        "fake audio"
    )

    assert result == "No clear pitch detected."


def fake_pitch(note, cents=0.0):
    """
    Build a Pitch without going near any audio.
    """

    return Pitch(
        frequency=440.0,
        midi=69.0,
        note=note,
        cents=cents
    )


def test_analyse_single_note_in_tune(monkeypatch):
    monkeypatch.setattr(
        "music.detect_single_note",
        lambda audio: fake_pitch("A4")
    )

    result = analyse_single_note(
        "fake audio"
    )

    assert result == "Detected note: A4 (in tune)"


def test_analyse_single_note_sharp(monkeypatch):
    monkeypatch.setattr(
        "music.detect_single_note",
        lambda audio: fake_pitch("A4", cents=32.0)
    )

    result = analyse_single_note(
        "fake audio"
    )

    assert result == "Detected note: A4 (32 cents sharp)"


def test_analyse_single_note_flat(monkeypatch):
    monkeypatch.setattr(
        "music.detect_single_note",
        lambda audio: fake_pitch("A4", cents=-27.0)
    )

    result = analyse_single_note(
        "fake audio"
    )

    assert result == "Detected note: A4 (27 cents flat)"


def test_analyse_sequence(monkeypatch):
    monkeypatch.setattr(
        "music.detect_sequence",
        lambda audio, durations, bpm: [
            fake_pitch("C4"),
            fake_pitch("G4", cents=38.0),
            None
        ]
    )

    result = analyse_sequence(
        "fake audio",
        "1 1 2",
        120
    )

    # In-tune notes stay plain, so only the notes worth
    # attention carry an annotation.
    assert result == "C4 G4(+38) ?"


def test_analyse_instrument(monkeypatch):
    fake_results = [
        {
            "label": "violin",
            "score": 0.82
        },
        {
            "label": "flute",
            "score": 0.11
        },
        {
            "label": "keyboard",
            "score": 0.07
        }
    ]

    monkeypatch.setattr(
        "music.detect_instrument",
        lambda audio: fake_results
    )

    result = analyse_instrument(
        "fake audio"
    )

    assert result == (
        "violin: 82.0%\n"
        "flute: 11.0%\n"
        "keyboard: 7.0%"
    )




def test_practice_guide_counts_in_then_clicks():
    from music import make_practice_guide

    result = make_practice_guide(
        "C4 C4",
        "1 1",
        120,
        "Clicks"
    )

    sample_rate, audio = result

    # Four count-in beats plus two beats of music.
    assert len(audio) == 6 * 4000


def test_practice_guide_can_include_the_melody():
    from music import make_practice_guide

    sample_rate, audio = make_practice_guide(
        "C4 C4",
        "1 1",
        120,
        "Your part"
    )

    assert len(audio) == 6 * 4000

    # The music section carries more than clicks: notes are
    # long sounds, so the section is loud for most of its
    # length rather than only at the beats.
    music_section = np.abs(audio[4 * 4000:])

    loud_share = float(np.mean(music_section > 0.1))

    assert loud_share > 0.5


def test_practice_guide_can_be_turned_off():
    from music import make_practice_guide

    assert make_practice_guide(
        "C4 C4",
        "1 1",
        120,
        "No guide"
    ) is None


def test_practice_guide_validates_its_input():
    from music import make_practice_guide

    with pytest.raises(MusicInputError):
        make_practice_guide("C4 banana", "1 1", 120, "Clicks")


def test_show_target_music_draws_without_a_performance():
    from music import show_target_music

    figure = show_target_music(
        "C4 E4",
        "1 1",
        120,
        "la la"
    )

    axes = figure.axes[0]

    assert len(axes.collections) == 2
    assert len(axes.lines) == 0

    texts = [t.get_text() for t in axes.texts]

    assert "la" in texts


def test_show_target_music_works_without_lyrics():
    from music import show_target_music

    figure = show_target_music(
        "C4 E4",
        "1 1",
        120,
        ""
    )

    assert len(figure.axes[0].collections) == 2