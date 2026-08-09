"""
Key detection: naming what the music is in.

This is a different question from which keys the app can
build a harmony in. A piece in D minor is in D minor
whether or not the odd accidental strays outside it.
"""

import pytest

from key_detector import (
    detect_key,
    describe_key,
    time_on_each_pitch
)
from music import (
    load_twinkle_phrase,
    load_wellerman_phrase,
    read_music
)


def best_key(pitches, durations):
    return detect_key(pitches, durations)[0][0]


def test_a_major_scale_names_its_key():
    pitches = ["C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5"]
    durations = [1.0] * 8

    # The tonic weighted as music weights it: start and end.
    durations[0] = 2.0
    durations[-1] = 2.0

    assert best_key(pitches, durations) == "C major"


def test_a_minor_melody_names_its_key():
    # A natural minor line settling on A.
    pitches = ["A3", "B3", "C4", "D4", "E4", "C4", "A3"]
    durations = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 2.0]

    assert best_key(pitches, durations) == "A minor"


def test_the_wellerman_is_in_d_minor():
    pitches, durations, lyrics, key, chart = load_wellerman_phrase()

    pitch_list, duration_list = read_music(pitches, durations)

    name = best_key(pitch_list, duration_list)

    assert name.startswith("D")


def test_twinkle_sounds_like_c():
    pitches, durations, lyrics, key, chart = load_twinkle_phrase()

    pitch_list, duration_list = read_music(pitches, durations)

    assert "C major" in [
        name for name, score in
        detect_key(pitch_list, duration_list)[:2]
    ]


def test_rests_spend_no_time_on_any_pitch():
    spent = time_on_each_pitch(
        ["C4", "R", "C4"],
        [1.0, 5.0, 1.0]
    )

    assert sum(spent) == 2.0


def test_a_near_tie_is_named_as_a_pair():
    """
    A short plain melody often genuinely fits two keys,
    and naming one alone would be a guess dressed up as
    an answer.
    """

    pitches, durations, lyrics, key, chart = load_twinkle_phrase()

    pitch_list, duration_list = read_music(pitches, durations)

    sentence = describe_key(pitch_list, duration_list)

    assert " or " in sentence


def test_a_clear_key_is_named_alone():
    pitches = [
        "D4", "E4", "F#4", "G4", "A4", "B4", "C#5", "D5",
        "D4", "A4", "D4"
    ]
    durations = [1.0] * 8 + [2.0, 2.0, 2.0]

    sentence = describe_key(pitches, durations)

    assert sentence == "This sounds like D major."


def test_flat_keys_go_by_their_flat_names():
    """
    The key of B flat is never called A sharp, even though
    the tonic is the same sound.
    """

    pitches = [
        "Bb3", "C4", "D4", "Eb4", "F4", "G4", "A4", "Bb4",
        "Bb3", "F4", "Bb3"
    ]
    durations = [1.0] * 8 + [2.0, 2.0, 2.0]

    assert best_key(pitches, durations) == "Bb major"


def test_the_key_report_ranks_candidates():
    """
    The report names the likeliest key and shows what else
    the music could be, with scores, so the choice stays
    informed and with the player.
    """

    from music import suggest_key

    pitches, durations, lyrics, key, chart = load_wellerman_phrase()

    report = suggest_key(pitches, durations)

    assert "D minor" in report
    assert "Also possible" in report or "Nothing else" in report
    assert "set the key to" in report


def test_key_fit_reports_rather_than_refuses():
    """
    Choosing a key that does not contain every note is
    allowed: it is described, not forbidden.
    """

    from music import describe_key_fit

    assert describe_key_fit(["D4", "F#4", "A4"], "D") is None

    sentence = describe_key_fit(["D4", "G#4", "A4"], "D")

    assert "G#4" in sentence
    assert "nearest note" in sentence


def test_the_whole_texture_names_the_key_more_surely():
    """
    A key is heard in everything sounding at once, not in
    one line of it. The other voices are exactly what tell
    a listener which key a melody sits in, so reading them
    should leave less doubt, not more.
    """

    import os
    import mido

    from midi_import import read_all_notes, read_notes, keep_melody
    from notes import midi_to_note

    path = os.path.join(
        os.path.dirname(__file__),
        "fixtures",
        "midi",
        "o-holy-night-satb.mid"
    )

    if not os.path.exists(path):
        pytest.skip("o holy night fixture not present")

    # The soprano line alone.
    midi_file = mido.MidiFile(path)
    notes, bpm = read_notes(midi_file, 1)
    melody = keep_melody(notes)

    line_pitches = [
        midi_to_note(number) for start, length, number in melody
    ]
    line_durations = [
        length for start, length, number in melody
    ]

    # Everything sounding, all parts together.
    all_pitches, all_durations = read_all_notes(path)

    assert len(all_pitches) > len(line_pitches)

    from_line = detect_key(line_pitches, line_durations)
    from_all = detect_key(all_pitches, all_durations)

    # The same key, named with a wider margin over the
    # next best guess.
    assert from_line[0][0] == from_all[0][0] == "D major"

    line_margin = from_line[0][1] - from_line[1][1]
    all_margin = from_all[0][1] - from_all[1][1]

    assert all_margin > line_margin


def test_the_key_report_needs_no_file():
    """
    Detecting the key reads the music boxes, so it works
    on notes typed by hand as much as on an import.
    """

    from music import suggest_key

    report = suggest_key(
        "D4 E4 F4 G4 A4 Bb4 A4 D4",
        "1 1 1 1 1 1 1 2"
    )

    assert "D minor" in report


def test_import_feedback_does_not_claim_harmony_is_unavailable():
    """
    Harmony works in any key now, so the feedback must
    recommend rather than refuse.
    """

    import os

    from music import import_midi_file, list_midi_tracks

    path = os.path.join(
        os.path.dirname(__file__),
        "fixtures",
        "midi",
        "o-holy-night-satb.mid"
    )

    if not os.path.exists(path):
        pytest.skip("o holy night fixture not present")

    tracks = list_midi_tracks(path)

    # Parts are offered likeliest tune first, so the one
    # to test with is chosen by what it holds rather than
    # by where it sits in the list.
    chromatic = [
        label for label in tracks
        if "Pan Flute" in label or "Grand Piano" in label
    ]

    pitches, durations, lyrics, bpm, feedback, chart = (
        import_midi_file(path, chromatic[0])
    )

    assert "not available" not in feedback


def test_a_detected_minor_key_names_a_key_setting():
    """
    The detector names minor keys, but harmony is built
    from major scales, so the report has to say which
    setting to actually choose.
    """

    from music import key_setting_for

    assert key_setting_for("D minor") == "F"
    assert key_setting_for("A minor") == "C"
    assert key_setting_for("D major") == "D"


def test_the_report_names_the_setting_to_choose():
    from music import suggest_key

    pitches, durations, lyrics, key, chart = load_wellerman_phrase()

    report = suggest_key(pitches, durations)

    assert "set the key to F major / D minor" in report


def test_the_report_names_every_setting_that_fits():
    """
    A short melody touches few pitches, and those pitches
    sit inside several keys. Naming only the likeliest
    would hide settings that work just as well.
    """

    from music import suggest_key

    pitches, durations, lyrics, key, chart = load_wellerman_phrase()

    report = suggest_key(pitches, durations)

    # The line uses only A, D and F, which C major holds
    # as surely as F major does.
    assert "C major / A minor" in report
    assert "also fit" in report


def test_how_many_candidates_depends_on_the_music():
    """
    How many keys a piece could be in is a property of the
    music, not a fixed number of rows to fill.

    A melody circling one triad names its key at once. A
    melody that wanders the scale without settling leaves
    several keys equally possible, and all of them are
    worth showing.
    """

    from key_detector import plausible_keys

    # Landing hard on the tonic and fifth of D minor.
    settled = plausible_keys(
        ["D4", "A4", "D4"],
        [2.0, 2.0, 4.0]
    )

    # Even time on every note of a scale, settling
    # nowhere, so the tonic could be any of them.
    wandering = plausible_keys(
        ["C4", "D4", "E4", "F4", "G4", "A4", "B4"],
        [1.0] * 7
    )

    assert len(settled) < len(wandering)


def test_candidates_never_run_past_the_limit():
    from key_detector import plausible_keys, MOST_CANDIDATES

    # A chromatic scale suits nothing in particular, so
    # everything scores about the same.
    pitches = [
        "C4", "C#4", "D4", "D#4", "E4", "F4",
        "F#4", "G4", "G#4", "A4", "A#4", "B4"
    ]

    candidates = plausible_keys(pitches, [1.0] * 12)

    assert len(candidates) <= MOST_CANDIDATES


def test_the_best_candidate_is_always_shown():
    from key_detector import plausible_keys, detect_key

    pitches = ["D4", "F4", "A4", "D5"]
    durations = [2.0, 1.0, 1.0, 2.0]

    best = detect_key(pitches, durations)[0]

    assert plausible_keys(pitches, durations)[0] == best