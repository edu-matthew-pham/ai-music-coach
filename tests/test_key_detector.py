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
    pitches, durations, lyrics, key = load_wellerman_phrase()

    pitch_list, duration_list = read_music(pitches, durations)

    name = best_key(pitch_list, duration_list)

    assert name.startswith("D")


def test_twinkle_sounds_like_c():
    pitches, durations, lyrics, key = load_twinkle_phrase()

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

    pitches, durations, lyrics, key = load_twinkle_phrase()

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

    pitches, durations, lyrics, key = load_wellerman_phrase()

    report = suggest_key(pitches, durations)

    assert "D minor" in report
    assert "Closest matches" in report
    assert "Harmony can be built in" in report


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