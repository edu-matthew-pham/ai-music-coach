# tests/test_music.py

import os

import numpy as np
import pytest

from harmony import MAJOR_SCALES
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
        melody_level=1,
        harmony_below_level=0,
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
        melody_level=0,
        harmony_below_level=0,
        bpm=120,
        metronome_level=0
    )

    assert float(np.max(np.abs(audio))) > 0.1


def test_melody_and_harmony_mix_together():
    sample_rate, together = play_music(
        "C4 C4",
        "1 1",
        "C",
        melody_level=1,
        harmony_below_level=1,
        bpm=120,
        metronome_level=0
    )

    sample_rate, alone = play_music(
        "C4 C4",
        "1 1",
        "C",
        melody_level=1,
        harmony_below_level=0,
        bpm=120,
        metronome_level=0
    )

    # The mixed track is a different signal, not just the
    # melody again.
    shared = min(len(together), len(alone))

    assert not np.allclose(
        together[:shared],
        alone[:shared]
    )


def test_load_twinkle_phrase():
    pitches, durations, lyrics, key, chart = load_twinkle_phrase()

    # The phrase ends with a rest: somewhere to breathe
    # before the line repeats.
    assert pitches == "C4 C4 G4 G4 A4 A4 G4 R"
    assert durations == "1 1 1 1 1 1 3/2 1/2"
    assert lyrics == "Twin- kle twin- kle lit- tle star"
    assert key == "C"


def test_load_wellerman_phrase_is_playable_and_harmonisable():
    """
    The loaded example must work with every feature: the
    counts agree, the notes read, and the harmony can be
    built in the key it loads with.
    """

    from music import (
        load_wellerman_phrase,
        read_music,
        read_lyrics,
        sung_count
    )
    from harmony import make_harmony

    pitches, durations, lyrics, key, chart = load_wellerman_phrase()

    pitch_list, duration_list = read_music(pitches, durations)

    # A rest takes no syllable, so the words are counted
    # against the notes that are actually sung.
    syllables = read_lyrics(lyrics, sung_count(pitch_list))

    assert len(syllables) == sung_count(pitch_list)

    harmony = make_harmony(pitch_list, key=key)

    assert len(harmony) == len(pitch_list)


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


def test_practice_guide_follows_a_selected_loop():
    """
    A loop selected in the mixer shortens the guide to just
    that stretch, the same rule Compare's judging follows.
    """

    from music import make_practice_guide

    pitches = "C4 D4 E4 F4 G4 A4"
    durations = "1 1 1 1 1 1"

    whole_rate, whole_audio = make_practice_guide(
        pitches, durations, 120, "Clicks"
    )

    # At 120bpm, notes 2-4 (E4 F4 G4) start at 1.0s, 1.5s,
    # 2.0s. loop_end sits safely before note 5's start
    # (2.5s) so it is excluded.
    mixer_value = {"loop_start": 1.0, "loop_end": 2.4, "bpm": 120.0}

    looped_rate, looped_audio = make_practice_guide(
        pitches, durations, 120, "Clicks", mixer_value=mixer_value
    )

    assert whole_rate == looped_rate
    assert len(looped_audio) < len(whole_audio)


def test_practice_guide_ignores_an_empty_mixer_value():
    """
    No mixer built yet, or nothing selected in it: the whole
    piece plays, exactly as before this was added.
    """

    from music import make_practice_guide

    pitches = "C4 D4 E4"
    durations = "1 1 1"

    without_param = make_practice_guide(
        pitches, durations, 120, "Clicks"
    )

    with_none = make_practice_guide(
        pitches, durations, 120, "Clicks", mixer_value=None
    )

    with_empty = make_practice_guide(
        pitches, durations, 120, "Clicks",
        mixer_value={"loop_start": None, "loop_end": None}
    )

    assert len(without_param[1]) == len(with_none[1]) == len(with_empty[1])


def test_compare_judges_against_a_selected_loop():
    """
    A loop selected in the mixer takes over from the phrase
    dropdown: judged against exactly the notes it covers, and
    the feedback says so.
    """

    from playback import make_melody
    from music import analyse_performance

    pitches = "C4 D4 E4 F4 G4 A4"
    durations = "1 1 1 1 1 1"

    # A recording matching only the looped notes (E4 F4 G4)
    # exactly.
    rate, sound = make_melody(
        ["E4", "F4", "G4"], [1.0, 1.0, 1.0], 120, 8000
    )

    mixer_value = {"loop_start": 1.0, "loop_end": 2.4, "bpm": 120.0}

    text, performance, tuning = analyse_performance(
        (rate, np.array(sound)),
        pitches, durations, 120,
        mixer_value=mixer_value
    )

    assert "3 of 3" in text
    assert "selected in the mixer" in text


def test_compare_falls_back_to_the_phrase_dropdown_without_a_loop():
    """
    No loop selected: phrase_label decides it, exactly as
    before this was added, and the mixer note is absent.
    """

    from playback import make_melody
    from music import analyse_performance

    pitches = "C4 D4 E4"
    durations = "1 1 1"

    rate, sound = make_melody(
        ["C4", "D4", "E4"], [1.0, 1.0, 1.0], 120, 8000
    )

    text, performance, tuning = analyse_performance(
        (rate, np.array(sound)),
        pitches, durations, 120,
        mixer_value=None
    )

    assert "selected in the mixer" not in text


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


def test_every_example_is_complete_and_singable():
    """
    Whatever an example button loads must work with every
    part of the app: the counts agree, the words fit the
    sung notes, the harmony builds in the key it brings,
    and it can be played.
    """

    from music import (
        load_wellerman_phrase,
        read_music,
        read_lyrics,
        sung_count,
        play_music
    )
    from harmony import make_harmony

    for loader in (load_twinkle_phrase, load_wellerman_phrase):

        pitches, durations, lyrics, key, chart = loader()

        pitch_list, duration_list = read_music(
            pitches, durations
        )

        assert len(pitch_list) == len(duration_list)

        syllables = read_lyrics(
            lyrics, sung_count(pitch_list)
        )

        assert len(syllables) == sung_count(pitch_list)

        harmony = make_harmony(pitch_list, key=key)

        assert len(harmony) == len(pitch_list)

        sample_rate, audio = play_music(
            pitches, durations, key,
            melody_level=1, harmony_below_level=1, bpm=120
        )

        assert len(audio) > 0


def test_examples_fill_whole_bars():
    """
    A phrase that does not fill whole bars cannot be
    counted in, looped, or played against a metronome
    without the beat sliding. The breath at the end comes
    out of the last note rather than being added on top.
    """

    from music import load_wellerman_phrase, read_music

    for loader in (load_twinkle_phrase, load_wellerman_phrase):

        pitches, durations, lyrics, key, chart = loader()

        pitch_list, duration_list = read_music(
            pitches, durations
        )

        total = sum(duration_list)

        assert total % 2 == 0, (
            f"{loader.__name__} runs to {total} beats"
        )


def test_examples_return_everything_the_boxes_need():
    """
    An example fills the pitch, duration, lyric and chord
    boxes and sets the key. The interface appends its own
    updates to clear any imported file, so the count here
    is what that wiring depends on.
    """

    from music import load_wellerman_phrase

    for loader in (load_twinkle_phrase, load_wellerman_phrase):

        values = loader()

        assert len(values) == 5

        pitches, durations, lyrics, key, chart = values

        assert len(pitches.split()) == len(durations.split())
        assert key in MAJOR_SCALES


def test_every_example_brings_a_chart_that_fits_it():
    """
    An example is a whole piece of music, chords included,
    and a chart that did not match its melody would be a
    worked example of the mistake.
    """

    from music import (
        load_wellerman_phrase,
        read_music,
        read_chords
    )

    for loader in (load_twinkle_phrase, load_wellerman_phrase):

        pitches, durations, lyrics, key, chart = loader()

        pitch_list, duration_list = read_music(
            pitches, durations
        )

        # Raises if the chart and the music disagree.
        chords, bars = read_chords(chart, duration_list)

        assert len(chords) > 0
        assert len(bars) > 0


def test_the_wellerman_line_is_two_bars_of_four():
    """
    Checked against a published arrangement: the line runs
    eight beats and the next line arrives on the bar, with
    no rest between. Written as two bars of three it would
    put the downbeat in a different place each time round.
    """

    from music import load_wellerman_phrase, read_music, read_chords

    pitches, durations, lyrics, key, chart = load_wellerman_phrase()

    pitch_list, duration_list = read_music(pitches, durations)

    assert sum(duration_list) == 8.0

    chords, bars = read_chords(chart, duration_list)

    assert bars == [(0.0, 4.0), (4.0, 4.0)]

def test_the_full_twinkle_is_a_consistent_piece():
    """
    The whole song: six phrases in an A B C C A B shape,
    the chart exactly as long as the music.
    """

    from fractions import Fraction

    from music import load_twinkle
    from piece import Piece
    from chords import chart_beats

    pitches, durations, lyrics, key, chart, tempo = load_twinkle()

    piece = Piece.read(pitches, durations, lyrics)

    assert len(piece.phrases()) == 6

    beats = sum(Fraction(x) for x in durations.split())

    assert beats == chart_beats(chart) == 48

    lines = pitches.split("\n") if "\n" in pitches else None

    # The reprise: last two phrases repeat the first two.
    tokens = pitches.split()
    assert tokens[:16] == tokens[32:]


def test_the_full_wellerman_is_a_consistent_piece():
    """
    Verse and chorus on a downbeat-aligned grid: three
    beats of opening rest put the pickup on beat four, and
    the chart - one chord to a bar, read at function level
    from a published sheet, extended to three verses by a
    real arrangement checked against an independent tab -
    lasts exactly as long as the music.
    """

    from fractions import Fraction

    from music import load_wellerman
    from piece import Piece
    from chords import chart_beats, read_chart

    pitches, durations, lyrics, key, chart, tempo = load_wellerman()

    piece = Piece.read(pitches, durations, lyrics)

    # 8 lines each of 3 verse-and-chorus cycles.
    assert len(piece.phrases()) == 24

    beats = sum(Fraction(x) for x in durations.split())

    assert beats == chart_beats(chart) == 200

    assert key == "F"

    # Three opening rests, then the pickup.
    assert pitches.split()[:4] == ["R", "R", "R", "A3"]

    # The chart parses, including the borrowed dominant.
    read_chart(chart)

    assert " A " in f" {chart} "


def test_the_full_wellerman_opens_like_the_phrase_example():
    """
    The first sung line of the full song is the phrase
    example, note for note: the hand-checked notation and
    the grid drafted from the imported performance agree,
    which is what makes the rest of the grid trustworthy.
    """

    from music import load_wellerman, load_wellerman_phrase

    full = load_wellerman()
    phrase = load_wellerman_phrase()

    # Skip the three opening rests; compare the nine notes.
    assert full[0].split()[3:12] == phrase[0].split()

    # Same lengths for the eight notes after the pickup:
    # the phrase example writes its pickup a beat long
    # inside its own two bars, the full song places it on
    # beat four of the count-in bar, so the pickup's length
    # is the one legitimate difference.
    assert full[1].split()[4:12] == phrase[1].split()[1:]


def test_both_harmony_lines_play_at_once():
    """
    A third above and a third below are separate layers
    with separate levels. Both up is a fuller texture than
    either alone, and each alone differs from the other.
    """

    import numpy as np

    from music import play_music

    def rendered(above, below):
        rate, audio = play_music(
            "C4 D4 E4", "1 1 1", "C",
            melody_level=1,
            harmony_above_level=above,
            harmony_below_level=below,
            bpm=120,
            metronome_level=0
        )
        return audio

    above_only = rendered(1, 0)
    below_only = rendered(0, 1)
    both = rendered(1, 1)

    assert not np.allclose(above_only, below_only)
    assert not np.allclose(both, above_only)
    assert not np.allclose(both, below_only)


def test_a_level_is_a_loudness_not_a_switch():
    """
    Half a level is the same part, quieter. That is what
    lets a harmony sit under the melody instead of
    matching it or being absent.
    """

    import numpy as np

    from music import play_music

    def peak(level):
        rate, audio = play_music(
            "C4 C4", "1 1", "C",
            melody_level=level,
            bpm=120,
            metronome_level=0
        )
        return float(np.max(np.abs(audio)))

    assert peak(0.5) < peak(1.0)
    assert peak(0.5) > 0


def test_the_part_names_its_own_direction():
    """
    Harmony above sings the third above; harmony below the
    third below. The part carries the direction, so the
    guide and the judging need no separate interval.
    """

    from music import part_notes, part_steps

    tune = ["C4", "E4", "G4"]

    above = part_notes(tune, "Harmony above", "C")
    below = part_notes(tune, "Harmony below", "C")

    assert above == part_notes(tune, "Harmony", "C", 2)
    assert below == part_notes(tune, "Harmony", "C", -2)
    assert above != below

    assert part_steps("Harmony above") == 2
    assert part_steps("Harmony below") == -2


def test_transposing_moves_the_notes_the_key_and_the_chords():
    """
    One edit of everything that describes the music. The
    notes move, the key follows them, the chart's roots
    travel with them and keep their qualities.
    """

    from music import transpose_music

    pitches, key, chart, notes = transpose_music(
        "C4 E4 R G4", "1 1 1 1", "C",
        "| C . Am . | F . G7 . |", None, 2
    )

    assert pitches == "D4 F#4 R A4"
    assert key == "D"
    assert chart == "| D . Bm . | G . A7 . |"


def test_transposing_and_back_is_exact():
    """
    Returning is a transpose, not a remembered original: a
    stored starting key would go stale the moment anything
    was typed, and the round trip is exact anyway.
    """

    from music import transpose_music, load_wellerman

    original, durations, lyrics, key, chart, tempo = load_wellerman()

    moved, moved_key, moved_chart, _ = transpose_music(
        original, durations, key, chart, None, -3
    )

    back, back_key, back_chart, _ = transpose_music(
        moved, durations, moved_key, moved_chart, None, 3
    )

    assert back == original
    assert back_key == key
    assert back_chart == chart


def test_a_modulating_piece_transposes_both_keys():
    """
    Every key in the timeline moves by the same interval
    and respells in its own new dialect - the notes and the
    chart both, not just the key box's own text. Checked
    with a piece the two keys of which respell very
    differently under the same shift (C -> Db, a flat
    landing; Ab -> A, a sharp one) so a bug that used one
    key for the whole piece could not accidentally look
    right.
    """

    from music import transpose_music

    pitches = "C4 C4 C4 C4 Ab4 Ab4 Ab4 Ab4"
    durations = "1 1 1 1 1 1 1 1"
    key = "C, Ab from beat 4"
    chart = "| C . . . | Ab . . . |"

    new_pitches, new_key, new_chart, _ = transpose_music(
        pitches, durations, key, chart, None, 1
    )

    assert new_pitches == "Db4 Db4 Db4 Db4 A4 A4 A4 A4"
    assert new_key == "Db, A from beat 4"
    assert new_chart == "| Db . . . | A . . . |"


def test_a_zero_semitone_transpose_of_a_modulating_piece_is_a_no_op():
    """
    The bug this whole feature exists to fix: transposing by
    zero semitones used to still respell every note through
    one blanket key, corrupting a modulating piece's already-
    correct spelling even though nothing was meant to move at
    all. Checked against the real Mulan file, not a built
    fixture - this is the exact case that was found broken.
    """

    from music import transpose_music
    from musicxml_import import import_musicxml, parts_in

    path = os.path.join(
        os.path.dirname(__file__), "fixtures", "musicxml",
        "mulan-ill-make-a-man-out-of-you.mxl"
    )

    if not os.path.exists(path):
        pytest.skip("Mulan fixture not present in this sandbox")

    label = parts_in(path)[0]

    (
        pitches, durations, lyrics, bpm, feedback,
        chart, polyphony, key
    ) = import_musicxml(path, label)

    new_pitches, new_key, new_chart, _ = transpose_music(
        pitches, durations, key, chart, polyphony, 0
    )

    assert new_pitches == pitches
    assert new_key == key
    assert new_chart == chart


def test_the_hidden_polyphony_travels_with_the_music():
    """
    The imported voices behind the picture's chord asides
    live in pitch, not in a box. Left behind they would
    describe the key the music has left, and nothing would
    say so.
    """

    from music import transpose_music

    _, _, _, notes = transpose_music(
        "C4", "1", "C", "", [(0.0, 1.0, 60), (0.0, 2.0, 64)], 5
    )

    assert notes == [(0.0, 1.0, 65), (0.0, 2.0, 69)]


def test_an_octave_leaves_the_key_and_the_names_alone():
    from music import transpose_music

    pitches, key, chart, _ = transpose_music(
        "C4 E4 G4", "1 1 1", "C", "| C . . . |", None, -12
    )

    assert pitches == "C3 E3 G3"
    assert key == "C"
    assert chart == "| C . . . |"


def test_the_spelling_follows_the_key_it_lands_in():
    """
    Arriving in a flat key reads flats. The same sound
    spelled in the wrong dialect is what makes a chart
    look foreign to the key box above it.
    """

    from music import transpose_music

    pitches, key, chart, _ = transpose_music(
        "A4 C5", "1 1", "C", "| C . F . |", None, -2
    )

    assert key == "Bb"
    assert "Bb" in chart
    assert "A#" not in chart
    assert pitches == "G4 Bb4"


def test_the_shortest_way_round_is_taken():
    from music import semitones_between

    assert semitones_between("C", "D") == 2
    assert semitones_between("C", "F") == 5

    # Up seven or down five: down five keeps the music
    # nearer where it was.
    assert semitones_between("C", "G") == -5

    assert semitones_between("C", "C") == 0


def test_music_pushed_off_the_keyboard_is_refused():
    from music import transpose_music, MusicInputError

    with pytest.raises(MusicInputError):
        transpose_music("C8 D8", "1 1", "C", "", None, 36)


def test_transposing_says_where_the_part_now_sits():
    """
    The range is the fact a singer is deciding on: not
    which key it is now, but whether the top note is
    still reachable.
    """

    from music import describe_transpose

    said = describe_transpose("C", "D", 2, "D4 F#4 A4")

    assert "C to D" in said
    assert "up 2" in said
    assert "D4" in said
    assert "A4" in said


def test_harmony_respects_a_real_key_change():
    """
    The other proven bug this whole feature exists to fix,
    alongside transpose: a wrong-key harmony is not just a
    wrong note NAME, it is a genuinely different note. Found
    on the real Mulan file - a note at beat 208.5, right at
    its own key change (bar 53, G to Ab), harmonised as C5
    under the old single-key bug and Db5 correctly.

    The beat here is the score's played position, once its
    repeat is unfolded (see test_musicxml_unfold.py) and its
    two voices are read apart rather than flattened together
    (see test_the_bridges_two_voices_are_read_apart, same
    file) - a second, separate fix landed after this test was
    first written, which moved both the note's index and its
    exact beat again. The note relationship the test checks
    (a modulation changing real pitches, not just names) is
    unchanged throughout; only its position in the sequence
    has moved, twice now, as the reading got more correct.
    """

    from music import harmony_line
    from musicxml_import import import_musicxml, parts_in
    from fractions import Fraction

    path = os.path.join(
        os.path.dirname(__file__), "fixtures", "musicxml",
        "mulan-ill-make-a-man-out-of-you.mxl"
    )

    if not os.path.exists(path):
        pytest.skip("Mulan fixture not present in this sandbox")

    label = parts_in(path)[0]

    (
        pitch_text, duration_text, lyrics, bpm, feedback,
        chart, polyphony, key
    ) = import_musicxml(path, label)

    pitches = pitch_text.split()
    durations = [
        float(Fraction(length))
        for length in duration_text.split()
    ]

    correct = harmony_line(
        pitches, durations, key, steps=-2,
        style="Parallel thirds"
    )

    # The bug's own shape: using only the opening key for
    # every note, the way harmony_line used to.
    opening_only = key.split(",")[0]

    wrong = harmony_line(
        pitches, durations, opening_only, steps=-2,
        style="Parallel thirds"
    )

    assert correct[248] == "Db5"
    assert wrong[248] == "C5"
    assert correct != wrong


def test_the_layers_are_the_same_ones_the_mix_uses():
    """
    play_music scales these and adds them; a mixer plays
    them apart. They must be one set of layers, not two
    sets built by two pieces of code, or the recording and
    the mixer drift and the drift is inaudible until
    someone compares them.
    """

    from music import load_wellerman, separate_layers, LAYER_NAMES

    pitches, durations, lyrics, key, chart, tempo = load_wellerman()

    rate, parts = separate_layers(
        pitches, durations, key, tempo, chart,
        lyric_text=lyrics, phrase_label="Whole part"
    )

    for name in LAYER_NAMES:
        assert name in parts, name

    lengths = {len(track) for track in parts.values()}

    assert len(lengths) == 1, "every layer covers the same music"


def test_a_part_the_music_cannot_sound_is_absent():
    """
    Bass and chords are built from the chart. With none,
    they are missing rather than silent, so a mixer can
    say why a fader does nothing.
    """

    from music import separate_layers

    rate, parts = separate_layers("C4 D4 E4", "1 1 1", "C", 120, "")

    assert "Melody" in parts
    assert "Harmony above" in parts
    assert "Metronome" in parts

    assert "Bass" not in parts
    assert "Chords" not in parts


def test_asking_for_a_missing_part_says_why():
    from music import play_music, MusicInputError

    with pytest.raises(MusicInputError, match="chord chart"):
        play_music(
            "C4 C4", "1 1", "C",
            melody_level=1, bpm=120, chart_text="", chords_level=1
        )