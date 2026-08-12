"""
The mixer block, as far as Python can see it.

What's left here is specific to mixer_html and MIXER_JS -
the HTML page and the JavaScript that wires it up. The
data underneath (sound encoding, the chart timeline,
opening levels and colours) is tested in test_mixer_data.py
against the module that now owns it. This split matters
because mixer_block.py is the gr.HTML mixer on its way out;
when it goes, this file goes with it and test_mixer_data.py
is unaffected.

What happens after the HTML is rendered - decoding, gain
nodes, the playhead - runs in a browser and is invisible to
pytest. That boundary is worth naming rather than pretending
these tests cover the feature.
"""

from mixer_block import mixer_html, MIXER_JS
from music import LAYER_NAMES, load_wellerman


def song():
    return load_wellerman()


def test_every_layer_is_sent_as_its_own_sound():
    """
    The point of the block: the parts arrive apart, so a
    level can move without anything being made again.
    """

    pitches, durations, lyrics, key, chart, tempo = song()

    html = mixer_html(
        pitches, durations, key, tempo, chart,
        lyric_text=lyrics, phrase_label="Whole part"
    )

    for name in LAYER_NAMES:
        assert f'&quot;{name}&quot;' in html


def test_no_chart_means_no_strip_and_no_missing_faders():
    """
    Bass and chords come from the chart. Without one they
    are absent rather than silent, and the block says so
    instead of offering faders that do nothing.
    """

    html = mixer_html("C4 D4 E4", "1 1 1", "C", 120, "")

    assert '&quot;Bass&quot;' not in html
    assert '&quot;Chords&quot;' not in html

    assert "No chord chart" in html


def test_a_phrase_is_a_smaller_thing_to_send_than_a_song():
    """
    The parts travel as sound, so the whole song is a large
    block. Worth knowing rather than discovering on a
    slow connection.
    """

    pitches, durations, lyrics, key, chart, tempo = song()

    from music import list_phrases

    labels = list_phrases(pitches, durations, lyrics)

    phrase = mixer_html(
        pitches, durations, key, tempo, chart,
        lyric_text=lyrics, phrase_label=labels[5]
    )

    whole = mixer_html(
        pitches, durations, key, tempo, chart,
        lyric_text=lyrics, phrase_label="Whole part"
    )

    assert len(phrase) < len(whole) / 4


def test_mixer_html_contains_no_inline_script():
    """
    Gradio inserts an HTML output with innerHTML, so an inline
    script there would be visible but would not execute.  The
    executable mixer code belongs in js_on_load instead.
    """

    html = mixer_html("C4 D4 E4", "1 1 1", "C", 120, "")

    assert "<script" not in html.lower()


def test_mixer_html_carries_data_for_js_on_load():
    """
    The Python-built sounds and timeline cross into the browser
    as data attributes for MIXER_JS to read after rendering.
    """

    pitches, durations, lyrics, key, chart, tempo = song()

    html = mixer_html(
        pitches, durations, key, tempo, chart,
        lyric_text=lyrics, phrase_label="Whole part"
    )

    assert 'data-layers=' in html
    assert 'data-timeline=' in html
    assert '&quot;Melody&quot;' in html


def test_mixer_js_reinitialises_after_html_value_changes():
    """
    Build the mixer replaces gr.HTML's value.  The js_on_load
    hook therefore has to watch that value and wire the newly
    rendered controls each time, not just on initial page load.
    """

    assert 'watch("value"' in MIXER_JS
    assert "initialiseMixer" in MIXER_JS
    assert 'element.querySelector("#mixer")' in MIXER_JS