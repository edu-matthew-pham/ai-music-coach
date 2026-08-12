
import gradio as gr
from app import demo as app
import os

_docs = {'MusicMixer': {'description': 'A live mixer: several sound layers played together in\nthe browser, a chord strip that follows them, and a\nloop region chosen by clicking it.\n\nUnlike gr.HTML, the value travels both ways. Python\nsets layers and timeline; the browser sets loop_start\nand loop_end whenever a person selects a stretch to\nlisten to or sing against - which is the entire reason\nthis exists rather than an HTML block.', 'members': {'__init__': {'value': {'type': 'dict | Callable | None', 'default': 'value = None', 'description': 'a dict with `layers`, `timeline`,'}, 'label': {'type': 'str | I18nData | None', 'default': 'value = None', 'description': 'shown above the component if show_label'}, 'every': {'type': "'Timer | float | None'", 'default': 'value = None', 'description': 'recalculates `value` on a timer if `value`'}, 'inputs': {'type': 'Component | Sequence[Component] | set[Component] | None', 'default': 'value = None', 'description': 'components `value` is recalculated from,'}, 'show_label': {'type': 'bool | None', 'default': 'value = None', 'description': 'whether to display the label.'}, 'scale': {'type': 'int | None', 'default': 'value = None', 'description': 'relative width compared to siblings in a'}, 'min_width': {'type': 'int', 'default': 'value = 160', 'description': 'minimum pixel width before wrapping.'}, 'visible': {'type': 'bool', 'default': 'value = True', 'description': 'whether the component is shown.'}, 'elem_id': {'type': 'str | None', 'default': 'value = None', 'description': 'HTML id, for CSS targeting.'}, 'elem_classes': {'type': 'list[str] | str | None', 'default': 'value = None', 'description': 'HTML classes, for CSS targeting.'}, 'render': {'type': 'bool', 'default': 'value = True', 'description': 'if False, do not render in the Blocks'}, 'key': {'type': 'int | str | tuple[int | str, ...] | None', 'default': 'value = None', 'description': 'identifies this component as the same one'}, 'preserved_by_key': {'type': 'list[str] | str | None', 'default': 'value = "value"', 'description': 'constructor parameters kept'}}, 'postprocess': {'value': {'type': 'dict| None', 'description': 'a dict built by mixer_data() - layers and'}}, 'preprocess': {'return': {'type': 'dict| None', 'description': 'The same dict, unchanged. A handler reading'}, 'value': None}}, 'events': {'change': {'type': None, 'default': None, 'description': 'Triggered when the value of the MusicMixer changes either because of user input (e.g. a user types in a textbox) OR because of a function update (e.g. an image receives a value from the output of an event trigger). See `.input()` for a listener that is only triggered by user input.'}, 'input': {'type': None, 'default': None, 'description': 'This listener is triggered when the user changes the value of the MusicMixer.'}}}, '__meta__': {'additional_interfaces': {}, 'user_fn_refs': {'MusicMixer': []}}}

abs_path = os.path.join(os.path.dirname(__file__), "css.css")

with gr.Blocks(
    css=abs_path,
    theme=gr.themes.Default(
        font_mono=[
            gr.themes.GoogleFont("Inconsolata"),
            "monospace",
        ],
    ),
) as demo:
    gr.Markdown(
"""
# `gradio_musicmixer`

<div style="display: flex; gap: 7px;">
<img alt="Static Badge" src="https://img.shields.io/badge/version%20-%200.0.1%20-%20orange">  
</div>

Python library for easily interacting with trained machine learning models
""", elem_classes=["md-custom"], header_links=True)
    app.render()
    gr.Markdown(
"""
## Installation

```bash
pip install gradio_musicmixer
```

## Usage

```python
\"\"\"
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
\"\"\"

import sys
from pathlib import Path

import gradio as gr

from gradio_musicmixer import MusicMixer

# The app itself lives one level up. Added to the path so
# this demo uses the real separate_layers and timeline
# rather than a copy that could drift from them.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mixer_data import mixer_data, loop_region  # noqa: E402
from music import load_wellerman  # noqa: E402


def build():
    \"\"\"
    The Wellerman, whole, through the real data path.
    \"\"\"

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

    mixer = MusicMixer(label="Mix it live", key="mixer")

    readout = gr.Markdown()

    build_button.click(fn=build, inputs=None, outputs=mixer)

    mixer.change(fn=report, inputs=mixer, outputs=readout)


if __name__ == "__main__":
    demo.launch()
```
""", elem_classes=["md-custom"], header_links=True)


    gr.Markdown("""
## `MusicMixer`

### Initialization
""", elem_classes=["md-custom"], header_links=True)

    gr.ParamViewer(value=_docs["MusicMixer"]["members"]["__init__"], linkify=[])


    gr.Markdown("### Events")
    gr.ParamViewer(value=_docs["MusicMixer"]["events"], linkify=['Event'])




    gr.Markdown("""

### User function

The impact on the users predict function varies depending on whether the component is used as an input or output for an event (or both).

- When used as an Input, the component only impacts the input signature of the user function.
- When used as an output, the component only impacts the return signature of the user function.

The code snippet below is accurate in cases where the component is used as both an input and an output.

- **As input:** Is passed, the same dict, unchanged. A handler reading.
- **As output:** Should return, a dict built by mixer_data() - layers and.

 ```python
def predict(
    value: dict| None
) -> dict| None:
    return value
```
""", elem_classes=["md-custom", "MusicMixer-user-fn"], header_links=True)




    demo.load(None, js=r"""function() {
    const refs = {};
    const user_fn_refs = {
          MusicMixer: [], };
    requestAnimationFrame(() => {

        Object.entries(user_fn_refs).forEach(([key, refs]) => {
            if (refs.length > 0) {
                const el = document.querySelector(`.${key}-user-fn`);
                if (!el) return;
                refs.forEach(ref => {
                    el.innerHTML = el.innerHTML.replace(
                        new RegExp("\\b"+ref+"\\b", "g"),
                        `<a href="#h-${ref.toLowerCase()}">${ref}</a>`
                    );
                })
            }
        })

        Object.entries(refs).forEach(([key, refs]) => {
            if (refs.length > 0) {
                const el = document.querySelector(`.${key}`);
                if (!el) return;
                refs.forEach(ref => {
                    el.innerHTML = el.innerHTML.replace(
                        new RegExp("\\b"+ref+"\\b", "g"),
                        `<a href="#h-${ref.toLowerCase()}">${ref}</a>`
                    );
                })
            }
        })
    })
}

""")

demo.launch()
