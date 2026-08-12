"""
The functions that live in mixer_data.py: sound encoding,
the chart timeline, opening levels and colours, the
component's dictionary, and reading a loop back out of it.

Most of these used to be tested via mixer_block.py, which
owned them before the move to the real MusicMixer
component. mixer_data() and loop_region() are new here -
they had no test of their own before the component was
wired into main.py, since there was nothing yet reading
their combined output.
"""

import base64
import io

from mixer_data import (
    as_wav_data,
    _timeline,
    OPENING_LEVELS,
    LAYER_COLOURS,
    mixer_data,
    loop_region
)
from music import load_wellerman, LAYER_NAMES


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


def test_mixer_data_has_the_shape_the_component_expects():
    """
    The dictionary the MusicMixer component's value is set
    from - layers, timeline, notes, phrases, and an open
    loop_start/loop_end that a freshly built mixer starts
    without one.
    """

    pitches, durations, lyrics, key, chart, tempo = song()

    value = mixer_data(
        pitches, durations, key, tempo, chart,
        lyric_text=lyrics, phrase_label="Whole part"
    )

    assert set(value.keys()) == {
        "layers", "timeline", "notes", "phrases",
        "loop_start", "loop_end"
    }

    assert value["loop_start"] is None
    assert value["loop_end"] is None

    layer_names = {layer["name"] for layer in value["layers"]}
    assert layer_names <= set(LAYER_NAMES)
    assert "Melody" in layer_names

    for layer in value["layers"]:
        assert layer["wav"]

    assert len(value["timeline"]) > 1
    assert len(value["notes"]) > 1
    assert len(value["phrases"]) > 1


def test_mixer_data_notes_carry_words_on_the_melody_only():
    """
    Only the sung line has words. The generated harmony and
    bass are derived from it, not independently sung, so
    they carry no lyrics of their own.
    """

    pitches, durations, lyrics, key, chart, tempo = song()

    value = mixer_data(
        pitches, durations, key, tempo, chart,
        lyric_text=lyrics, phrase_label="Whole part"
    )

    melody_notes = [
        note for note in value["notes"] if note["layer"] == "Melody"
    ]

    assert any("word" in note for note in melody_notes)

    for note in value["notes"]:
        if note["layer"] != "Melody":
            assert "word" not in note


def test_mixer_data_without_a_chart_has_no_bass_layer():
    """
    Bass reads the root of each chord, so without a chart
    there is nothing to build it from - absent rather than
    silent, the same rule mixer_html followed.
    """

    value = mixer_data("C4 D4 E4", "1 1 1", "C", 120, "")

    layer_names = {layer["name"] for layer in value["layers"]}

    assert "Bass" not in layer_names
    assert "Melody" in layer_names


def test_loop_region_reads_a_selected_stretch():
    """
    What a Compare handler would read once the browser has
    sent a loop back.
    """

    assert loop_region({"loop_start": 4.0, "loop_end": 9.5}) == (4.0, 9.5)


def test_loop_region_is_none_when_nothing_is_selected():
    """
    A freshly built mixer, or one where nothing has been
    clicked yet.
    """

    assert loop_region({"loop_start": None, "loop_end": None}) is None
    assert loop_region(None) is None
    assert loop_region({}) is None