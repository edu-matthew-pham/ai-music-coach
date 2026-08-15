"""
demo/app.py - the component with real music in it.

The generated demo passed no value, which was useful for
checking the component mounts but shows an empty shell.
This loads an actual song through the same mixer_data()
the app itself will use, so what appears here is what will
appear in the app: six faders, a chord strip, and a loop
region that reports back.

Run from the component folder with `gradio cc dev`, then
open the backend server (127.0.0.1:7861). The frontend
dev server on 7862 only adds hot reload and is broken in
this version pairing.
"""

import sys
from pathlib import Path

import gradio as gr

from gradio_musicmixer import MusicMixer

# The app itself lives one level up. Added to the path so
# this demo uses the real separate_layers and timeline
# rather than a copy that could drift from them.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mixer_data import mixer_data, loop_region  # noqa: E402
from music import load_wellerman, load_twinkle  # noqa: E402


def build():
    """
    The Wellerman, whole, through the real data path.
    """

    pitches, durations, lyrics, key, chart, tempo = load_wellerman()

    return mixer_data(
        pitches,
        durations,
        key,
        tempo,
        chart,
        lyric_text=lyrics,
        phrase_label="Whole part"
    )


def build_other():
    """
    A second, different song through the same real data
    path - Twinkle rather than the Wellerman.

    Exists for the song-swap test: loading a different song
    into a mixer that already has a loop selected is the one
    thing the single-song demo could never exercise on its
    own, and it is exactly the case the fingerprint fix in
    the engine is for. Its own chart also has a genuine
    multi-chord bar (bar 2: F then C), which the bar-grouped
    strip test reuses rather than building a third fixture
    for the same shape.
    """

    pitches, durations, lyrics, key, chart, tempo = load_twinkle()

    return mixer_data(
        pitches,
        durations,
        key,
        tempo,
        chart,
        lyric_text=lyrics,
        phrase_label="Whole part"
    )


def build_intro():
    """
    A short, made-up fixture for the one shape neither real
    song happens to have: a wordless instrumental bar. Bar 1
    is a bar of rest under a held Em with nothing sung; bar
    2 sings four words under a bar that itself splits D then
    G - both symptoms the bar-grouped strip was built to
    fix, in two bars' worth of music. Verified directly
    against mixer_data() (not just assumed from the fixture)
    before being wired up here.
    """

    return mixer_data(
        "R R R R C4 D4 E4 F4",
        "1 1 1 1 1 1 1 1",
        "C",
        120,
        "| Em . . . | D . G . |",
        lyric_text="here we go now",
        phrase_label=None
    )


def report(value):
    print("[test.py] report() loop_start:", value.get("loop_start") if value else None,
          "loop_end:", value.get("loop_end") if value else None)
    region = loop_region(value)
    if region is None:
        return "Nothing looped yet. Click a bar, then shift-click a later one."
    start, end = region
    return f"Looping {start:.2f}s to {end:.2f}s ({end - start:.2f}s long)."


with gr.Blocks() as demo:

    gr.Markdown(
        "## MusicMixer\n"
        "Press **Build** to load the Wellerman, then Play. "
        "Move a fader while it is playing - the level should "
        "change without anything being rebuilt.\n\n"
        "Click a bar to jump there. Shift-click a later bar "
        "to loop that stretch. The line underneath is Python "
        "receiving the loop region back from the browser."
    )

    build_button = gr.Button("Build the mixer", variant="primary")
    build_other_button = gr.Button("Load a different song")
    build_intro_button = gr.Button("Load a wordless intro")

    mixer = MusicMixer(label="Mix it live", key="mixer")

    readout = gr.Markdown()

    build_button.click(fn=build, inputs=None, outputs=mixer)
    build_other_button.click(fn=build_other, inputs=None, outputs=mixer)
    build_intro_button.click(fn=build_intro, inputs=None, outputs=mixer)

    mixer.change(fn=report, inputs=mixer, outputs=readout)


if __name__ == "__main__":
    demo.launch()