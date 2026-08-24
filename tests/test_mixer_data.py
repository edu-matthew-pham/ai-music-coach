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
        "layers", "timeline", "notes", "phrases", "phrases_by_part",
        "diagrams", "bpm", "parts", "part", "loop_start", "loop_end"
    }

    # An ordinary, undivided song has no tunes of its own to
    # choose between, and says so with an empty list rather
    # than a list of one - which is how the browser knows
    # not to offer a chooser at all.
    assert value["parts"] == []
    assert value["part"] is None
    assert value["phrases_by_part"] == {}

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


def test_a_stale_part_name_does_not_survive_into_a_one_tune_song():
    """
    build_mixer carries the tune being sung across a rebuild,
    so a singer editing a box is not bounced back to part 1.
    Load the partner song, sing "Three Blind Mice", then load
    the Wellerman: that name means nothing here, and an
    undivided song has no names at all, so it must come back
    as None rather than reach the browser. Left in, the
    Lyrics panel looked for words on a tune the song did not
    contain and showed nothing, while the Notes panel (which
    does not filter by that name) still showed every word -
    the exact split seen on a real screenshot.
    """

    pitches, durations, lyrics, key, chart, tempo = load_wellerman()

    value = mixer_data(
        pitches, durations, key, tempo, chart,
        lyric_text=lyrics, part_label="Three Blind Mice"
    )

    assert value["parts"] == []
    assert value["part"] is None

    # What the Lyrics panel would then read, by its own rule.
    mine = value["part"] or "Melody"
    assert [n for n in value["notes"] if n["layer"] == mine and n.get("word")]


def test_every_tunes_phrases_are_sent_by_name():
    """
    Showing two singers' words side by side needs each
    tune's own lines, not just the chosen one's.
    """

    from examples import load_partner_songs

    pitches, durations, lyrics, key, chart, tempo = load_partner_songs()

    value = mixer_data(
        pitches, durations, key, tempo, chart,
        lyric_text=lyrics, part_label="Three Blind Mice"
    )

    by_part = value["phrases_by_part"]

    assert set(by_part) == {"Three Blind Mice", "Frere Jacques"}
    assert "Three blind mice" in by_part["Three Blind Mice"][0]["label"]
    assert "Fre" in by_part["Frere Jacques"][0]["label"]

    # The chosen tune's own phrases come first, unchanged;
    # after they finish, the pages carry on with the other
    # part's (see _continue_with_other_parts), so the full
    # list is a superset, not an exact match.
    own = by_part["Three Blind Mice"]
    assert value["phrases"][:len(own)] == own
    assert len(value["phrases"]) >= len(own)


def test_pages_carry_on_with_other_parts_once_yours_has_finished():
    """
    A round's first voice finishes bars before the piece does.
    Its own phrases end where its singing does; after that,
    the pages follow whoever is still singing - each carried-
    on phrase labelled and tagged with the part it belongs to,
    with no gap and nothing of the tail left unshown.
    """

    from examples import load_row_your_boat

    pitches, durations, lyrics, key, chart, tempo = load_row_your_boat()

    value = mixer_data(
        pitches, durations, key, tempo, chart,
        lyric_text=lyrics, part_label="Voice 1"
    )

    phrases = value["phrases"]

    own = [ph for ph in phrases if not ph.get("part")]
    carried = [ph for ph in phrases if ph.get("part")]

    assert len(own) == 4
    assert carried, "nothing carried on after Voice 1 finished"

    # Everything carried on belongs to another part, and is
    # said so - not silently pretending to be Voice 1's.
    for ph in carried:
        assert ph["part"] != "Voice 1"
        assert ph["label"].startswith(ph["part"] + ":")

    # No hole from your last page into the tail, none within
    # it, and coverage right to the end.
    joined = [own[-1]] + carried
    for earlier, later in zip(joined, joined[1:]):
        assert abs(later["start"] - earlier["end"]) < 1e-6, (
            f"gap between {earlier['label']!r} and {later['label']!r}"
        )

    assert abs(phrases[-1]["end"] - value["timeline"][-1]["end"]) < 1e-6


def test_the_last_voice_of_a_round_carries_nothing_on():
    """
    Whoever finishes last has no one still singing after
    them - their pages are exactly their own, unchanged.
    """

    from examples import load_row_your_boat

    pitches, durations, lyrics, key, chart, tempo = load_row_your_boat()

    value = mixer_data(
        pitches, durations, key, tempo, chart,
        lyric_text=lyrics, part_label="Voice 3"
    )

    assert not [ph for ph in value["phrases"] if ph.get("part")]


def test_a_single_tune_song_is_untouched_by_carrying_on():
    from examples import load_wellerman

    pitches, durations, lyrics, key, chart, tempo = load_wellerman()

    value = mixer_data(
        pitches, durations, key, tempo, chart, lyric_text=lyrics
    )

    assert not [ph for ph in value["phrases"] if ph.get("part")]


# A synthetic several-tune piece built to hit the shapes the
# round example never produces: a voice that finishes in the
# MIDDLE (two others carrying on with DIFFERENT phrasing at
# that moment, so the overlap-merge branch runs), and a voice
# that only ENTERS after another has finished. Same technique
# as the multi-key tests' synthetic modulating score - typed
# directly, so every boundary is known to the beat.

def _staggered_piece():
    """
    Three tunes over eight bars of 4/4:

      Lead    sings bars 1-4, then rests           (finishes first)
      Alto    sings bars 3-8, phrases 3-5 / 6-8    (starts mid-way,
                                                    straddles Lead's end)
      Tenor   rests bars 1-4, sings 5-8            (enters only after
                                                    Lead has finished)

    Lead's last phrase ends at bar 4; Alto's phrase 1 (bars
    3-5) is still going then, so it must be clipped to start
    at bar 5 not skipped; Tenor's first phrase starts exactly
    at bar 5, alongside Alto's clipped one - the merge branch.
    """

    bar_rest_p, bar_rest_d = "R", "4"

    lead_p = " ".join(["C4 D4 E4 F4"] * 2 + ["G4 A4 G4 F4"] * 2) + " " + " ".join([bar_rest_p] * 4)
    lead_d = " ".join(["1 1 1 1"] * 4) + " " + " ".join([bar_rest_d] * 4)
    lead_l = "one two three four\nfive six sev- en\neight nine ten el-\nev- en twelve thir-"

    alto_p = " ".join([bar_rest_p] * 2) + " " + " ".join(["E4 F4 G4 A4"] * 6)
    alto_d = " ".join([bar_rest_d] * 2) + " " + " ".join(["1 1 1 1"] * 6)
    alto_l = "a b c d e f g h i j k l\nm n o p q r s t u v w x"

    tenor_p = " ".join([bar_rest_p] * 4) + " " + " ".join(["C4 C4 C4 C4"] * 4)
    tenor_d = " ".join([bar_rest_d] * 4) + " " + " ".join(["1 1 1 1"] * 4)
    tenor_l = "la la la la la la la la\nla la la la la la la la"

    pitches = f"=== Lead ===\n{lead_p}\n=== Alto ===\n{alto_p}\n=== Tenor ===\n{tenor_p}"
    durations = f"=== Lead ===\n{lead_d}\n=== Alto ===\n{alto_d}\n=== Tenor ===\n{tenor_d}"
    lyrics = f"=== Lead ===\n{lead_l}\n=== Alto ===\n{alto_l}\n=== Tenor ===\n{tenor_l}"

    chart = "| " + " | ".join(["C . . ."] * 8) + " |"

    return pitches, durations, lyrics, "C", chart, 120


def test_synthetic_stagger_is_the_shape_it_claims_to_be():
    """
    Pin the fixture itself first, so a later edit to it can't
    silently stop exercising what the tests below rely on.
    """

    from piece import Piece
    from notes import is_rest

    pitches, durations, lyrics, key, chart, tempo = _staggered_piece()

    parts = dict(Piece.read_parts(pitches, durations, lyrics, key, chart, tempo))

    assert set(parts) == {"Lead", "Alto", "Tenor"}

    for piece in parts.values():
        assert abs(piece.beats() - 32.0) < 1e-9

    def first_sung(piece):
        return next(
            s for s, p in zip(piece.starts(), piece.pitches) if not is_rest(p)
        )

    assert first_sung(parts["Lead"]) == 0.0
    assert first_sung(parts["Alto"]) == 8.0
    assert first_sung(parts["Tenor"]) == 16.0


def test_a_middle_finisher_carries_on_with_both_remaining_voices():
    """
    Lead finishes at bar 4 (beat 16). Alto's first phrase
    straddles that moment and must be clipped, not skipped;
    Tenor's first phrase starts exactly there. Both continue,
    interleaved by time, with no gap and full coverage.
    """

    from mixer_data import mixer_data

    pitches, durations, lyrics, key, chart, tempo = _staggered_piece()

    value = mixer_data(
        pitches, durations, key, tempo, chart,
        lyric_text=lyrics, part_label="Lead"
    )

    phrases = value["phrases"]
    own = [ph for ph in phrases if not ph.get("part")]
    carried = [ph for ph in phrases if ph.get("part")]

    # Lead's own four lines, each ending where its singing
    # does - beat 16 for the last, no rest glued on.
    assert len(own) == 4
    lead_end = own[-1]["end"]
    assert abs(lead_end - 16 * (60.0 / tempo)) < 1e-6

    assert carried, "nothing carried on after Lead finished"

    # First carried-on phrase picks up exactly where Lead
    # ended - not at Alto's own phrase start (which was
    # earlier), and not with a hole.
    assert abs(carried[0]["start"] - lead_end) < 1e-6

    # After Lead's last sung note (beat 16 = 8.0s at 120bpm)
    # the pages are the UNION of Alto's and Tenor's phrase
    # boundaries: Alto breaks at 20 and 24 beats, Tenor at 24
    # only, so the tail is cut at 16, 20, 24 and the piece's
    # end - three pages, as fine as either part cuts it. Each
    # is owned by the part whose phrase begins at its cut.
    spb = 60.0 / tempo
    assert [(round(ph["start"] / spb), round(ph["end"] / spb), ph["part"])
            for ph in carried] == [
        (16, 20, "Alto"),
        (20, 24, "Alto"),
        (24, 32, "Tenor"),
    ]

    # No hole from your last page into the tail, none within
    # the tail, and coverage to the piece's end. (Gaps between
    # your OWN pages are allowed - a rest between two of your
    # lines belongs to neither page.)
    joined = [own[-1]] + carried
    for earlier, later in zip(joined, joined[1:]):
        assert abs(later["start"] - earlier["end"]) < 1e-6, (
            f"gap between {earlier['label']!r} and {later['label']!r}"
        )
    assert abs(phrases[-1]["end"] - value["timeline"][-1]["end"]) < 1e-6


def test_the_merge_keeps_one_phrase_per_stretch_of_time():
    """
    When two carried-on phrases cover the same seconds (Alto's
    clipped first line and Tenor's first line both start at
    beat 16), only one is kept for that stretch - a second
    page over the same seconds would just be the same notes
    drawn again.
    """

    from mixer_data import mixer_data

    pitches, durations, lyrics, key, chart, tempo = _staggered_piece()

    value = mixer_data(
        pitches, durations, key, tempo, chart,
        lyric_text=lyrics, part_label="Lead"
    )

    carried = [ph for ph in value["phrases"] if ph.get("part")]

    for earlier, later in zip(carried, carried[1:]):
        assert later["start"] >= earlier["end"] - 1e-6, (
            f"{earlier['label']!r} and {later['label']!r} overlap"
        )


def test_a_late_entrant_is_paged_when_it_is_the_singer():
    """
    Tenor rests four bars then sings. As the singer, its
    phrases start where it enters; nothing before that is a
    phrase of its own. And since it finishes last, nothing is
    carried on after it.
    """

    from mixer_data import mixer_data

    pitches, durations, lyrics, key, chart, tempo = _staggered_piece()

    value = mixer_data(
        pitches, durations, key, tempo, chart,
        lyric_text=lyrics, part_label="Tenor"
    )

    phrases = value["phrases"]

    assert not [ph for ph in phrases if ph.get("part")]

    # Its last phrase runs to the piece's end (it IS the last
    # thing sounding), and coverage is complete.
    assert abs(phrases[-1]["end"] - value["timeline"][-1]["end"]) < 1e-6


def test_carried_on_phrases_name_the_part_their_words_come_from():
    """
    A panel drawing words for a carried-on page has to fetch
    that part's words, not the singer's - the tag is what
    lets it.
    """

    from mixer_data import mixer_data

    pitches, durations, lyrics, key, chart, tempo = _staggered_piece()

    value = mixer_data(
        pitches, durations, key, tempo, chart,
        lyric_text=lyrics, part_label="Lead"
    )

    notes = value["notes"]

    for ph in value["phrases"]:
        if not ph.get("part"):
            continue

        # There ARE words from the named part inside this
        # window - the tag points at something real.
        inside = [
            n for n in notes
            if n["layer"] == ph["part"] and n.get("word")
            and ph["start"] <= n["start"] < ph["end"]
        ]
        assert inside, f"{ph['label']!r} tagged {ph['part']!r} but no words there"

# --- gap pages: instrumental stretches and long silences ---


def _gap_phrases(pitches, durations, lyrics):
    value = mixer_data(pitches, durations, "C", 120, "", lyric_text=lyrics)
    return value["phrases"]


def test_a_long_unsung_intro_becomes_its_own_pages():
    """
    An imported intro arrives as a line of held notes longer
    than any real melisma. That is nobody's phrase - it is
    paged on its own, greedily, four bars to a page, so a
    28-second intro is no longer one blank page a singer
    stares at.
    """

    # 24 beats of unsung holds (6 four-beat bars), then a
    # sung line. Greedy: one full 4-bar page, then the
    # 2-bar remainder as its own page (longer than the
    # 1-bar fold), then the singing.
    pitches = " ".join(["C4"] * 24 + ["E4", "F4", "G4", "A4"])
    durations = " ".join(["1"] * 28)
    lyrics = " ".join(["_"] * 24) + "\nHi there my friend"

    phrases = _gap_phrases(pitches, durations, lyrics)

    assert [p["label"] for p in phrases] == [
        "1. (instrumental)",
        "2. (instrumental)",
        "3. Hi there my friend",
    ]

    seconds_per_beat = 0.5

    assert phrases[0]["start"] == 0.0
    assert phrases[0]["end"] == 16 * seconds_per_beat
    assert phrases[1]["end"] == 24 * seconds_per_beat
    assert phrases[2]["start"] == 24 * seconds_per_beat


def test_a_short_gap_folds_into_the_next_phrase():
    """
    A rest of a bar or less between phrases is a breath, not
    a page: the next phrase starts where the last one ended,
    so no time on the strip belongs to nobody.
    """

    pitches = "C4 D4 E4 F4 R R G4 A4 B4 C5"
    durations = "1 1 1 1 1 1 1 1 1 1"
    lyrics = "One two three four\nFive six sev'n eight"

    phrases = _gap_phrases(pitches, durations, lyrics)

    assert len(phrases) == 2
    assert phrases[1]["start"] == phrases[0]["end"]


def test_a_long_silence_is_paged_as_rest():
    """
    Silence past a bar is real counting time - it gets its
    own page, named "(rest)" rather than "(instrumental)",
    because nothing sounds there for a singer to listen to;
    they are counting themselves in.
    """

    pitches = " ".join(
        ["C4", "D4", "E4", "F4"] + ["R"] * 8 + ["G4", "A4", "B4", "C5"]
    )
    durations = " ".join(["1"] * 16)
    lyrics = "One two three four\nFive six sev'n eight"

    phrases = _gap_phrases(pitches, durations, lyrics)

    assert [p["label"] for p in phrases] == [
        "1. One two three four",
        "2. (rest)",
        "3. Five six sev'n eight",
    ]


def test_a_trailing_unsung_run_splits_off_the_last_phrase():
    """
    An outro's held notes share a lyric line with the last
    sung words, so trimming by rests alone left them inside
    the phrase - a real page bloat seen on two uploaded
    songs before this trim treated "*" notes at a phrase's
    edges as the unowned time they are.
    """

    pitches = " ".join(
        ["C4", "D4", "E4", "F4"] + ["G4", "A4", "B4", "C5"] + ["G4"] * 8
    )
    durations = " ".join(["1"] * 16)
    lyrics = (
        "One two three four\n"
        "Five six sev'n eight " + " ".join(["_"] * 8)
    )

    phrases = _gap_phrases(pitches, durations, lyrics)

    assert phrases[1]["label"] == "2. Five six sev'n eight"
    assert phrases[1]["end"] == 8 * 0.5
    assert phrases[-1]["label"].endswith("(instrumental)")


def test_a_divided_song_pages_exactly_as_before():
    """
    In a song with several tunes, one voice's rests are not
    silence - another voice is singing there, and the
    carried-on paging owns that time. No gap pages, no
    folding: one page per lyric line, trimmed to the last
    sung note, same as always.
    """

    from examples import load_partner_songs

    pitches, durations, lyrics, key, chart, tempo = load_partner_songs()

    value = mixer_data(
        pitches, durations, key, tempo, chart, lyric_text=lyrics
    )

    for name, phrases in value["phrases_by_part"].items():
        for phrase in phrases:
            assert "(rest)" not in phrase["label"], name
            assert "(instrumental)" not in phrase["label"], name