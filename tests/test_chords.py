"""
Chord charts.

A chart is a grid: bars of beat slots saying what sounds
underneath. The melody is not a grid, and does not have to
agree with it note for note - a chord spans many notes, a
syncopated melody crosses the bar lines. The two only have
to last the same time.
"""

import os

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


def test_a_chord_arriving_just_before_a_bar_line_is_not_struck_twice():
    """
    A chord that arrives less than a beat before a bar line
    - a syncopated push onto the "and" of the last beat, say
    - would otherwise be struck once on its true arrival and
    then struck again almost immediately by the bar-line
    reinforcement rule, audibly doubling a note that was
    never meant to repeat. Found against a real recording
    (BUILDNOTES.md), not guessed: Mulan's Em arrives at beat
    63.5, half a beat before the bar line at 64.0.

    Proven by comparison rather than by reading a peak out
    of an ambiguous decay curve (a struck string's own ring
    can still be loud shortly after the strike, which is
    what made this bug easy to miss by ear the first time):
    with the bar line too close to matter, the sound must be
    bit-identical to having no bar-line information at all,
    since a genuine second strike would change the waveform.
    """

    import numpy as np

    from playback import make_accompaniment

    close = make_accompaniment(
        [(3.5, 4.5, chord_semitones("C"))],
        [(0.0, 4.0), (4.0, 4.0)], 8, 120, 8000
    )

    no_bar_info = make_accompaniment(
        [(3.5, 4.5, chord_semitones("C"))], [], 8, 120, 8000
    )

    assert np.allclose(close, no_bar_info)


def test_a_chord_arriving_well_before_a_bar_line_still_reinforces():
    """
    The one-beat guard only skips a reinforcement that would
    be redundant. A chord that has genuinely been sounding
    for a while before the bar line still gets struck again
    there, exactly as before - the regression this test
    guards against is the guard swallowing the whole feature
    rather than just the too-close case.
    """

    import numpy as np

    from playback import make_accompaniment

    far = make_accompaniment(
        [(2.0, 6.0, chord_semitones("C"))],
        [(0.0, 4.0), (4.0, 4.0)], 8, 120, 8000
    )

    no_bar_info = make_accompaniment(
        [(2.0, 6.0, chord_semitones("C"))], [], 8, 120, 8000
    )

    assert not np.allclose(far, no_bar_info)


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
        melody_level=1, harmony_below_level=0, bpm=120,
        metronome_level=0, chart_text=chart, chords_level=1
    )

    rate, without = play_music(
        pitches, durations, key,
        melody_level=1, harmony_below_level=0, bpm=120,
        metronome_level=0, chart_text=chart, chords_level=0
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
        melody_level=1, harmony_below_level=1, bpm=100,
        metronome_level=1, chart_text=chart, chords_level=1
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


def test_the_parallel_third_fallback_respects_a_key_change():
    """
    A note with no chord under it falls back to the parallel
    third - and that fallback has to know which key was in
    force at its own beat, not one key for the whole line,
    the same requirement make_harmony has and for the same
    reason (proven on the real Mulan file: a note at beat
    164.5, after its own modulation, harmonised as C5 under
    the old single-key bug and Db5 correctly).
    """

    from harmony import make_chord_harmony

    pitches = ["C4", "C4", "Ab4", "Ab4"]
    durations = [1.0, 1.0, 1.0, 1.0]

    # No chords at all, so chord_tones_at is always None and
    # every note takes the parallel-third fallback - the one
    # path that reads `key` at all.
    changed = make_chord_harmony(
        pitches, durations, [],
        key=[(0.0, "C"), (2.0, "Ab")], steps=-2
    )

    before = make_chord_harmony(
        pitches[:2], durations[:2], [], key="C", steps=-2
    )
    after = make_chord_harmony(
        pitches[2:], durations[2:], [], key="Ab", steps=-2
    )

    assert changed == before + after


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

    # One note per chord, repeated. The F is above the C
    # rather than below it: a fourth up is a shorter
    # journey than a fifth down, and it keeps the line off
    # the floor of the range.
    assert line == [
        "C3", "C3", "C3", "C3", "F3", "F3", "C3"
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
        ["C3", "C3", "C3", "C3", "F3", "F3", "C3", "R"],
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
        melody_level=1, harmony_below_level=0, bpm=120,
        metronome_level=0, chart_text=chart
    )

    rate, without = play_music(
        pitches, durations, key, bass_level=0, **common
    )

    rate, with_bass = play_music(
        pitches, durations, key, bass_level=1, **common
    )

    assert not np.allclose(without, with_bass)


def test_the_bass_layer_needs_a_chart_too():
    from music import play_music, MusicInputError

    with pytest.raises(MusicInputError, match="needs a chord chart"):
        play_music(
            "C4 C4", "1 1", "C",
            melody_level=0, harmony_below_level=0, bpm=120,
            chart_text="", bass_level=1
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
        harmony_below=["A3", "A3", "E4", "E4"],
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
        harmony_below=["A3", "A3"],
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


def test_the_bass_moves_by_the_shortest_step():
    """
    A bass line walks. Anchoring each root independently
    from the bottom of the range produces leaps nobody
    would write.
    """

    from harmony import bass_octave_for
    from notes import note_to_midi, midi_to_note

    # From C3, the F above is nearer than the F below.
    from_c = bass_octave_for(
        note_to_midi("F4") % 12,
        note_to_midi("C3")
    )

    assert midi_to_note(from_c) == "F3"

    # From A3, the same F is nearer below.
    from_a = bass_octave_for(
        note_to_midi("F4") % 12,
        note_to_midi("A3")
    )

    assert midi_to_note(from_a) == "F3"


def test_the_bass_stays_in_a_range_people_can_sing():
    """
    A line that drops to F2 because the arithmetic allowed
    it asks for a note most people cannot support, and one
    the detector can barely hear.
    """

    from harmony import (
        make_bass,
        BASS_LOWEST_MIDI,
        BASS_HIGHEST_MIDI
    )
    from notes import note_to_midi

    for chart in [
        "| C . G . | Am . F . |",
        "| G . D . | Em . C . |",
        "| Bb . F . | Eb . Bb . |"
    ]:

        chords, bars = read_chart(chart)

        voiced = [
            (start, length, chord_semitones(name))
            for start, length, name in chords
        ]

        beats = int(sum(length for start, length in bars))

        line = make_bass(["C4"] * beats, [1.0] * beats, voiced)

        for note in line:
            assert BASS_LOWEST_MIDI <= note_to_midi(note)
            assert note_to_midi(note) <= BASS_HIGHEST_MIDI


def test_a_phrase_is_padded_to_whole_bars():
    """
    Phrases break where the music breathes, and a breath
    rarely falls on a bar line. Padding to the bars either
    side gives the chart, the bar lines and the downbeats
    somewhere to sit.
    """

    from midi_import import import_midi
    from music import read_music

    path = os.path.join(
        os.path.dirname(__file__),
        "fixtures", "midi", "o-holy-night-satb.mid"
    )

    if not os.path.exists(path):
        pytest.skip("the satb fixture is not present")

    for phrase in range(6):

        pitches, durations, lyrics, bpm, chart, chart_notes = import_midi(
            path, track_number=1
        )

        pitch_list, duration_list = read_music(pitches, durations)

        assert sum(duration_list) % 4 == 0


def test_an_imported_chart_fits_its_music():
    """
    A chart read from a file has to pass the same check as
    one typed by hand, or importing produces music that
    cannot be played.
    """

    from midi_import import import_midi
    from music import read_music, read_chords

    path = os.path.join(
        os.path.dirname(__file__),
        "fixtures", "midi", "o-holy-night-satb.mid"
    )

    if not os.path.exists(path):
        pytest.skip("the satb fixture is not present")

    for phrase in range(8):

        pitches, durations, lyrics, bpm, chart, chart_notes = import_midi(
            path, track_number=1
        )

        pitch_list, duration_list = read_music(pitches, durations)

        # Raises if the chart and the music disagree.
        chords, bars = read_chords(chart, duration_list)

        assert len(chords) > 0


def test_chords_come_from_every_voice_not_the_one_sung():
    """
    A soprano line alone holds no chords. The four parts
    of a hymn spell one out on every beat.
    """

    from midi_import import import_midi

    path = os.path.join(
        os.path.dirname(__file__),
        "fixtures", "midi", "o-holy-night-satb.mid"
    )

    if not os.path.exists(path):
        pytest.skip("the satb fixture is not present")

    pitches, durations, lyrics, bpm, chart, chart_notes = import_midi(
        path, track_number=1
    )

    chords, bars = read_chart(chart)

    # Real chords, not one per melody note.
    assert len(chords) < len(pitches.split())

    names = {name for start, length, name in chords}

    assert "D" in names


def test_alternative_names_are_offered_not_chosen():
    """
    Some pitch sets genuinely are two chords. Naming only
    the winner hides that the question was open, so the
    others are reported alongside - information, not a
    change to what the chart says.
    """

    import mido

    from midi_import import read_notes
    from chord_detector import (
        detect_chords,
        fill_gaps,
        other_names_for,
        weigh_pitches
    )

    path = os.path.join(
        os.path.dirname(__file__),
        "fixtures", "midi", "o-holy-night-satb.mid"
    )

    if not os.path.exists(path):
        pytest.skip("the satb fixture is not present")

    notes, bpm = read_notes(mido.MidiFile(path))

    chords = fill_gaps(detect_chords(notes, 24, 4), 24)

    # The chart still names one chord per change.
    for start, length, name in chords:
        assert " " not in name
        assert "(" not in name

    # And somewhere among them, a second name fits.
    found = False

    for start, length, name in chords:

        weights, lowest = weigh_pitches(notes, start, start + length)

        if other_names_for(weights, lowest, name):
            found = True

    assert found


def test_an_inversion_is_reported_since_the_chart_cannot_write_it():
    """
    A chord with a note other than its root at the bottom
    is written D/F sharp. The chart notation has no way to
    say that, so it is mentioned rather than lost.
    """

    from chord_detector import bass_note_for

    # D, F sharp and A sounding, with F sharp lowest.
    weights = [0.0] * 12
    weights[2] = 1.0
    weights[6] = 1.0
    weights[9] = 1.0

    assert bass_note_for(weights, 6, "D") == "F#"

    # Root position says nothing.
    assert bass_note_for(weights, 2, "D") is None


def test_the_asides_are_keyed_to_where_the_chords_start():
    from chord_detector import asides_for

    notes = [
        (0.0, 4.0, 42),
        (0.0, 4.0, 62),
        (0.0, 4.0, 69)
    ]

    chords = [(0.0, 4.0, "D")]

    asides = asides_for(notes, chords)

    assert 0.0 in asides
    assert "/F#" in asides[0.0]


def test_a_note_list_can_be_read_by_a_midi_chord_reader():
    """
    A file is only a way of carrying notes about, and we
    already have the notes, so a reader that expects a
    file can be handed one built in memory.
    """

    pytest.importorskip("chorder")
    pytest.importorskip("miditoolkit")

    from chorder import Dechorder

    from chord_detector import as_midi_object

    # D major for a bar, then G major.
    notes = [
        (0, 4, 50), (0, 4, 54), (0, 4, 57),
        (4, 4, 55), (4, 4, 59), (4, 4, 62)
    ]

    read = [
        str(chord)
        for chord in Dechorder.dechord(as_midi_object(notes))
    ]

    assert read[0].startswith("D")
    assert read[-1].startswith("G")


def test_second_opinions_are_optional():
    """
    The app runs without either reader installed, and the
    extra lines simply do not appear.
    """

    import builtins

    from chord_detector import second_opinion, midi_reader_opinion

    real_import = builtins.__import__

    def refuse(name, *args, **kwargs):
        if name in ("pychord", "pychord.analyzer", "chorder"):
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    notes = [(0, 4, 50), (0, 4, 54), (0, 4, 57)]
    chords = [(0.0, 4.0, "D")]

    builtins.__import__ = refuse

    try:
        assert second_opinion(notes, chords) == ""
        assert midi_reader_opinion(notes, chords) == ""

    finally:
        builtins.__import__ = real_import


def test_the_two_opinions_answer_different_questions():
    """
    One names a set of notes; the other decides where a
    chord ends. They are worth having both because they
    disagree in different ways.
    """

    pytest.importorskip("pychord")
    pytest.importorskip("chorder")

    import mido

    from midi_import import read_notes
    from chord_detector import (
        detect_chords,
        fill_gaps,
        second_opinion,
        midi_reader_opinion
    )

    path = os.path.join(
        os.path.dirname(__file__),
        "fixtures", "midi", "o-holy-night-satb.mid"
    )

    if not os.path.exists(path):
        pytest.skip("the satb fixture is not present")

    notes, bpm = read_notes(mido.MidiFile(path))

    # 48 beats no longer reaches a chorder disagreement:
    # SEVENTH_COST made our own reading of this stretch
    # more accurate, so chorder has nothing left to add
    # here specifically. 72 does.
    chords = fill_gaps(detect_chords(notes, 72, 4), 72)

    namer = second_opinion(notes, chords)
    reader = midi_reader_opinion(notes, chords)

    # Both have something to say, and it is not the same
    # something.
    assert namer
    assert reader
    assert namer != reader


def test_a_single_line_is_not_named_as_chords():
    """
    One note is not a chord. A bare melody will happily
    match some triad containing that note, and the answer
    is confident, arbitrary and wrong.
    """

    from chord_detector import name_chord, weigh_pitches

    # One note sounding, at length.
    notes = [(0.0, 4.0, 62)]

    weights, lowest = weigh_pitches(notes, 0, 4)

    assert name_chord(weights, lowest) is None


def test_two_notes_are_thin_but_real():
    """
    An open fifth is a chord, and hymns do reduce to two
    voices.
    """

    from chord_detector import name_chord, weigh_pitches

    notes = [(0.0, 4.0, 62), (0.0, 4.0, 69)]

    weights, lowest = weigh_pitches(notes, 0, 4)

    assert name_chord(weights, lowest) == "D"


def test_a_trace_note_cannot_rename_the_chord():
    """
    A pitch heard for a sliver of the beat is decoration.
    Without the floor, a whisper of C under an E flat
    triad names the beat C minor seventh: the whisper
    fills the seventh chord's fourth tone and, lying
    lowest, collects the bass bonus too. Measured against
    the Wellerman's published sheet, this one whisper cost
    two chorus bars.
    """

    from chord_detector import name_chord, weigh_pitches

    # A solid E flat triad, and a low C for four percent
    # of the beat.
    notes = [
        (0.0, 4.0, 63),
        (0.0, 4.0, 67),
        (0.0, 4.0, 70),
        (0.0, 0.48, 48),
    ]

    weights, lowest = weigh_pitches(notes, 0, 4)

    assert weights[0] == 0.0
    assert lowest == 3
    assert name_chord(weights, lowest) == "D#"


def test_a_real_bass_note_still_names_itself():
    """
    The floor drops whispers, not quiet voices: a bass
    note sounding for a proper share of the beat keeps
    its claim.
    """

    from chord_detector import name_chord, weigh_pitches

    notes = [
        (0.0, 4.0, 63),
        (0.0, 4.0, 67),
        (0.0, 4.0, 70),
        (0.0, 2.0, 48),
    ]

    weights, lowest = weigh_pitches(notes, 0, 4)

    assert weights[0] > 0
    assert lowest == 0


def test_a_missing_third_breaks_toward_the_key_not_a_list():
    """
    A root and a fifth alone, no third at all, score
    identically as major or minor - neither reading
    explains or contradicts the other's missing note.
    Untouched, that tie always fell to major, because
    DETECTED_QUALITIES lists "" before "m" and a strict
    greater-than only replaces the first candidate tried.
    That was a real, measured bias, not a hypothetical one:
    fifteen genuinely minor bars read as major in one
    published song alone, every one of them exactly this
    shape. On a true tie the key breaks it instead: E is
    the sixth degree of G major, which is minor, so a bare
    E-and-B, no third, should read E minor here.
    """

    from chord_detector import name_chord, weigh_pitches

    notes = [
        (0.0, 4.0, 64),  # E4, the root
        (0.0, 4.0, 71),  # B4, the fifth - no third present
    ]

    weights, lowest = weigh_pitches(notes, 0, 4)

    assert name_chord(weights, lowest, "G") == "Em"


def test_the_same_tie_still_reads_major_when_the_key_says_so():
    """
    The fix is a tie-break, not a new bias toward minor: a
    bare root-and-fifth on the tonic of a major key, G in G
    major, should still read as G major, not flip to minor
    out of overcorrection.
    """

    from chord_detector import name_chord, weigh_pitches

    notes = [
        (0.0, 4.0, 67),  # G4, the root
        (0.0, 4.0, 74),  # D5, the fifth
    ]

    weights, lowest = weigh_pitches(notes, 0, 4)

    assert name_chord(weights, lowest, "G") == "G"


def test_a_diatonic_seventh_needs_no_accidental_to_be_reached():
    """
    The search only widens to all sixty candidates when a
    real accidental sounds - a pitch outside the key's own
    seven notes. It does not widen just because a seventh
    is being considered: A7's own tones (A, C sharp, E, G)
    are every one of them a note of D major already, so
    this should be reachable with nothing outside the key
    at all. Restricting the quiet case to the seven plain
    triads alone - rather than any chord whose own tones
    stay diatonic - was a real bug caught by exactly this
    case: it silently turned real, ordinary sevenths into
    the wrong triad, found on the app's own O Holy Night
    fixture.
    """

    from chord_detector import name_chord, weigh_pitches

    notes = [
        (0.0, 4.0, 57),  # A3
        (0.0, 4.0, 61),  # C#4
        (0.0, 4.0, 64),  # E4
        (0.0, 4.0, 67),  # G4 - the seventh, still a D major note
    ]

    weights, lowest = weigh_pitches(notes, 0, 4)

    assert name_chord(weights, lowest, "D") == "A7"


def test_a_real_accidental_opens_the_search_past_the_key():
    """
    A pitch that genuinely is not one of the key's own seven
    notes is real evidence the music has left the key, and
    only then does the search widen to all sixty candidates.
    F minor in C major needs an A flat, which C major does
    not have - found on a real published song, where the
    seven-triad-only version of this fix could never reach
    it no matter how loud the F minor was.
    """

    from chord_detector import name_chord, weigh_pitches

    notes = [
        (0.0, 4.0, 65),  # F4
        (0.0, 4.0, 68),  # A flat 4 - not a note of C major
        (0.0, 4.0, 72),  # C5
    ]

    weights, lowest = weigh_pitches(notes, 0, 4)

    assert name_chord(weights, lowest, "C") == "Fm"


def test_a_passing_sixth_does_not_turn_a_triad_into_a_seventh():
    """
    A seventh chord explains one more tone than the triad
    inside it, so on a beat where that fourth tone is only
    a decoration, the wider net scoops it up for free. A
    sung sixth over a B flat triad should stay B flat, not
    read as the minor seventh a third below (G minor
    seventh happens to share three of its four tones with
    it). Found on a real published sheet, where this
    mistake was systematic rather than occasional.
    """

    from chord_detector import name_chord, weigh_pitches

    notes = [
        (0.0, 4.0, 58),  # B flat 3
        (0.0, 4.0, 62),  # D4
        (0.0, 4.0, 65),  # F4
        (0.0, 1.0, 67),  # G4, a quarter of the beat
    ]

    weights, lowest = weigh_pitches(notes, 0, 4)

    assert name_chord(weights, lowest) == "A#"


def test_a_real_seventh_still_wins():
    """
    The cost only stops a seventh winning by default; a
    seventh that is genuinely, fully there still wins.
    """

    from chord_detector import name_chord, weigh_pitches

    notes = [
        (0.0, 4.0, 55),  # G3
        (0.0, 4.0, 59),  # B3
        (0.0, 4.0, 62),  # D4
        (0.0, 4.0, 65),  # F4
    ]

    weights, lowest = weigh_pitches(notes, 0, 4)

    assert name_chord(weights, lowest) == "G7"


def test_an_empty_chart_explains_itself():
    """
    An empty box with no explanation looks like a fault.
    """

    from chord_detector import chart_from_notes, explain_empty_chart

    melody = [(float(beat), 1.0, 62 + beat) for beat in range(8)]

    assert chart_from_notes(melody, 8, 4) == ""

    reason = explain_empty_chart(melody, 8)

    assert "single line" in reason


def test_chords_are_spelled_in_the_key():
    """
    A chart in B flat major that reads A sharp is the same
    sound written in the wrong dialect.
    """

    from chord_detector import chart_from_notes

    # A B flat chord, held.
    notes = [
        (0.0, 4.0, 46), (0.0, 4.0, 50), (0.0, 4.0, 53)
    ]

    assert "A#" in chart_from_notes(notes, 4, 4)
    assert "Bb" in chart_from_notes(notes, 4, 4, key="Bb")


def test_the_spelling_key_is_read_from_the_music():
    from midi_import import spelling_key

    # A B flat major scale.
    notes = [
        (float(beat), 1.0, midi)
        for beat, midi in enumerate(
            [46, 48, 50, 51, 53, 55, 57, 58]
        )
    ]

    assert spelling_key(notes) == "Bb"


def test_reading_and_suggesting_are_different_answers():
    """
    Reading chords off several voices says what the
    harmony is. Suggesting them from a melody says what
    would fit. The second is a weaker claim, and worth
    having where the first cannot be made.
    """

    import mido

    from midi_import import read_notes
    from music import suggest_chords

    path = os.path.join(
        os.path.dirname(__file__),
        "fixtures", "midi", "o-holy-night-satb.mid"
    )

    if not os.path.exists(path):
        pytest.skip("the satb fixture is not present")

    notes, bpm = read_notes(mido.MidiFile(path))

    within = [
        (start, length, number)
        for start, length, number in notes
        if start < 8
    ]

    melody = "D4 " * 8
    lengths = "1 " * 8

    read = suggest_chords(within, melody, lengths, "D")

    suggested = suggest_chords(None, melody, lengths, "D")

    # Both give a chart, and they need not agree: one is
    # what sounded, the other what would fit.
    assert read.startswith("|")
    assert suggested.startswith("|")


def test_a_melody_implies_chords_even_alone():
    """
    A melody does not state its harmony, but it does
    narrow it: the notes on the strong beats are usually
    the chord, and the key offers only seven to choose
    between.
    """

    from music import suggest_chords, load_twinkle_phrase

    pitches, durations, lyrics, key, chart = load_twinkle_phrase()

    suggested = suggest_chords(None, pitches, durations, key)

    # The same chords a person wrote by hand.
    assert suggested == chart


def test_a_minor_melody_is_harmonised_from_its_own_tonic():
    """
    D minor and F major share every note and lean on
    different chords. Taking the major as home in a minor
    song puts every cadence in the wrong place.
    """

    from music import suggest_chords, load_wellerman_phrase

    pitches, durations, lyrics, key, chart = load_wellerman_phrase()

    suggested = suggest_chords(None, pitches, durations, key)

    assert suggested == chart

    # And the mode is worked out, not assumed.
    from music import sounds_minor, read_music

    pitch_list, duration_list = read_music(pitches, durations)

    assert sounds_minor(pitch_list, duration_list)


def test_a_strong_beat_counts_for_more_than_a_passing_note():
    """
    The ear takes the note on the beat as the harmony and
    hears the rest as decoration.
    """

    from chord_detector import weigh_melody
    from notes import note_to_midi

    # C on the downbeat, D slipping past between beats.
    weights = weigh_melody(
        ["C4", "D4", "E4", "F4"],
        [1.0, 0.5, 0.5, 2.0],
        0, 4
    )

    assert weights[note_to_midi("C4") % 12] > weights[
        note_to_midi("D4") % 12
    ]


def test_only_the_chords_of_the_key_are_offered():
    from chord_detector import chords_of_key, note_name

    names = [
        note_name(root) + quality
        for root, quality in chords_of_key("C")
    ]

    assert names == [
        "C", "Dm", "Em", "F", "G", "Am", "Bdim"
    ]


def test_a_bar_is_split_only_when_one_chord_will_not_do():
    """
    Harmony changes at the bar far more often than not, and
    a chart that changes every other beat is harder to read
    and rarely more true.
    """

    from chord_detector import suggest_chart_from_melody

    # A bar that plainly sits on one chord.
    steady = suggest_chart_from_melody(
        ["C4", "E4", "G4", "E4"],
        [1.0, 1.0, 1.0, 1.0],
        "C"
    )

    assert steady == "| C . . . |"


def test_there_must_be_a_bar_to_harmonise():
    from music import suggest_chords, MusicInputError

    with pytest.raises(MusicInputError, match="least that can be"):
        suggest_chords(None, "C4 E4", "1 1")


def test_the_axis_counts_bars_when_there_is_a_chart():
    """
    A chord chart lives in bars, and the picture under it
    should count the way a musician counts: bar numbers on
    the bar lines, beats as small marks between. Seconds
    remain when there is no chart, because a bare
    recording is genuinely in seconds and bars would be an
    invention.
    """

    from music import show_target_music, load_twinkle_phrase

    pitches, durations, lyrics, key, chart = load_twinkle_phrase()

    with_chart = show_target_music(
        pitches, durations, 120, lyrics, key,
        0, 0, chart
    )

    assert with_chart.axes[0].get_xlabel() == "bars"

    labels = [
        tick.get_text()
        for tick in with_chart.axes[0].get_xticklabels()
    ]

    assert labels[0] == "1"

    without = show_target_music(
        pitches, durations, 120, lyrics, key,
        0, 0, ""
    )

    assert without.axes[0].get_xlabel() == "seconds"

def test_the_two_harmony_lines_are_different_colours():
    """
    Above and below cross the melody and each other, so a
    box's position on the page cannot say which line it
    belongs to. The colour has to.
    """

    from tuning_plot import (
        make_performance_plot,
        HARMONY_ABOVE_COLOUR,
        HARMONY_BELOW_COLOUR,
        BASS_COLOUR
    )

    figure = make_performance_plot(
        ["C4", "C4"],
        [1.0, 1.0],
        120,
        None,
        harmony_above=["E4", "E4"],
        harmony_below=["A3", "A3"],
        bass=["C3", "C3"]
    )

    colours = {
        text.get_color()
        for text in figure.axes[0].texts
    }

    assert HARMONY_ABOVE_COLOUR in colours
    assert HARMONY_BELOW_COLOUR in colours
    assert BASS_COLOUR in colours

    assert len({
        HARMONY_ABOVE_COLOUR,
        HARMONY_BELOW_COLOUR,
        BASS_COLOUR
    }) == 3, "every voice needs its own colour"


def test_a_harmony_line_keeps_its_colour_when_alone():
    """
    Turning one line off must not move the other's colour:
    the colour belongs to the part, not to the order the
    voices happened to be drawn in.
    """

    from tuning_plot import (
        make_performance_plot,
        HARMONY_ABOVE_COLOUR,
        HARMONY_BELOW_COLOUR
    )

    def colours_of(**voices):
        figure = make_performance_plot(
            ["C4", "C4"], [1.0, 1.0], 120, None, **voices
        )
        return {
            text.get_color()
            for text in figure.axes[0].texts
        }

    above_alone = colours_of(harmony_above=["E4", "E4"])
    below_alone = colours_of(harmony_below=["A3", "A3"])

    assert HARMONY_ABOVE_COLOUR in above_alone
    assert HARMONY_BELOW_COLOUR not in above_alone

    assert HARMONY_BELOW_COLOUR in below_alone
    assert HARMONY_ABOVE_COLOUR not in below_alone


# Half-beat chords: a syncopated change writes as A>B in
# one beat's slot, or >B when the first half just carries
# the chord before it. Found needed by a real Disney lead
# sheet (Mulan's "I'll Make a Man Out of You") where the
# printed chart genuinely changes on the "and" of a beat -
# a chart holding only whole beats either dropped that
# chord or struck it a whole beat early.


def test_a_split_token_reads_as_two_half_beat_chords():
    chords, bars = read_chart("| D>G |")

    assert chords == [(0.0, 0.5, "D"), (0.5, 0.5, "G")]
    assert bars == [(0.0, 1.0)]


def test_a_bare_split_carries_the_previous_chord_for_the_first_half():
    """
    ">G" means the chord already sounding just continues
    through the first half of the beat, and G is the only
    genuinely new arrival - the common case, a chord pushed
    early onto the "and".
    """

    chords, bars = read_chart("| D >G |")

    assert chords == [
        (0.0, 1.5, "D"),
        (1.5, 0.5, "G")
    ]


def test_a_beat_cannot_split_more_than_once():
    with pytest.raises(ChartError, match="more than one"):
        read_chart("| A>B>C . . . |")


def test_a_split_needs_a_chord_after_the_mark():
    with pytest.raises(ChartError, match="needs a chord"):
        read_chart("| > . . . |")


def test_a_chart_cannot_open_on_a_bare_split():
    """
    Same shape as opening on a dot: nothing to carry on for
    the first half.
    """

    with pytest.raises(ChartError, match="cannot begin with"):
        read_chart("| >G . . . |")


def test_write_chart_round_trips_a_split_exactly():
    from chord_detector import write_chart

    for original in ("| D>G . . . |", "| D . >G . |", "| Em . . D>G |"):

        chords, bars = read_chart(original)

        assert write_chart(chords, chart_beats(original), 4.0) == original


def test_write_chart_still_floors_whole_beat_detector_output():
    """
    A detector never lands on a genuine half - it only ever
    samples whole beats - so its output must render exactly
    as it always did, with no split tokens appearing where
    none were ever intended. This is the regression guard
    for the two protected ground-truth fixtures: a chord
    list shaped like detector output must be untouched by
    the half-beat change.
    """

    from chord_detector import write_chart

    chords = [(0.0, 2.0, "Dm"), (2.0, 2.0, "Bb")]

    assert write_chart(chords, 4.0, 4.0) == "| Dm . Bb . |"


def test_write_chart_floors_a_finer_than_half_start_gracefully():
    """
    Only an exact half is kept - a start landing at, say, a
    third of the way through a beat still floors to the
    beat it began within, the same graceful fallback a
    whole-beat-only chart has always had.
    """

    from chord_detector import write_chart

    chords = [(0.0, 2.33, "D"), (2.33, 1.67, "G")]

    assert write_chart(chords, 4.0, 4.0) == "| D . G . |"


def test_transpose_moves_both_halves_of_a_split():
    from chords import transpose_chart

    assert transpose_chart("| D>G . . . |", 2) == "| E>A . . . |"


def test_transpose_moves_the_bare_half_of_a_split():
    from chords import transpose_chart

    assert transpose_chart("| >G . . . |", -2, key="F") == "| >F . . . |"


def test_transpose_respells_each_chord_against_its_own_key():
    """
    A chart's own timeline (Piece.key_changes' shape) means
    a chord respells against whichever key was actually in
    force at its own start, not one key for the whole
    chart. The same C, transposed by the same interval,
    lands as C# under a sharp-dialect key and Db under a
    flat one - same pitch, different truth about where it
    sits.
    """

    from chords import transpose_chart

    key_changes = [(0.0, "C"), (4.0, "Ab")]

    moved = transpose_chart(
        "| C . . . | C . . . |", 1, key=key_changes
    )

    assert moved == "| C# . . . | Db . . . |"


def test_transpose_preserves_a_bar_with_no_chord_in_it():
    """
    read_chart silently drops a bar with nothing in it
    (found on the Wellerman's own committed chart), and a
    round trip through read_chart/write_chart would quietly
    lose it - transpose_chart only promises to move roots,
    so the bar-line structure has to survive exactly,
    decorative empty bars included.
    """

    from chords import transpose_chart

    assert (
        transpose_chart("| Dm . . . | | Dm . . . |", 2)
        == "| Em . . . | | Em . . . |"
    )