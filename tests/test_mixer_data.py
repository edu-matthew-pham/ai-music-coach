"""
The functions that live in mixer_data.py: sound encoding,
the chart timeline, opening levels and colours.

These used to be tested via mixer_block.py, which owned
them. They now live in mixer_data.py and mixer_block.py
only borrows them back for as long as it still exists, so
the tests point at the module that actually owns the
behaviour - the same reason mixer_block.py can be deleted
later without silently losing this coverage.

mixer_data() itself - the dictionary a MusicMixer
component's value expects, and loop_region() - is covered
separately once the component is wired into main.py.
"""

import base64
import io

from mixer_data import (
    as_wav_data,
    _timeline,
    OPENING_LEVELS,
    LAYER_COLOURS
)
from music import load_wellerman


def song():
    return load_wellerman()


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


def test_no_chart_means_no_timeline():
    """
    Bass and chords come from the chart. Without one there
    is nothing to follow.
    """

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
