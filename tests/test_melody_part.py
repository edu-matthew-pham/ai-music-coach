"""
The Melody section's Part choice (melody_lanes.melody_page), for a
song of several tunes: it mirrors the mixer's "Your part" (shown only
when there is more than one, starting on the first) and is separate
from it.

Expectations are read off the partner songs in examples.py by hand:
two tunes, "Three Blind Mice" (first; its words start "Three blind
mice", its first note A4) and "Frere Jacques" (words "Fre- re Jac-
ques", four lines; first sung note F4 after four rests).
"""

import ast
import os
import re

from examples import load_partner_songs, load_twinkle
from melody_lanes import keep_part, melody_page
from music import WHOLE_PART

KALIMBA = "Kalimba, 41 keys"
MICE = "Three Blind Mice"
FRERE = "Frere Jacques"


def _page(song, part=None, phrase=WHOLE_PART, instruments=(KALIMBA,)):
    pitches, durations, lyrics, key, chart, _tempo = song()

    return melody_page(
        pitches, durations, lyrics, key, chart, phrase,
        list(instruments), part_label=part,
    )


def _words(html):
    return re.findall(r'font-size="12" fill="#37474f">([^<]*)<', html)


def test_a_song_of_several_tunes_lists_them_in_order():
    page = _page(load_partner_songs)

    assert page["parts"] == [MICE, FRERE]


def test_it_starts_on_the_first_tune_as_the_mixer_does():
    page = _page(load_partner_songs)

    assert page["part"] == MICE
    assert _words(page["views"][0])[:3] == ["Three", "blind", "mice"]


def test_choosing_a_tune_draws_that_tune():
    page = _page(load_partner_songs, FRERE)

    assert page["part"] == FRERE
    assert _words(page["views"][0])[:4] == ["Fre-", "re", "Jac-", "ques"]
    assert "Three" not in _words(page["views"][0])


def test_the_phrase_list_is_the_chosen_tunes_own():
    mice = _page(load_partner_songs, MICE)["choices"]
    frere = _page(load_partner_songs, FRERE)["choices"]

    # Mice has eight lines of words, Frere Jacques four.
    assert len(mice) == 1 + 8
    assert len(frere) == 1 + 4
    assert frere[1].startswith("Phrase 1: Frere Jacques")


def test_a_phrase_of_the_chosen_tune_is_drawn():
    choices = _page(load_partner_songs, FRERE)["choices"]
    page = _page(load_partner_songs, FRERE, choices[2])

    assert _words(page["views"][0]) == ["Dor-", "mez", "vous",
                                        "Dor-", "mez", "vous"]


def test_a_song_of_one_tune_has_nothing_to_choose():
    page = _page(load_twinkle)

    assert page["parts"] == []
    assert page["part"] is None


def test_a_stale_choice_falls_back_to_the_first_tune():
    assert keep_part("Alto", [MICE, FRERE]) == MICE
    assert keep_part(FRERE, [MICE, FRERE]) == FRERE
    assert keep_part(FRERE, []) is None


def test_every_instrument_tab_shows_the_same_tune():
    page = _page(load_partner_songs, FRERE,
                 instruments=(KALIMBA, "Lever harp, 19 strings", "Flute"))

    for view in page["views"]:
        assert "Three" not in view
        assert "Fre-" in view


# --- the screen ----------------------------------------------------

MAIN = os.path.join(os.path.dirname(__file__), "..", "main.py")


def _main_text():
    with open(MAIN) as source:
        return source.read()


def test_the_part_choice_is_in_the_bar_hidden_until_needed():
    text = _main_text()
    start = text.index("melody_part = gr.Dropdown(")
    block = text[start:text.index(")", start)]

    assert 'label="Part"' in block
    assert "visible=False" in block
    # In the slim bar, after the phrase list and before Show.
    assert text.index("melody_phrase = gr.Dropdown(") < start
    assert start < text.index("melody_show = gr.CheckboxGroup(")


def test_the_part_choice_is_redrawn_shown_only_for_several_tunes():
    text = _main_text()

    assert 'visible=len(page["parts"]) > 1' in text
    assert "melody_part.change" in text


def test_the_part_choice_belongs_to_the_melody_section_alone():
    # Made once, read by the Melody redraw, written by it, and a change
    # redraws it: nothing else (the mixer has its own "Your part").
    assert _main_text().count("melody_part") == 4
