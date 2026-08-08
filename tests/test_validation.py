import pytest

from music import (
    MusicInputError,
    read_music,
    show_harmony,
    play_music,
    check_bpm,
    describe_comparison,
    describe_summary
)

from compare import compare_note
from helpers import fake_played


def test_empty_input_is_rejected():
    with pytest.raises(MusicInputError, match="Enter some notes"):
        read_music("", "")


def test_bad_note_name_is_rejected():
    with pytest.raises(MusicInputError, match="banana"):
        read_music("C4 banana", "1 1")


def test_note_without_an_octave_is_rejected():
    with pytest.raises(MusicInputError, match="not a note"):
        read_music("C D E", "1 1 1")


def test_bad_duration_is_rejected():
    with pytest.raises(MusicInputError, match="not a number"):
        read_music("C4 D4", "1 quick")


def test_zero_duration_is_rejected():
    with pytest.raises(MusicInputError, match="longer than zero"):
        read_music("C4", "0")


def test_mismatched_counts_say_both_numbers():
    with pytest.raises(MusicInputError, match="3 notes but 2"):
        read_music("C4 D4 E4", "1 1")


def test_zero_tempo_is_rejected():
    with pytest.raises(MusicInputError, match="greater than zero"):
        check_bpm(0)


def test_tempo_must_be_a_number():
    with pytest.raises(MusicInputError, match="must be a number"):
        check_bpm("fast")


def test_out_of_key_notes_are_reported_not_refused():
    """
    The key is the player's to choose. Notes outside it
    are harmonised at the nearest scale note, and named so
    the interval is no surprise.
    """

    from music import describe_key_fit

    sentence = describe_key_fit(["C4", "C4"], "D")

    assert "C4" in sentence
    assert "nearest note" in sentence


def test_playback_checks_the_key_only_when_harmonising():
    """
    A melody does not need a harmony, so an awkward key
    should not stop it playing.
    """

    sample_rate, audio = play_music(
        "C4 C4", "1 1", "D",
        melody_on=True, harmony_on=False, bpm=120
    )

    assert len(audio) > 0


def test_harmony_plays_in_any_chosen_key():
    """
    Music that does not sit neatly in the chosen key still
    produces a harmony, rather than an error that stops
    the player hearing anything at all.
    """

    sample_rate, audio = play_music(
        "C4 C4", "1 1", "D",
        melody_on=False, harmony_on=True, bpm=120
    )

    assert len(audio) > 0


def described(target, cents):
    """
    Describe a comparison built from a plain offset.
    """

    return describe_comparison(
        compare_note(target, fake_played(target, cents))
    )


def test_small_error_is_called_in_tune():
    assert described("C4", 6) == "C4: in tune"


def test_moderate_error_is_called_slight():
    assert described("C4", -18) == "C4: slightly flat (-18)"


def test_large_error_is_called_clear():
    assert described("C4", 40) == "C4: clearly sharp (+40)"


def test_wrong_note_is_named():
    """
    Seventy cents sharp of C4 lands nearer C#4, so the
    description says what was heard as well as how far off
    it was from what was wanted.
    """

    assert described("C4", 70) == (
        "C4: heard C#4, 70 cents sharp"
    )


def test_undetected_note_is_described():
    assert describe_comparison(
        compare_note("C4", None)
    ) == "C4: nothing detected"


def test_summary_line():
    from compare import compare_sequence, summarise

    targets = ["C4", "E4", "G4"]

    performance = [
        fake_played("C4", 5),
        fake_played("E4", -10),
        fake_played("G4", 90)
    ]

    summary = summarise(
        compare_sequence(targets, performance)
    )

    assert describe_summary(summary) == (
        "2 of 3 notes on the right pitch. "
        "Average 35 cents from target."
    )


def test_summary_when_nothing_was_heard():
    from compare import compare_sequence, summarise

    summary = summarise(
        compare_sequence(["C4"], [None])
    )

    assert describe_summary(summary) == (
        "No notes were detected in that recording."
    )


def fake_audio_for(pitches, durations, bpm=120, sample_rate=8000):
    """
    Build a recording of these notes, as a Gradio audio pair.
    """

    import numpy as np
    from playback import make_melody

    rate, melody = make_melody(
        pitches,
        durations,
        bpm,
        sample_rate
    )

    return rate, np.array(melody)


def test_wrong_octave_scores_badly_by_default():
    """
    The app does not guess which octave was meant.
    """

    from music import analyse_performance

    audio = fake_audio_for(
        ["C3", "E3", "G3"],
        [1.0, 1.0, 1.0]
    )

    text, performance, tuning = analyse_performance(
        audio,
        "C4 E4 G4",
        "1 1 1",
        120
    )

    # Without saying which octave was played, singing an
    # octave low simply scores badly.
    assert "0 of 3 notes" in text


def test_analyse_performance_with_the_shift_applied():
    from music import analyse_performance

    audio = fake_audio_for(
        ["C3", "E3", "G3"],
        [1.0, 1.0, 1.0]
    )

    text, performance, tuning = analyse_performance(
        audio,
        "C4 E4 G4",
        "1 1 1",
        120,
        "One octave down"
    )

    assert "3 of 3 notes" in text
    assert "octave below" in text


def test_analyse_performance_needs_a_recording():
    from music import analyse_performance

    with pytest.raises(MusicInputError, match="Record or upload"):
        analyse_performance(None, "C4", "1", 120)


def test_shift_must_be_sensible():
    from music import check_transpose

    with pytest.raises(MusicInputError, match="three octaves"):
        check_transpose(40)


def test_octave_choices_map_to_semitones():
    from music import read_octave_choice

    assert read_octave_choice("Same octave") == 0
    assert read_octave_choice("One octave down") == -12
    assert read_octave_choice("One octave up") == 12


def test_unknown_octave_choice_is_rejected():
    from music import read_octave_choice

    with pytest.raises(MusicInputError, match="octave options"):
        read_octave_choice("Sideways")


def test_octave_choice_defaults_to_no_shift():
    from music import read_octave_choice

    assert read_octave_choice(None) == 0


def test_lyrics_are_optional():
    from music import read_lyrics

    assert read_lyrics("", 7) is None
    assert read_lyrics(None, 7) is None


def test_lyrics_must_match_the_notes():
    from music import read_lyrics

    with pytest.raises(MusicInputError, match="7 sung notes but 2"):
        read_lyrics("some words", 7)


def test_melisma_counts_as_a_syllable_slot():
    """
    An underscore holds the previous syllable through a
    note, so it fills that note's slot in the count.
    """

    from music import read_lyrics

    assert read_lyrics("star _ _", 3) == ["star", "_", "_"]


def test_hyphens_pass_through_untouched():
    from music import read_lyrics

    assert read_lyrics("Twin- kle", 2) == ["Twin-", "kle"]


def test_harmony_part_is_judged_against_harmony_notes():
    """
    Someone singing the harmony line sang the right notes,
    and must not be marked wrong against the melody.
    """

    from music import analyse_performance
    from harmony import make_harmony

    targets = "C4 E4 G4"

    harmony_line = make_harmony(
        targets.split(),
        key="C"
    )

    audio = fake_audio_for(
        harmony_line,
        [1.0, 1.0, 1.0]
    )

    text, performance, tuning = analyse_performance(
        audio,
        targets,
        "1 1 1",
        120,
        part="Harmony",
        key="C"
    )

    assert "3 of 3 notes" in text
    assert "harmony part" in text


def test_melody_part_stays_the_default():
    from music import analyse_performance

    audio = fake_audio_for(
        ["C4", "E4", "G4"],
        [1.0, 1.0, 1.0]
    )

    text, performance, tuning = analyse_performance(
        audio,
        "C4 E4 G4",
        "1 1 1",
        120
    )

    assert "3 of 3 notes" in text
    assert "harmony part" not in text


def test_unknown_part_is_rejected():
    from music import analyse_performance

    with pytest.raises(MusicInputError, match="not a part"):
        analyse_performance(
            fake_audio_for(["C4"], [1.0]),
            "C4",
            "1",
            120,
            part="Percussion"
        )


def test_harmony_part_works_in_any_key():
    from music import analyse_performance

    text, performance, tuning = analyse_performance(
        fake_audio_for(["C4"], [1.0]),
        "C4",
        "1",
        120,
        part="Harmony",
        key="D"
    )

    assert "1 of 1" in text or "0 of 1" in text


def test_guide_plays_your_part():
    """
    Practising the harmony with Your part selected plays
    the harmony line, not the melody.
    """

    from music import make_practice_guide

    sample_rate, your_part = make_practice_guide(
        "C4 E4", "1 1", 120, "Your part", "Harmony", "C"
    )

    sample_rate, melody = make_practice_guide(
        "C4 E4", "1 1", 120, "Your part", "Melody", "C"
    )

    import numpy as np

    assert not np.allclose(your_part, melody)


def test_guide_other_part_flips_the_selection():
    """
    Singing the harmony against the melody, and singing
    the melody against the harmony, hear each other's line.
    """

    from music import make_practice_guide

    import numpy as np

    sample_rate, heard_by_harmonist = make_practice_guide(
        "C4 E4", "1 1", 120, "The other part", "Harmony", "C"
    )

    sample_rate, own_melody = make_practice_guide(
        "C4 E4", "1 1", 120, "Your part", "Melody", "C"
    )

    assert np.allclose(heard_by_harmonist, own_melody)


def test_guide_rejects_unknown_choice():
    from music import make_practice_guide

    with pytest.raises(MusicInputError, match="guide option"):
        make_practice_guide(
            "C4", "1", 120, "Interpretive dance", "Melody", "C"
        )


def test_harmony_interval_choices():
    from music import read_harmony_choice

    assert read_harmony_choice("Third below") == -2
    assert read_harmony_choice("Third above") == 2
    assert read_harmony_choice(None) == -2


def test_unknown_harmony_interval_is_rejected():
    from music import read_harmony_choice

    with pytest.raises(MusicInputError, match="harmony options"):
        read_harmony_choice("Eleventh sideways")


def test_harmony_part_can_be_judged_above():
    """
    A performance of the third above is judged against the
    third above.
    """

    from music import analyse_performance, part_notes

    above = part_notes(["C4", "E4", "G4"], "Harmony", "C", 2)

    audio = fake_audio_for(above, [1.0, 1.0, 1.0])

    text, performance, tuning = analyse_performance(
        audio,
        "C4 E4 G4",
        "1 1 1",
        120,
        part="Harmony",
        key="C",
        harmony_choice="Third above"
    )

    assert "3 of 3 notes" in text


def test_midi_import_reports_candidate_keys(tmp_path):
    """
    The key dropdown is not guessed at. The feedback names
    which keys the imported notes would allow harmony in,
    and the choice stays with the player.
    """

    import mido
    from music import import_midi_file

    midi_file = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    midi_file.tracks.append(track)

    # F#4 narrows the field: it fits G and D but not C or F.
    for number in [67, 66, 62]:
        track.append(
            mido.Message("note_on", note=number, velocity=80, time=0)
        )
        track.append(
            mido.Message("note_off", note=number, velocity=0, time=480)
        )

    path = str(tmp_path / "sharp.mid")
    midi_file.save(path)

    pitches, durations, lyrics, bpm, feedback = (
        import_midi_file(path)
    )

    assert "G or D" in feedback
    assert "C" not in feedback.replace("BPM", "")


def test_midi_import_needs_a_file():
    from music import import_midi_file

    with pytest.raises(MusicInputError, match="Choose a MIDI"):
        import_midi_file(None)