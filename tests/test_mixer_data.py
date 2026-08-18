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
    _diagrams,
    OPENING_LEVELS,
    LAYER_COLOURS,
    mixer_data,
    loop_region,
    loop_notes
)
from music import LAYER_NAMES
from examples import load_wellerman


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


def test_the_timeline_says_when_each_bar_sounds():
    """
    In seconds, because the browser knows where it is in a
    sound file and not what a beat is. One box per real
    bar now, not one per chord run - every bar carries at
    least one chord in its own chords list.
    """

    pitches, durations, lyrics, key, chart, tempo = song()

    strip = _timeline(
        pitches, durations, key, tempo, chart, lyrics, "Whole part"
    )

    assert len(strip) > 1

    first = strip[0]

    assert first["start"] == 0
    assert first["end"] > 0
    assert first["chords"]
    assert first["chords"][0]["name"]

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


def test_a_bar_shows_every_chord_it_holds_not_one_run_per_box():
    """
    read_chart() returns chords (one entry per chord run,
    dots merged) and bars (one entry per actual bar) as two
    separate lists. A chord spanning several bars used to
    swallow them - one box claiming to be "bar 1", nothing
    shown for the bars after; a bar with more than one
    chord change used to split into several boxes, each
    claiming to be its own bar. Both were the same mistake:
    a box was a chord run, not a bar.

    Em holds bars 1 and 2 whole. D and G split bar 3 in
    half. Three real bars, three boxes - not four run-boxes
    drifting away from the real bar count.
    """

    pitches = "C4 D4 E4 F4 G4 A4 B4 C5 D5 E5 F5 G5"
    durations = "1 1 1 1 1 1 1 1 1 1 1 1"
    chart = "| Em . . . | . . . . | D . G . |"

    strip = _timeline(
        pitches, durations, "C", 120, chart, "", None
    )

    assert [bar["bar"] for bar in strip] == [1, 2, 3]

    assert strip[0]["chords"] == [
        {"name": "Em", "beat_in_bar": 0.0, "carried": False}
    ]

    # Bar 2 is entirely carried - not new here, but still
    # its own bar, present and numbered.
    assert strip[1]["chords"] == [
        {"name": "Em", "beat_in_bar": 0.0, "carried": True}
    ]

    assert strip[2]["chords"] == [
        {"name": "D", "beat_in_bar": 0.0, "carried": False},
        {"name": "G", "beat_in_bar": 2.0, "carried": False}
    ]


def test_a_half_beat_split_carries_its_true_position_within_the_bar():
    """
    A syncopated chord change (stage 1's "A>B" token) keeps
    its true half-beat position inside the bar it lands in -
    the same position that now drives real audio timing too
    (make_accompaniment strikes at a chord's own start).
    """

    pitches = "C4 D4 E4 F4 G4 A4 B4 C5"
    durations = "1 1 1 1 1 1 1 1"
    chart = "| Em . . D>G | Am . . . |"

    strip = _timeline(
        pitches, durations, "C", 120, chart, "", None
    )

    assert strip[0]["chords"] == [
        {"name": "Em", "beat_in_bar": 0.0, "carried": False},
        {"name": "D", "beat_in_bar": 3.0, "carried": False},
        {"name": "G", "beat_in_bar": 3.5, "carried": False}
    ]


def test_an_instrumental_intro_bar_is_present_and_wordless():
    """
    The original symptom this shape fix was built for: an
    intro held by one chord across several bars used to be
    invisible on the strip entirely (one box for the whole
    span, nothing for the bars inside it). Now every bar
    gets a box, whether or not anything is sung in it.
    """

    pitches = "R R R R C4 D4 E4 F4"
    durations = "1 1 1 1 1 1 1 1"
    lyrics = "here we go now"
    chart = "| Em . . . | D . G . |"

    strip = _timeline(
        pitches, durations, "C", 120, chart, lyrics, None
    )

    assert len(strip) == 2
    assert strip[0]["words"] == ""
    assert strip[0]["chords"] == [
        {"name": "Em", "beat_in_bar": 0.0, "carried": False}
    ]
    assert strip[1]["words"]


def test_each_bar_carries_the_key_in_force_there():
    """
    A modulating piece's own bars each know their own key
    (Piece.key_at, the same lookup transpose and harmony
    already use) - needed so the mixer's diagram panel can
    show the right key's Scale overlay at the playhead
    rather than the opening key for the whole song.
    """

    pitches = "C4 C4 C4 C4 G4 G4 G4 G4"
    durations = "1 1 1 1 1 1 1 1"
    key = "C, G from beat 4"
    chart = "| C . . . | G . . . |"

    strip = _timeline(pitches, durations, key, 120, chart, "", None)

    assert strip[0]["key"] == "C"
    assert strip[1]["key"] == "G"


def test_diagrams_build_a_scale_overlay_per_distinct_key():
    """
    The bug this fix replaced: _diagrams used to reject the
    key box's own multi-key text outright ("key not in
    MAJOR_SCALES"), sending back an empty dict and leaving
    the whole diagram panel blank for any modulating piece -
    not just the Scale layer, everything, since the guard
    sat before structure/chords/shapes were built too.
    """

    pitches = "C4 C4 C4 C4 G4 G4 G4 G4"
    durations = "1 1 1 1 1 1 1 1"
    key = "C, G from beat 4"
    chart = "| C . . . | G . . . |"

    strip = _timeline(pitches, durations, key, 120, chart, "", None)

    diagrams = _diagrams(key, strip)

    # Not empty - the whole-panel outage this fix closes.
    assert diagrams

    assert set(diagrams["scale"].keys()) == {"C", "G"}

    from instrument_diagrams import INSTRUMENTS

    for instruments in diagrams["scale"].values():
        assert set(instruments.keys()) == set(INSTRUMENTS)

    # The two keys' own Scale pictures genuinely differ -
    # not the same overlay duplicated under two names.
    assert (
        diagrams["scale"]["C"]["Piano, 3 octaves"]
        != diagrams["scale"]["G"]["Piano, 3 octaves"]
    )


def test_the_faders_start_where_the_sliders_did():
    """
    The song in its own pure form - melody, bass, chords -
    with a click under it and only the harmonies silent,
    since those are what's being practised, not the rest of
    the song.
    """

    assert OPENING_LEVELS["Melody"] == 1.0
    assert OPENING_LEVELS["Bass"] == 1.0
    assert OPENING_LEVELS["Chords"] == 1.0
    assert OPENING_LEVELS["Metronome"] > 0

    for name in ("Harmony above", "Harmony below"):
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
        "bpm", "parts", "part", "loop_start", "loop_end"
    }

    # An ordinary, undivided song has no tunes of its own to
    # choose between, and says so with an empty list rather
    # than a list of one - which is how the browser knows
    # not to offer a chooser at all.
    assert value["parts"] == []
    assert value["part"] is None

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
    # (always-there background), and the scale base for
    # every distinct key the piece actually uses (one entry
    # in the ordinary, single-key case), and one chord
    # overlay per chord name the chart actually printed on
    # the strip.
    from instrument_diagrams import INSTRUMENTS

    assert set(value["diagrams"]["structure"].keys()) == set(INSTRUMENTS)

    assert set(value["diagrams"]["scale"].keys()) == {key}

    for instruments in value["diagrams"]["scale"].values():
        assert set(instruments.keys()) == set(INSTRUMENTS)

    chart_chord_names = {
        chord["name"]
        for bar in value["timeline"]
        for chord in bar["chords"]
    }

    assert (
        set(value["diagrams"]["chords"]["Piano, 3 octaves"].keys())
        == chart_chord_names
    )

    # shapes is the beginner-voicing alternative to chords -
    # present for every instrument key, but only actually
    # populated where a standard shape exists. Piano covers
    # every quality this app supports, so its shapes should
    # match chords exactly for this song's chart.
    assert set(value["diagrams"]["shapes"].keys()) == set(INSTRUMENTS)

    assert (
        set(value["diagrams"]["shapes"]["Piano, 3 octaves"].keys())
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

    # "Both positions" now has a genuine second shape - a
    # real double stop in third position, not first
    # position's shape reused - so it draws both, differing
    # from "Violin, first position" wherever the chart has a
    # chord at all, using the same SHAPE_COLOUR/
    # HIGHER_SHAPE_COLOUR split guitar and ukulele's own
    # higher positions already use.
    from instrument_diagrams import SHAPE_COLOUR, HIGHER_SHAPE_COLOUR

    both_shapes = value["diagrams"]["shapes"]["Violin, both positions"]
    first_shapes = value["diagrams"]["shapes"]["Violin, first position"]

    assert set(both_shapes.keys()) == chart_chord_names

    for chord_name in chart_chord_names:
        assert both_shapes[chord_name] != first_shapes[chord_name]
        assert SHAPE_COLOUR in both_shapes[chord_name]
        assert HIGHER_SHAPE_COLOUR in both_shapes[chord_name]

    # Structure and scale must be different pictures, not
    # the same one under two names - the bug that shipped
    # the combined diagram as "scale" and left nothing for
    # an always-there background.
    structure_piano = value["diagrams"]["structure"]["Piano, 3 octaves"]
    scale_piano = value["diagrams"]["scale"][key]["Piano, 3 octaves"]

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

# Several tunes in one song - PLAN-multi-part.md stage 1.

def test_a_several_tune_song_sends_a_layer_per_tune():
    """
    Each tune is its own sound, named as the divider names
    it, so a group can hear all of them and mute the ones
    that are not theirs. The derived layers follow after.
    """

    from examples import load_partner_songs

    pitches, durations, lyrics, key, chart, tempo = load_partner_songs()

    value = mixer_data(
        pitches, durations, key, tempo, chart,
        lyric_text=lyrics, part_label="Three Blind Mice"
    )

    names = [layer["name"] for layer in value["layers"]]

    assert names[:2] == [
        "Three Blind Mice", "Frere Jacques"
    ]

    for derived in ("Harmony above", "Bass", "Chords", "Metronome"):
        assert derived in names

    # The tunes come first, before anything derived from them.
    assert names.index("Frere Jacques") < names.index("Harmony above")


def test_the_chosen_tune_rides_on_the_value_both_ways():
    """
    parts says what there is to choose between; part says
    which is being sung. The browser sends part back when a
    person picks another, so both have to be there.
    """

    from examples import load_partner_songs

    pitches, durations, lyrics, key, chart, tempo = load_partner_songs()

    value = mixer_data(
        pitches, durations, key, tempo, chart,
        lyric_text=lyrics, part_label="Frere Jacques"
    )

    assert value["parts"] == [
        "Three Blind Mice", "Frere Jacques"
    ]
    assert value["part"] == "Frere Jacques"


def test_a_stale_tune_name_falls_back_rather_than_failing():
    """
    A name left over from another song must never stop the
    music being read - the chooser is a view, the same way
    the phrase dropdown is.
    """

    from examples import load_partner_songs

    pitches, durations, lyrics, key, chart, tempo = load_partner_songs()

    value = mixer_data(
        pitches, durations, key, tempo, chart,
        lyric_text=lyrics, part_label="Some Other Song"
    )

    assert value["part"] == "Three Blind Mice"


def test_every_tune_carries_its_own_words():
    """
    Unlike the generated harmony and bass, each tune of a
    several-tune song is really sung and really has lyrics.
    """

    from examples import load_partner_songs

    pitches, durations, lyrics, key, chart, tempo = load_partner_songs()

    value = mixer_data(
        pitches, durations, key, tempo, chart,
        lyric_text=lyrics, part_label="Frere Jacques"
    )

    for tune in ("Three Blind Mice", "Frere Jacques"):

        worded = [
            note for note in value["notes"]
            if note["layer"] == tune and note.get("word")
        ]

        assert worded, f"{tune} sent no words"

    # The derived lines still carry none.
    for derived in ("Harmony above", "Bass"):

        assert not [
            note for note in value["notes"]
            if note["layer"] == derived and note.get("word")
        ]


def test_phrases_follow_the_tune_being_sung():
    """
    Each tune has its own words and so its own lines to
    sing; the phrase strip must follow the one being sung
    rather than the first one written.
    """

    from examples import load_partner_songs

    pitches, durations, lyrics, key, chart, tempo = load_partner_songs()

    value = mixer_data(
        pitches, durations, key, tempo, chart,
        lyric_text=lyrics, part_label="Frere Jacques"
    )

    labels = [phrase["label"] for phrase in value["phrases"]]

    assert labels
    assert "Fre" in labels[0]


def test_part_selected_reads_the_browsers_choice():
    from mixer_data import part_selected

    assert part_selected(None) is None
    assert part_selected({}) is None
    assert part_selected({"part": "Three Blind Mice"}) == "Three Blind Mice"