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
    loop_region,
    loop_notes
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
    from - layers, timeline, notes, phrases, diagrams, and
    an open loop_start/loop_end that a freshly built mixer
    starts without one.
    """

    pitches, durations, lyrics, key, chart, tempo = song()

    value = mixer_data(
        pitches, durations, key, tempo, chart,
        lyric_text=lyrics, phrase_label="Whole part"
    )

    assert set(value.keys()) == {
        "layers", "timeline", "notes", "phrases", "diagrams",
        "bpm", "loop_start", "loop_end"
    }

    assert value["loop_start"] is None
    assert value["loop_end"] is None

    layer_names = {layer["name"] for layer in value["layers"]}
    assert layer_names <= set(LAYER_NAMES)
    assert "Melody" in layer_names

    for layer in value["layers"]:
        assert layer["wav"]

    assert len(value["timeline"]) > 1

    # The diagrams stack in the browser, so mixer_data must
    # always ship the full instrument set for the structure
    # (always-there background) and the scale base, and one
    # chord overlay per chord name the chart actually
    # printed on the strip.
    from instrument_diagrams import INSTRUMENTS

    assert set(value["diagrams"]["structure"].keys()) == set(INSTRUMENTS)
    assert set(value["diagrams"]["scale"].keys()) == set(INSTRUMENTS)

    chart_chord_names = {
        bar["name"] for bar in value["timeline"] if bar["name"]
    }

    assert (
        set(value["diagrams"]["chords"]["Piano"].keys())
        == chart_chord_names
    )

    # shapes is the beginner-voicing alternative to chords -
    # present for every instrument key, but only actually
    # populated where a standard shape exists. Piano covers
    # every quality this app supports, so its shapes should
    # match chords exactly for this song's chart.
    assert set(value["diagrams"]["shapes"].keys()) == set(INSTRUMENTS)

    assert (
        set(value["diagrams"]["shapes"]["Piano"].keys())
        == chart_chord_names
    )

    # Violin now has a real shape mode too - a beginner
    # double stop, first position only - so its shapes
    # dict should match chords the same way Piano's does,
    # not sit empty the way it used to before that existed.
    assert (
        set(value["diagrams"]["shapes"]["Violin, first position"].keys())
        == chart_chord_names
    )

    # Third position has no shape of its own, so it falls
    # back to chord_overlay_for for every chord - the panel
    # sees a missing entry there, same as any other
    # quality-with-no-standard-shape gap.
    assert value["diagrams"]["shapes"]["Violin, third position"] == {}

    # Structure and scale must be different pictures, not
    # the same one under two names - the bug that shipped
    # the combined diagram as "scale" and left nothing for
    # an always-there background.
    structure_piano = value["diagrams"]["structure"]["Piano"]
    scale_piano = value["diagrams"]["scale"]["Piano"]

    assert structure_piano != scale_piano
    assert "<rect" in structure_piano
    assert "<rect" not in scale_piano
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


def test_mixer_data_carries_its_own_build_tempo():
    """
    A selected loop is in seconds fixed at the tempo the
    mixer was built at. Reading it back has to use that
    tempo, not whatever the BPM box says later, so it is
    carried in the dictionary rather than assumed to match.
    """

    value = mixer_data("C4 D4 E4", "1 1 1", "C", 90, "")

    assert value["bpm"] == 90.0


def test_loop_notes_finds_the_selected_stretch():
    """
    The reverse of the walk that placed notes in seconds:
    given a selected range, find which notes it covers.
    """

    pitches, durations, lyrics, key, chart, tempo = song()

    value = mixer_data(
        pitches, durations, key, tempo, chart,
        lyric_text=lyrics, phrase_label="Whole part"
    )

    timeline = value["timeline"]
    value["loop_start"] = timeline[1]["start"]
    value["loop_end"] = timeline[5]["end"]

    piece = loop_notes(pitches, durations, lyrics, key, chart, value)

    assert piece is not None
    assert 0 < len(piece.pitches) < len(pitches.split())

    # The chart re-cuts to the loop too, the same way
    # Piece.slice already does for the phrase dropdown -
    # this is not new chart-cutting logic, just a new way
    # of choosing the range to cut to.
    assert piece.chart.strip()


def test_loop_notes_uses_the_build_tempo_not_a_different_one():
    """
    The same seconds, read against the tempo actually used
    to build the mixer, land on the same notes regardless of
    what the BPM box says by the time Compare runs.
    """

    pitches, durations, lyrics, key, chart, tempo = song()

    value = mixer_data(
        pitches, durations, key, tempo, chart,
        lyric_text=lyrics, phrase_label="Whole part"
    )

    timeline = value["timeline"]
    value["loop_start"] = timeline[1]["start"]
    value["loop_end"] = timeline[5]["end"]

    at_build_tempo = loop_notes(
        pitches, durations, lyrics, key, chart, value
    )

    # A tampered copy with the wrong bpm would misread the
    # same seconds against a different beat grid - this is
    # the bug the carried bpm field exists to prevent.
    wrong_tempo_value = dict(value, bpm=tempo * 2)

    at_wrong_tempo = loop_notes(
        pitches, durations, lyrics, key, chart, wrong_tempo_value
    )

    assert len(at_build_tempo.pitches) != len(at_wrong_tempo.pitches)


def test_loop_notes_is_none_without_a_selection():
    """
    Nothing selected yet, or the mixer never built - either
    way, there is nothing to slice to.
    """

    pitches, durations, lyrics, key, chart, tempo = song()

    value = mixer_data(
        pitches, durations, key, tempo, chart,
        lyric_text=lyrics, phrase_label="Whole part"
    )

    assert loop_notes(pitches, durations, lyrics, key, chart, value) is None
    assert loop_notes(pitches, durations, lyrics, key, chart, None) is None