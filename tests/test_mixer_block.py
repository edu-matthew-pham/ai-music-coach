"""
The mixer block, as far as Python can see it.

What is testable here is what Python builds: the layers,
their sound data, and the timeline the browser follows.
What happens after that - decoding, gain nodes, the
playhead - runs in a browser and is invisible to pytest.
That boundary is worth naming rather than pretending
these tests cover the feature.
"""

import base64
import io

import pytest

from mixer_block import (
    mixer_html,
    as_wav_data,
    _timeline,
    OPENING_LEVELS,
    LAYER_COLOURS
)
from music import LAYER_NAMES, load_wellerman


def song():
    return load_wellerman()


def test_every_layer_is_sent_as_its_own_sound():
    """
    The point of the block: the parts arrive apart, so a
    level can move without anything being made again.
    """

    pitches, durations, lyrics, key, chart, tempo = song()

    html = mixer_html(
        pitches, durations, key, tempo, chart,
        lyric_text=lyrics, phrase_label="Whole part"
    )

    for name in LAYER_NAMES:
        assert f'"{name}"' in html


def test_a_layer_decodes_as_a_sound_file():
    """
    The browser is handed a wav, so it has to be one.
    """

    from scipy.io import wavfile

    data = as_wav_data([0.0, 0.5, -0.5, 0.0], 8000)

    rate, samples = wavfile.read(io.BytesIO(base64.b64decode(data)))

    assert rate == 8000
    assert len(samples) == 4


def test_a_layer_louder_than_the_speaker_is_brought_back():
    """
    Sent past full scale it would wrap round and sound
    broken rather than loud.
    """

    from scipy.io import wavfile

    data = as_wav_data([0.0, 4.0, -4.0], 8000)

    rate, samples = wavfile.read(io.BytesIO(base64.b64decode(data)))

    assert max(abs(int(value)) for value in samples) <= 32767


def test_the_timeline_says_when_each_chord_sounds():
    """
    In seconds, because the browser knows where it is in a
    sound file and not what a beat is.
    """

    pitches, durations, lyrics, key, chart, tempo = song()

    strip = _timeline(
        pitches, durations, key, tempo, chart, lyrics, "Whole part"
    )

    assert len(strip) > 1

    first = strip[0]

    assert first["start"] == 0
    assert first["end"] > 0
    assert first["name"]

    # In order, and touching: a gap would leave the
    # playhead lighting nothing.
    for before, after in zip(strip, strip[1:]):
        assert after["start"] >= before["start"]
        assert abs(after["start"] - before["end"]) < 0.001


def test_the_timeline_carries_the_words_under_each_bar():
    """
    So the strip reads as the song rather than as a row of
    chord names.
    """

    pitches, durations, lyrics, key, chart, tempo = song()

    strip = _timeline(
        pitches, durations, key, tempo, chart, lyrics, "Whole part"
    )

    assert any(bar["words"] for bar in strip)

    words = " ".join(bar["words"] for bar in strip)

    assert "Wel-" in words or "Wellerman" in words


def test_the_timeline_follows_the_tempo():
    """
    Twice the speed, half the seconds. The bars are the
    same bars.
    """

    pitches, durations, lyrics, key, chart, tempo = song()

    slow = _timeline(
        pitches, durations, key, 60, chart, lyrics, "Whole part"
    )

    fast = _timeline(
        pitches, durations, key, 120, chart, lyrics, "Whole part"
    )

    assert len(slow) == len(fast)

    assert abs(slow[-1]["end"] - 2 * fast[-1]["end"]) < 0.01


def test_no_chart_means_no_strip_and_no_missing_faders():
    """
    Bass and chords come from the chart. Without one they
    are absent rather than silent, and the block says so
    instead of offering faders that do nothing.
    """

    html = mixer_html("C4 D4 E4", "1 1 1", "C", 120, "")

    assert '"Bass"' not in html
    assert '"Chords"' not in html

    assert "No chord chart" in html

    assert _timeline("C4 D4 E4", "1 1 1", "C", 120, "", "", None) == []


def test_the_faders_start_where_the_sliders_did():
    """
    The tune audible, a click under it, the rest waiting.
    Opening onto a full six part mix would be a shock.
    """

    assert OPENING_LEVELS["Melody"] == 1.0
    assert OPENING_LEVELS["Metronome"] > 0

    for name in ("Harmony above", "Harmony below", "Bass", "Chords"):
        assert OPENING_LEVELS[name] == 0.0


def test_a_fader_wears_the_colour_of_its_part():
    """
    The same colours the picture uses, so a fader and the
    line it moves are recognisably one thing.
    """

    from tuning_plot import (
        HARMONY_ABOVE_COLOUR, HARMONY_BELOW_COLOUR, BASS_COLOUR
    )

    assert LAYER_COLOURS["Harmony above"] == HARMONY_ABOVE_COLOUR
    assert LAYER_COLOURS["Harmony below"] == HARMONY_BELOW_COLOUR
    assert LAYER_COLOURS["Bass"] == BASS_COLOUR


def test_a_phrase_is_a_smaller_thing_to_send_than_a_song():
    """
    The parts travel as sound, so the whole song is a large
    block. Worth knowing rather than discovering on a
    slow connection.
    """

    pitches, durations, lyrics, key, chart, tempo = song()

    from music import list_phrases

    labels = list_phrases(pitches, durations, lyrics)

    phrase = mixer_html(
        pitches, durations, key, tempo, chart,
        lyric_text=lyrics, phrase_label=labels[5]
    )

    whole = mixer_html(
        pitches, durations, key, tempo, chart,
        lyric_text=lyrics, phrase_label="Whole part"
    )

    assert len(phrase) < len(whole) / 4
