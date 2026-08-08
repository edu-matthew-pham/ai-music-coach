"""
The guide has to stay true.

Documentation drifts from code silently: nothing fails
when a help page keeps describing a syntax that changed.
These tests tie the wording to the things it describes, so
that renaming a marker or adding a key breaks the guide
loudly rather than leaving it quietly wrong.
"""

from help_text import HELP_TEXT
from notes import REST
from harmony import MAJOR_SCALES
from music import read_beats, read_music


def test_the_guide_says_how_to_write_a_rest():
    assert REST in HELP_TEXT


def test_the_guide_counts_the_keys_correctly():
    assert str(len(MAJOR_SCALES)) in HELP_TEXT


def test_every_duration_the_guide_shows_can_be_read():
    """
    The lengths given as examples must actually parse.
    """

    for text in ["1", "1/2", "1/4", "3/2", "1/3"]:
        assert read_beats(text) > 0
        assert text in HELP_TEXT


def test_the_example_in_the_guide_is_real_music():
    """
    The guide points at the Twinkle button, so that button
    has to exist and produce something playable.
    """

    from music import load_twinkle_phrase

    assert "Twinkle" in HELP_TEXT

    pitches, durations, lyrics, key = load_twinkle_phrase()

    pitch_list, duration_list = read_music(pitches, durations)

    assert len(pitch_list) == len(duration_list)


# The controls a newcomer has to find to record a take.
CONTROLS = [
    "Detect key",
    "Part",
    "Guide while recording",
    "Octave",
    "Generate Playback",
    "Compare"
]


def test_the_guide_covers_the_main_controls():
    """
    Someone reading this should meet every control they
    will have to touch to record and compare a take.
    """

    for control in CONTROLS:
        assert control in HELP_TEXT, control


def test_the_guide_calls_the_controls_what_the_screen_does():
    """
    A guide naming a button that is labelled differently
    on screen sends people looking for something that is
    not there. This is the failure that documentation
    normally suffers in silence.
    """

    import os

    interface = open(
        os.path.join(
            os.path.dirname(__file__), "..", "main.py"
        )
    ).read()

    for control in CONTROLS:
        assert control in interface, control


def test_the_guide_explains_the_tuning_numbers():
    assert "cents" in HELP_TEXT
    assert "fifteen" in HELP_TEXT
