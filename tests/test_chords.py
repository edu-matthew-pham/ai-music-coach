"""
Chord charts.

A chart is a grid: bars of beat slots saying what sounds
underneath. The melody is not a grid, and does not have to
agree with it note for note - a chord spans many notes, a
syncopated melody crosses the bar lines. The two only have
to last the same time.
"""

import pytest

from chords import (
    ChartError,
    read_chart,
    chart_beats,
    chord_at,
    chord_semitones,
    chord_root,
    split_chord,
    describe_chart
)
from music import read_chords, MusicInputError


def test_a_chord_lasts_as_long_as_its_dots():
    chords, bars = read_chart("| Dm . Bb . |")

    assert chords == [
        (0.0, 2.0, "Dm"),
        (2.0, 2.0, "Bb")
    ]


def test_a_chord_on_every_beat():
    chords, bars = read_chart("| C G Am F |")

    assert len(chords) == 4

    for start, length, name in chords:
        assert length == 1.0


def test_the_bars_declare_the_metre():
    """
    Three slots is three four and four slots is four four.
    Nothing has to be told the time signature separately.
    """

    chords, bars = read_chart("| Dm . . | F . . |")

    assert bars == [(0.0, 3.0), (3.0, 3.0)]

    assert "3 beats to the bar" in describe_chart(
        "| Dm . . | F . . |"
    )


def test_bars_may_change_length():
    chords, bars = read_chart("| C . . . | G . . |")

    assert bars == [(0.0, 4.0), (4.0, 3.0)]

    assert "changing" in describe_chart("| C . . . | G . . |")


def test_a_chart_must_begin_with_a_bar_line():
    with pytest.raises(ChartError, match="begins with a bar line"):
        read_chart("Dm . Bb .")


def test_a_chart_cannot_begin_with_a_dot():
    with pytest.raises(ChartError, match="no chord to carry on"):
        read_chart("| . Dm |")


def test_an_unknown_chord_is_reported():
    with pytest.raises(ChartError, match="not a chord this app knows"):
        read_chart("| Dwhatever . |")


def test_something_that_is_not_a_chord_at_all():
    with pytest.raises(ChartError, match="does not start with a note"):
        read_chart("| Hm . |")


def test_chord_names_split_into_root_and_quality():
    assert split_chord("Dm") == ("D", "m")
    assert split_chord("Bbmaj7") == ("Bb", "maj7")
    assert split_chord("F#m7") == ("F#", "m7")
    assert split_chord("C") == ("C", "")


def test_chord_tones():
    # D minor is D, F, A.
    assert sorted(chord_semitones("Dm")) == [2, 5, 9]

    # G7 is G, B, D, F.
    assert sorted(chord_semitones("G7")) == [2, 5, 7, 11]


def test_the_root_is_what_a_bass_line_sings():
    assert chord_root("Bb") == 10
    assert chord_root("F#m7") == 6


def test_the_chord_at_a_moment():
    chords, bars = read_chart("| Dm . Bb . |")

    assert chord_at(chords, 0.0) == "Dm"
    assert chord_at(chords, 1.9) == "Dm"
    assert chord_at(chords, 2.0) == "Bb"
    assert chord_at(chords, 99) is None


def test_a_note_takes_the_chord_it_begins_under():
    """
    A note held across a change keeps the identity it
    started with, which is what lets a suspension resolve
    rather than simply sound wrong.
    """

    chords, bars = read_chart("| Dm . Bb . |")

    # A note starting on beat one and lasting three beats
    # belongs to D minor, however far it runs.
    assert chord_at(chords, 1.0) == "Dm"


def test_the_chart_must_last_as_long_as_the_music():
    with pytest.raises(MusicInputError, match="same length"):
        read_chords("| C . . . |", [1.0, 1.0])


def test_the_mismatch_says_what_both_lengths_are():
    try:
        read_chords("| C . . . | G . . . |", [1.0, 1.0, 1.0])

    except MusicInputError as problem:
        assert "8 beats" in str(problem)
        assert "3 beats" in str(problem)
        assert "2 bars" in str(problem)


def test_chords_are_optional():
    assert read_chords("", [1.0, 1.0]) == ([], [])
    assert read_chords(None, [1.0, 1.0]) == ([], [])


def test_a_syncopated_melody_needs_no_alignment():
    """
    The chart is a grid and the melody is not. They only
    have to last the same time.
    """

    # Notes that begin off the beat and tie across the bar.
    durations = [0.5, 1.5, 2.0, 1.5, 2.5]

    chords, bars = read_chords(
        "| Dm . Bb . | F . . . |",
        durations
    )

    assert len(chords) == 3


def test_chart_beats_counts_the_whole_chart():
    assert chart_beats("| C . . . | G . . . |") == 8.0
    assert chart_beats("") == 0.0


def test_chord_symbols_are_drawn_above_the_music():
    """
    A chart belongs above the notes, as a lead sheet
    prints it.
    """

    from tuning_plot import make_performance_plot

    chords, bars = read_chart("| C . . . | F . C . |")

    figure = make_performance_plot(
        ["C4", "E4", "G4", "C5", "G4", "E4", "C4", "C4"],
        [1.0] * 8,
        120,
        None,
        chords=chords,
        bars=bars
    )

    axes = figure.axes[0]

    labels = [text.get_text() for text in axes.texts]

    assert labels.count("C") >= 2
    assert "F" in labels

    # Above the highest note, not among the boxes.
    lowest, highest = axes.get_ylim()

    for text in axes.texts:
        if text.get_text() in ("C", "F"):
            assert text.get_position()[1] > highest - 2


def test_bar_lines_are_drawn_for_every_bar():
    from tuning_plot import make_performance_plot

    chords, bars = read_chart("| C . . . | F . . . | G . . . |")

    figure = make_performance_plot(
        ["C4"] * 12,
        [1.0] * 12,
        120,
        None,
        chords=chords,
        bars=bars
    )

    axes = figure.axes[0]

    # One at the start of each bar and one at the end.
    assert len(axes.lines) >= len(bars) + 1


def test_a_picture_without_chords_is_unchanged():
    """
    Chords are optional, and music without them draws
    exactly as it did before.
    """

    from tuning_plot import make_performance_plot

    figure = make_performance_plot(
        ["C4", "E4"], [1.0, 1.0], 120, None
    )

    assert len(figure.axes[0].lines) == 0


def test_the_downbeat_is_marked():
    """
    A run of clicks says how fast but not where. Marking
    the first beat of each bar is what lets a singer count
    a phrase in.
    """

    import numpy as np

    from playback import add_metronome

    silence = [0.0] * int(8 * 0.5 * 8000)

    clicks = np.array(
        add_metronome(
            silence, 8, 120, 8000,
            bars=[(0.0, 4.0), (4.0, 4.0)]
        )
    )

    def loudest_at(beat):
        start = int(beat * 0.5 * 8000)
        return float(np.max(np.abs(clicks[start:start + 200])))

    for downbeat in (0, 4):
        for ordinary in (1, 2, 3):
            assert loudest_at(downbeat) > loudest_at(ordinary)


def test_bars_of_three_accent_every_third_beat():
    import numpy as np

    from playback import add_metronome

    silence = [0.0] * int(6 * 0.5 * 8000)

    clicks = np.array(
        add_metronome(
            silence, 6, 120, 8000,
            bars=[(0.0, 3.0), (3.0, 3.0)]
        )
    )

    def loudest_at(beat):
        start = int(beat * 0.5 * 8000)
        return float(np.max(np.abs(clicks[start:start + 200])))

    assert loudest_at(3) > loudest_at(2)
    assert loudest_at(3) > loudest_at(4)


def test_without_a_chart_every_click_is_the_same():
    """
    Music with no chart has no bars, so nothing is
    accented and the metronome behaves as it always did.
    """

    import numpy as np

    from playback import add_metronome

    silence = [0.0] * int(4 * 0.5 * 8000)

    clicks = np.array(
        add_metronome(silence, 4, 120, 8000)
    )

    loudest = [
        float(np.max(np.abs(
            clicks[int(beat * 0.5 * 8000):int(beat * 0.5 * 8000) + 200]
        )))
        for beat in range(4)
    ]

    assert max(loudest) - min(loudest) < 0.01


def test_a_chord_is_voiced_below_a_singer():
    """
    Chords in the singer's own octave muddy the line they
    are meant to support.
    """

    from playback import voice_chord, CHORD_HIGHEST_MIDI

    for name in ["C", "Dm", "G7", "Bb"]:

        voiced = voice_chord(chord_semitones(name))

        assert len(voiced) >= 3

        for midi_number in voiced:
            assert midi_number <= CHORD_HIGHEST_MIDI

        # Opening upward, not bunched at the bottom.
        assert voiced == sorted(voiced)
        assert len(set(voiced)) == len(voiced)


def test_a_plucked_string_dies_away():
    """
    Starting loud and fading is most of what makes a
    string sound plucked rather than pressed.
    """

    from playback import make_pluck

    # Long enough to hear the decay: a guitar chord rings
    # well past a beat, which is the point of it.
    string = make_pluck(220, 3.0, 8000, loud=1.0)

    beginning = max(abs(value) for value in string[:400])
    end = max(abs(value) for value in string[-400:])

    assert beginning > end * 5


def test_the_chord_sounds_again_on_each_bar_line():
    """
    A chord held for several bars would ring once and
    leave the singer with nothing underneath at exactly
    the point a long note is hardest to hold.
    """

    import numpy as np

    from playback import make_accompaniment

    # One chord lasting two whole bars.
    chords = [(0.0, 8.0, chord_semitones("C"))]
    bars = [(0.0, 4.0), (4.0, 4.0)]

    sound = np.array(
        make_accompaniment(chords, bars, 8, 120, 8000)
    )

    def peak_at(beat):
        start = int(beat * 0.5 * 8000)
        return float(np.max(np.abs(sound[start:start + 400])))

    # Struck at the start of each bar, quiet by the end of
    # one.
    assert peak_at(4) > peak_at(3) * 3
    assert peak_at(0) > peak_at(3) * 3


def test_no_chart_means_no_accompaniment():
    from playback import make_accompaniment

    sound = make_accompaniment([], [], 4, 120, 8000)

    assert max(abs(value) for value in sound) == 0


def test_chords_mix_with_the_melody():
    import numpy as np

    from music import play_music, load_twinkle_phrase

    pitches, durations, lyrics, key, chart = load_twinkle_phrase()

    rate, with_chords = play_music(
        pitches, durations, key,
        melody_on=True, harmony_on=False, bpm=120,
        metronome=False, chart_text=chart, chords_on=True
    )

    rate, without = play_music(
        pitches, durations, key,
        melody_on=True, harmony_on=False, bpm=120,
        metronome=False, chart_text=chart, chords_on=False
    )

    assert len(with_chords) == len(without)
    assert not np.allclose(with_chords, without)


def test_a_ringing_chord_is_damped_not_cut():
    """
    A string still sounding when the chord changes has to
    be damped, or the waveform jumps and the change
    arrives with a click on it.
    """

    import numpy as np

    from playback import make_chord

    sound = np.array(
        make_chord(chord_semitones("C"), 2, 120, 8000)
    )

    # Whatever is left at the end is near silence, so the
    # next chord starts from nothing.
    assert abs(float(sound[-1])) < 0.01


def test_layers_together_do_not_clip():
    """
    Four layers add up past what a speaker can play, and
    the result is not loud but broken.
    """

    import numpy as np

    from music import play_music, load_twinkle_phrase

    pitches, durations, lyrics, key, chart = load_twinkle_phrase()

    rate, audio = play_music(
        pitches, durations, key,
        melody_on=True, harmony_on=True, bpm=100,
        metronome=True, chart_text=chart, chords_on=True
    )

    assert float(np.max(np.abs(audio))) <= 1.0


def test_quiet_music_is_left_alone():
    """
    The limiter only acts when it has to, so a single
    quiet layer keeps its level.
    """

    from playback import keep_in_range

    quiet = [0.1, -0.2, 0.3]

    assert keep_in_range(quiet) == quiet


def test_the_sour_third_is_corrected():
    """
    Parallel thirds put A under C over a C chord: the one
    sour moment in Twinkle. Chord correction takes the
    fifth of the chord instead, and touches nothing else,
    because every other third already is a chord tone -
    triads being stacked thirds.
    """

    from harmony import make_harmony, make_chord_harmony

    pitches = ["C4", "C4", "G4", "G4", "A4", "A4", "G4"]
    durations = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 2.0]

    chords, bars = read_chart("| C . . . | F . C . |")

    voiced = [
        (start, length, chord_semitones(name))
        for start, length, name in chords
    ]

    parallel = make_harmony(pitches, key="C")

    corrected = make_chord_harmony(
        pitches, durations, voiced, "C", -2,
        "Thirds, chord-corrected"
    )

    assert parallel[0] == "A3"
    assert corrected[0] == "G3"

    # Everything after the repair is the parallel line.
    assert corrected[2:] == parallel[2:]


def test_chord_tones_follow_the_harmony_not_the_tune():
    """
    Where corrected thirds shadow the melody, chord tones
    take the nearest note of the chord below it, which is
    an arranged inner voice rather than a duet partner.
    """

    from harmony import make_chord_harmony

    # A melody leaping about over one chord.
    pitches = ["C4", "E4", "C5", "G4"]
    durations = [1.0, 1.0, 1.0, 1.0]

    chords, bars = read_chart("| C . . . |")

    voiced = [
        (start, length, chord_semitones(name))
        for start, length, name in chords
    ]

    line = make_chord_harmony(
        pitches, durations, voiced, "C", -2,
        "Chord tones"
    )

    # Every note belongs to the chord, and sits below the
    # melody it supports.
    from notes import note_to_midi

    for position in range(len(line)):

        assert note_to_midi(line[position]) % 12 in voiced[0][2]
        assert note_to_midi(line[position]) < note_to_midi(
            pitches[position]
        )


def test_a_dissonant_melody_note_is_left_alone():
    """
    A melody note outside its own chord is the composer's
    dissonance, not ours to repair: it keeps its parallel
    third rather than being harmonised as something else.
    """

    from harmony import make_harmony, make_chord_harmony

    # D over a C chord: a deliberate passing dissonance.
    pitches = ["C4", "D4", "E4"]
    durations = [1.0, 1.0, 2.0]

    chords, bars = read_chart("| C . . . |")

    voiced = [
        (start, length, chord_semitones(name))
        for start, length, name in chords
    ]

    parallel = make_harmony(pitches, key="C")

    corrected = make_chord_harmony(
        pitches, durations, voiced, "C", -2,
        "Thirds, chord-corrected"
    )

    assert corrected[1] == parallel[1]


def test_without_a_chart_every_style_is_parallel_thirds():
    """
    The style choice is always safe to make: with no
    chords to read, every style comes out the same.
    """

    from music import harmony_line

    pitches = ["C4", "E4", "G4"]
    durations = [1.0, 1.0, 1.0]

    plain = harmony_line(pitches, durations, "C")

    for style in [
        "Thirds, chord-corrected",
        "Chord tones"
    ]:
        assert harmony_line(
            pitches, durations, "C",
            style=style, chart_text=""
        ) == plain


def test_the_bass_sings_the_root_of_each_chord():
    """
    A bass part does not follow the melody. It sings one
    note per chord and holds it while the tune moves, which
    is what tells everyone else where the harmony is.
    """

    from harmony import make_bass
    from notes import note_to_midi

    pitches = ["C4", "C4", "G4", "G4", "A4", "A4", "G4"]
    durations = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 2.0]

    chords, bars = read_chart("| C . . . | F . C . |")

    voiced = [
        (start, length, chord_semitones(name))
        for start, length, name in chords
    ]

    line = make_bass(pitches, durations, voiced)

    # One note per chord, repeated: C, C, C, C, F, F, C.
    assert line == [
        "C3", "C3", "C3", "C3", "F2", "F2", "C3"
    ]

    # And every note is the root, not just any chord tone.
    for position in range(len(line)):

        beat = sum(durations[:position])

        for start, length, tones in voiced:
            if start <= beat < start + length:
                assert note_to_midi(line[position]) % 12 == tones[0]


def test_the_bass_sits_below_the_singer():
    from harmony import make_bass, BASS_HIGHEST_MIDI
    from notes import note_to_midi

    chords, bars = read_chart("| G . . . |")

    voiced = [
        (start, length, chord_semitones(name))
        for start, length, name in chords
    ]

    line = make_bass(["G4"] * 4, [1.0] * 4, voiced)

    for note in line:
        assert note_to_midi(note) <= BASS_HIGHEST_MIDI


def test_a_bass_part_needs_chords():
    """
    Without a chart there is no root to sing, and saying
    so is more use than a line of silence.
    """

    from music import part_notes, MusicInputError

    with pytest.raises(MusicInputError, match="needs a chord chart"):
        part_notes(
            ["C4", "E4"], "Bass", "C",
            durations=[1.0, 1.0], chart_text=""
        )


def test_a_bass_performance_is_judged_against_the_bass():
    import numpy as np

    from playback import make_melody
    from music import analyse_performance, load_twinkle_phrase

    pitches, durations, lyrics, key, chart = load_twinkle_phrase()

    rate, sound = make_melody(
        ["C3", "C3", "C3", "C3", "F2", "F2", "C3", "R"],
        [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.5, 0.5],
        120, 8000
    )

    text, performance, tuning = analyse_performance(
        (rate, np.array(sound)),
        pitches, durations, 120,
        part="Bass", key=key, chart_text=chart
    )

    assert "7 of 7" in text
    assert "bass part" in text


def test_bass_is_offered_as_a_part():
    from music import PART_CHOICES

    assert "Bass" in PART_CHOICES


def test_bass_is_a_playback_layer_too():
    """
    A part you can be judged on is a part you should be
    able to hear, so bass appears among the layers as well
    as among the parts.
    """

    import numpy as np

    from music import play_music, load_twinkle_phrase

    pitches, durations, lyrics, key, chart = load_twinkle_phrase()

    common = dict(
        melody_on=True, harmony_on=False, bpm=120,
        metronome=False, chart_text=chart
    )

    rate, without = play_music(
        pitches, durations, key, bass_on=False, **common
    )

    rate, with_bass = play_music(
        pitches, durations, key, bass_on=True, **common
    )

    assert not np.allclose(without, with_bass)


def test_the_bass_layer_needs_a_chart_too():
    from music import play_music, MusicInputError

    with pytest.raises(MusicInputError, match="needs a chord chart"):
        play_music(
            "C4 C4", "1 1", "C",
            melody_on=False, harmony_on=False, bpm=120,
            chart_text="", bass_on=True
        )


def test_the_bass_appears_on_the_picture():
    """
    A part you can hear should be a part you can see.
    """

    from tuning_plot import make_performance_plot

    figure = make_performance_plot(
        ["C4", "C4", "G4", "G4"],
        [1.0] * 4,
        120,
        None,
        harmony=["A3", "A3", "E4", "E4"],
        bass=["C3", "C3", "C3", "C3"]
    )

    labels = [text.get_text() for text in figure.axes[0].texts]

    assert "C3" in labels
    assert "A3" in labels
    assert "C4" in labels


def test_each_voice_has_its_own_colour():
    from tuning_plot import (
        make_performance_plot,
        HARMONY_COLOUR,
        BASS_COLOUR
    )

    figure = make_performance_plot(
        ["C4", "C4"],
        [1.0, 1.0],
        120,
        None,
        harmony=["A3", "A3"],
        bass=["C3", "C3"]
    )

    colours = {
        text.get_color()
        for text in figure.axes[0].texts
    }

    assert HARMONY_COLOUR in colours
    assert BASS_COLOUR in colours
    assert HARMONY_COLOUR != BASS_COLOUR


def test_the_axis_names_the_notes_of_the_key():
    """
    With a key, the pitch labels are its scale: seven to
    the octave, every one meaningful, and the axis itself
    becomes a picture of where the key sits.
    """

    from tuning_plot import make_performance_plot

    figure = make_performance_plot(
        ["C5", "C5"],
        [1.0, 1.0],
        120,
        None,
        bass=["C3", "C3"],
        key="C"
    )

    labels = [
        text.get_text()
        for text in figure.axes[0].get_yticklabels()
    ]

    # White notes only: no sharps anywhere on a C axis.
    assert "C4" in labels
    assert all("#" not in label for label in labels)


def test_a_wide_range_grows_the_figure():
    """
    Three voices spread out rather than being squeezed
    into the same four inches as one.
    """

    from tuning_plot import make_performance_plot

    narrow = make_performance_plot(
        ["C4", "E4"], [1.0, 1.0], 120, None
    )

    wide = make_performance_plot(
        ["C5", "C5"], [1.0, 1.0], 120, None,
        bass=["E2", "E2"]
    )

    assert wide.get_size_inches()[1] > narrow.get_size_inches()[1]


def test_flat_keys_spell_their_notes_in_flats():
    """
    In F major the fourth is Bb. An axis saying A# there
    is the same sound spelled in the wrong dialect.
    """

    from tuning_plot import make_performance_plot

    figure = make_performance_plot(
        ["Bb3", "C4"], [1.0, 1.0], 120, None, key="F"
    )

    labels = [
        text.get_text()
        for text in figure.axes[0].get_yticklabels()
    ]

    assert "Bb3" in labels
    assert "A#3" not in labels


def test_sharp_keys_keep_their_sharps():
    from notes import midi_to_note

    assert midi_to_note(58, "F") == "Bb3"
    assert midi_to_note(58, "D") == "A#3"
    assert midi_to_note(58) == "A#3"