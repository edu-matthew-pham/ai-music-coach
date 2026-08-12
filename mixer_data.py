# mixer_data.py

"""
The data half of the mixer, unchanged by the move to a
component.

separate_layers, as_wav_data and the timeline logic already
exist and are already tested - moving from an HTML block to
a real component changes delivery, not synthesis. This
module is the seam: it assembles the dictionary the
MusicMixer component's value expects, from the same
functions mixer_block.py used.

Kept separate from mixer_block.py deliberately, so the old
block and the new component can both exist while the
component is being proven, and mixer_block.py can be
deleted without touching this file.
"""

from music import LAYER_NAMES, separate_layers
from mixer_block import as_wav_data, _timeline, OPENING_LEVELS, LAYER_COLOURS


def mixer_data(
    pitch_text,
    duration_text,
    key,
    bpm=120,
    chart_text="",
    harmony_style="Thirds, chord-corrected",
    lyric_text="",
    phrase_label=None
):
    """
    The dictionary a MusicMixer component's value expects.

    loop_start and loop_end are left unset here: those are
    the browser's to fill in, and a freshly built mixer
    should open with nothing looped.
    """

    sample_rate, parts = separate_layers(
        pitch_text, duration_text, key, bpm, chart_text,
        harmony_style, lyric_text, phrase_label
    )

    layers = []

    for name in LAYER_NAMES:

        track = parts.get(name)

        if track is None:
            continue

        layers.append({
            "name": name,
            "level": OPENING_LEVELS.get(name, 0.0),
            "colour": LAYER_COLOURS.get(name, "#37474f"),
            "wav": as_wav_data(track, sample_rate)
        })

    timeline = _timeline(
        pitch_text, duration_text, key, bpm, chart_text,
        lyric_text, phrase_label
    )

    return {
        "layers": layers,
        "timeline": timeline,
        "loop_start": None,
        "loop_end": None
    }


def loop_region(mixer_value):
    """
    The stretch a person selected, in seconds - or None if
    nothing is looped.

    This is what a Compare handler reads once the mixer's
    value comes back from the browser: the loop a person
    chose by ear is what they should be judged against.
    """

    if not mixer_value:
        return None

    start = mixer_value.get("loop_start")
    end = mixer_value.get("loop_end")

    if start is None or end is None:
        return None

    return start, end
