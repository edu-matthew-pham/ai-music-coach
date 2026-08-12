
# `gradio_musicmixer`
<img alt="Static Badge" src="https://img.shields.io/badge/version%20-%200.0.1%20-%20orange">  

Python library for easily interacting with trained machine learning models

## Installation

```bash
pip install gradio_musicmixer
```

## Usage

```python
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
    the engine is for.
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

    mixer = MusicMixer(label="Mix it live", key="mixer")

    readout = gr.Markdown()

    build_button.click(fn=build, inputs=None, outputs=mixer)
    build_other_button.click(fn=build_other, inputs=None, outputs=mixer)

    mixer.change(fn=report, inputs=mixer, outputs=readout)


if __name__ == "__main__":
    demo.launch()
```

## `MusicMixer`

### Initialization

<table>
<thead>
<tr>
<th align="left">name</th>
<th align="left" style="width: 25%;">type</th>
<th align="left">default</th>
<th align="left">description</th>
</tr>
</thead>
<tbody>
<tr>
<td align="left"><code>value</code></td>
<td align="left" style="width: 25%;">

```python
dict | Callable | None
```

</td>
<td align="left"><code>value = None</code></td>
<td align="left">a dict with `layers`, `timeline`,</td>
</tr>

<tr>
<td align="left"><code>label</code></td>
<td align="left" style="width: 25%;">

```python
str | I18nData | None
```

</td>
<td align="left"><code>value = None</code></td>
<td align="left">shown above the component if show_label</td>
</tr>

<tr>
<td align="left"><code>every</code></td>
<td align="left" style="width: 25%;">

```python
'Timer | float | None'
```

</td>
<td align="left"><code>value = None</code></td>
<td align="left">recalculates `value` on a timer if `value`</td>
</tr>

<tr>
<td align="left"><code>inputs</code></td>
<td align="left" style="width: 25%;">

```python
Component | Sequence[Component] | set[Component] | None
```

</td>
<td align="left"><code>value = None</code></td>
<td align="left">components `value` is recalculated from,</td>
</tr>

<tr>
<td align="left"><code>show_label</code></td>
<td align="left" style="width: 25%;">

```python
bool | None
```

</td>
<td align="left"><code>value = None</code></td>
<td align="left">whether to display the label.</td>
</tr>

<tr>
<td align="left"><code>scale</code></td>
<td align="left" style="width: 25%;">

```python
int | None
```

</td>
<td align="left"><code>value = None</code></td>
<td align="left">relative width compared to siblings in a</td>
</tr>

<tr>
<td align="left"><code>min_width</code></td>
<td align="left" style="width: 25%;">

```python
int
```

</td>
<td align="left"><code>value = 160</code></td>
<td align="left">minimum pixel width before wrapping.</td>
</tr>

<tr>
<td align="left"><code>visible</code></td>
<td align="left" style="width: 25%;">

```python
bool
```

</td>
<td align="left"><code>value = True</code></td>
<td align="left">whether the component is shown.</td>
</tr>

<tr>
<td align="left"><code>elem_id</code></td>
<td align="left" style="width: 25%;">

```python
str | None
```

</td>
<td align="left"><code>value = None</code></td>
<td align="left">HTML id, for CSS targeting.</td>
</tr>

<tr>
<td align="left"><code>elem_classes</code></td>
<td align="left" style="width: 25%;">

```python
list[str] | str | None
```

</td>
<td align="left"><code>value = None</code></td>
<td align="left">HTML classes, for CSS targeting.</td>
</tr>

<tr>
<td align="left"><code>render</code></td>
<td align="left" style="width: 25%;">

```python
bool
```

</td>
<td align="left"><code>value = True</code></td>
<td align="left">if False, do not render in the Blocks</td>
</tr>

<tr>
<td align="left"><code>key</code></td>
<td align="left" style="width: 25%;">

```python
int | str | tuple[int | str, ...] | None
```

</td>
<td align="left"><code>value = None</code></td>
<td align="left">identifies this component as the same one</td>
</tr>

<tr>
<td align="left"><code>preserved_by_key</code></td>
<td align="left" style="width: 25%;">

```python
list[str] | str | None
```

</td>
<td align="left"><code>value = "value"</code></td>
<td align="left">constructor parameters kept</td>
</tr>
</tbody></table>


### Events

| name | description |
|:-----|:------------|
| `change` | Triggered when the value of the MusicMixer changes either because of user input (e.g. a user types in a textbox) OR because of a function update (e.g. an image receives a value from the output of an event trigger). See `.input()` for a listener that is only triggered by user input. |
| `input` | This listener is triggered when the user changes the value of the MusicMixer. |



### User function

The impact on the users predict function varies depending on whether the component is used as an input or output for an event (or both).

- When used as an Input, the component only impacts the input signature of the user function.
- When used as an output, the component only impacts the return signature of the user function.

The code snippet below is accurate in cases where the component is used as both an input and an output.

- **As output:** Is passed, the same dict, unchanged. A handler reading.
- **As input:** Should return, a dict built by mixer_data() - layers and.

 ```python
 def predict(
     value: dict| None
 ) -> dict| None:
     return value
 ```
 
