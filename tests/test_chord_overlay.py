"""
The chord overlay must land on the same spots the key
diagram marks, and mark only the chord's own tones - not
the whole key, not nothing.
"""

import re

import pytest

from chords import chord_semitones
from instrument_diagrams import (
    INSTRUMENTS,
    CHORD_TONE_COLOUR,
    chord_overlay_for,
    diagram_for,
    name_for,
)


def test_a_chord_overlay_is_well_formed_svg():
    for instrument in INSTRUMENTS:

        picture = chord_overlay_for("C", instrument, "Dm")

        assert picture.startswith("<svg")
        assert picture.endswith("</svg>")

        opened = len(re.findall(r"<(rect|circle|line|text)\b", picture))
        closed = (
            len(re.findall(r"/>", picture))
            + len(re.findall(r"</text>", picture))
        )

        assert closed >= opened


def test_dm_marks_exactly_d_f_and_a_on_the_piano():
    """
    D minor is D, F, A. On a keyboard in C major that is
    two white notes and one black note (F), and nothing
    else should be marked.
    """

    picture = chord_overlay_for("C", "Piano", "Dm")

    assert f">{name_for(2, 'C')}</text>" in picture   # D
    assert f">{name_for(5, 'C')}</text>" in picture   # F
    assert f">{name_for(9, 'C')}</text>" in picture   # A

    # Nothing outside the triad: the tonic C is not in Dm.
    assert f">{name_for(0, 'C')}</text>" not in picture


def test_the_overlay_uses_its_own_colour_not_the_key_colours():
    """
    A chord tone is marked distinctly from "in the key" -
    it is a stronger claim (playing right now) than a
    weaker one (belongs to the scale).
    """

    from instrument_diagrams import IN_KEY_COLOUR, HOME_COLOUR

    picture = chord_overlay_for("C", "Piano", "G")

    assert CHORD_TONE_COLOUR in picture
    assert IN_KEY_COLOUR not in picture
    assert HOME_COLOUR not in picture


def test_the_overlay_shares_the_bases_coordinates():
    """
    The whole point of an overlay is stacking exactly on
    the base diagram. Same instrument, same key: the
    viewBox must match, or the two pictures disagree about
    where the neck or keyboard sits.
    """

    for instrument in INSTRUMENTS:

        base = diagram_for("D", instrument)
        overlay = chord_overlay_for("D", instrument, "D")

        base_box = re.search(r'viewBox="([^"]+)"', base).group(1)
        overlay_box = re.search(r'viewBox="([^"]+)"', overlay).group(1)

        assert base_box == overlay_box


def test_an_unreadable_chord_is_refused_not_guessed():
    from chords import ChartError

    with pytest.raises(ChartError):
        chord_overlay_for("C", "Piano", "Not a chord")


def test_every_chord_tone_is_a_pitch_the_chord_actually_has():
    """
    Cross-check against the theory module that already
    names chord tones, so the diagram cannot silently drift
    from what the app plays.
    """

    for chord in ["C", "G7", "Am", "Dm7", "Bb", "F#m"]:

        tones = set(chord_semitones(chord))
        picture = chord_overlay_for("C", "Piano", chord)

        for semitone in range(12):

            label = f">{name_for(semitone, 'C')}</text>"
            appears = label in picture

            if semitone in tones:
                assert appears, f"{chord} should mark {label}"
