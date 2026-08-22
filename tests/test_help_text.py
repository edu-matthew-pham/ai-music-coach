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

    from examples import load_twinkle_phrase

    assert "Twinkle" in HELP_TEXT

    pitches, durations, lyrics, key, chart = load_twinkle_phrase()

    pitch_list, duration_list = read_music(pitches, durations)

    assert len(pitch_list) == len(duration_list)


# The controls a newcomer has to find to hear a song and
# sing along to it. The record-then-Compare flow (Part,
# Guide while recording, Compare) is hidden for now - the
# mixer's own live mic covers it - so the guide names the
# live controls instead, and the screen check below only
# looks at what is actually rendered.
CONTROLS = [
    "Detect key",
    "Octave down",
    "Generate Playback",
    "Mic",
    "Record",
]


def test_the_guide_covers_the_main_controls():
    """
    Someone reading this should meet every control they
    will have to touch to hear a song and sing along.
    """

    for control in CONTROLS:
        assert control in HELP_TEXT, control


def test_the_guide_calls_the_controls_what_the_screen_does():
    """
    A guide naming a button that is labelled differently
    on screen sends people looking for something that is
    not there. This is the failure that documentation
    normally suffers in silence.

    The mixer's own controls (Mic, Record) live in the
    frontend, not main.py, so both are checked: a control
    the guide names must appear in one of the two places a
    user could actually see it.
    """

    import os

    here = os.path.dirname(__file__)
    interface = open(os.path.join(here, "..", "main.py")).read()
    transport = open(
        os.path.join(
            here, "..", "musicmixer", "frontend",
            "TransportSettings.svelte"
        )
    ).read()

    for control in CONTROLS:
        assert control in interface or control in transport, control


def test_the_interface_ignores_events_with_no_file():
    """
    Clearing a dropdown fires its change event, so the
    import handlers are called when the file has just been
    cleared. That must do nothing rather than throw an
    error at someone who only pressed Load Twinkle.
    """

    import os

    interface = open(
        os.path.join(
            os.path.dirname(__file__), "..", "main.py"
        )
    ).read()

    # Every handler that takes a file guards against its
    # absence before asking the music layer for anything.
    assert interface.count("if file_path is None") >= 2

    # And the guard comes before the work in each case.
    for handler in [
        "def import_and_show",
        "def import_track"
    ]:
        start = interface.index(handler)
        body = interface[start:start + 600]

        assert "is None" in body, handler


def test_the_guide_explains_the_chart_syntax():
    """
    Neither the bar lines nor the dots are guessable, so
    the guide has to show them, and what it shows has to
    parse.
    """

    from chords import read_chart

    assert "Chords" in HELP_TEXT
    assert "| Dm" in HELP_TEXT

    for example in [
        "| Dm .  Bb . | F  .  .  . |",
        "| Dm .  .    | F  .  .    |"
    ]:
        assert example in HELP_TEXT

        chords, bars = read_chart(example)

        assert len(chords) > 0