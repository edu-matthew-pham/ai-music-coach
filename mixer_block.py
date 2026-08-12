# mixer_block.py

"""
A mixer that moves while the music is playing.

Everywhere else in this app, playback is a finished
recording: the parts are scaled, added together, and sent
as one sound. That is what a recording is, and it is
right for one - but it means a level cannot move without
the whole thing being made again from the start, which is
the wrong shape for working out how a piece goes. The ear
test is nudge, listen, nudge again, and a rebuild between
each nudge breaks the listening.

So the parts are sent apart and mixed in the browser. Each
one gets its own volume control, they play in step, and
moving a fader is heard at once because nothing is being
rebuilt - only a number is changing on a sound already
sounding.

What this is not: a second way of making the music. The
layers come from separate_layers, the same ones a
recording is made of, so the mixer and the recording
cannot drift apart.

The block is HTML plus JavaScript registered through
Gradio's js_on_load hook. Gradio renders the markup into
the page, and from there the browser's own audio engine
does the work. That is worth knowing when reading this
file: the Python here supplies JavaScript, and the usual
guarantees stop at the edge - browser audio behaviour
shows up in the browser console rather than a pytest
report.
"""

import html
import json

from music import LAYER_NAMES, separate_layers

# These used to be defined here and were borrowed by
# mixer_data.py. Now the other way round: mixer_data.py is
# the module still standing once this file is deleted (the
# gr.HTML mixer is being replaced by the MusicMixer
# component), so it owns them and this file borrows them
# back for as long as it still exists.
from mixer_data import as_wav_data, OPENING_LEVELS, LAYER_COLOURS, _timeline


def mixer_html(
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
    The mixer, built for the music in the boxes.

    Read at the moment the button is pressed, like every
    other handler: the block that comes back is a picture
    of the boxes as they were then, and pressing again
    after an edit builds a new one.
    """

    sample_rate, parts = separate_layers(
        pitch_text,
        duration_text,
        key,
        bpm,
        chart_text,
        harmony_style,
        lyric_text,
        phrase_label
    )

    layers = []

    for name in LAYER_NAMES:

        track = parts.get(name)

        if track is None:
            # Bass and chords need a chart. Absent rather
            # than silent, and the block says so instead of
            # offering a fader that does nothing.
            continue

        layers.append({
            "name": name,
            "level": OPENING_LEVELS.get(name, 0.0),
            "colour": LAYER_COLOURS.get(name, "#37474f"),
            "wav": as_wav_data(track, sample_rate)
        })

    missing = [
        name for name in ("Bass", "Chords")
        if name not in parts
    ]

    seconds = len(parts["Melody"]) / sample_rate

    timeline = _timeline(
        pitch_text, duration_text, key, bpm, chart_text,
        lyric_text, phrase_label
    )

    return _page(layers, missing, seconds, timeline)


# JavaScript for the live mixer.  gr.HTML executes this through
# js_on_load rather than through a <script> tag in its value.
# The watch is important: Build the mixer replaces the component
# value, so the new controls need wiring after each rebuild.
MIXER_JS = r"""
function initialiseMixer() {
  requestAnimationFrame(() => {

  const root = element.querySelector("#mixer");
  if (!root || root.dataset.ready) return;
  root.dataset.ready = "1";

  const layers = JSON.parse(root.dataset.layers || "[]");
  const timeline = JSON.parse(root.dataset.timeline || "[]");

  let context = null;
  const gains = {};
  const buffers = {};
  let sources = [];
  let startedAt = 0;
  let ticker = null;

  function bytes(base64) {
    const binary = atob(base64);
    const out = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      out[i] = binary.charCodeAt(i);
    }
    return out.buffer;
  }

  async function ready() {
    if (context) return;
    context = new (window.AudioContext || window.webkitAudioContext)();

    // The browser sums every live layer after its fader. Unlike the
    // rendered playback, that sum has no Python-side keep_in_range()
    // step, so several loud parts can clip at the destination. Give
    // the live mix some headroom and catch peaks before the speakers.
    const master = context.createGain();
    master.gain.value = 0.7;

    const limiter = context.createDynamicsCompressor();
    limiter.threshold.value = -6;
    limiter.knee.value = 0;
    limiter.ratio.value = 20;
    limiter.attack.value = 0.003;
    limiter.release.value = 0.15;

    master.connect(limiter);
    limiter.connect(context.destination);

    for (const layer of layers) {
      const gain = context.createGain();
      gain.gain.value = layer.level;
      gain.connect(master);
      gains[layer.name] = gain;
      buffers[layer.name] = await context.decodeAudioData(bytes(layer.wav));
    }
  }

  function stop() {
    for (const source of sources) {
      try { source.stop(); } catch (e) {}
    }
    sources = [];
    if (ticker) { clearInterval(ticker); ticker = null; }
  }

  let loopFrom = null;
  let loopTo = null;

  function playingAt() {
    if (!context || !sources.length) return offset;
    let at = offset + (context.currentTime - startedAt);
    if (loopFrom !== null && loopTo !== null && at > loopTo) {
      // Inside a loop the sound wraps, so the readout has
      // to wrap with it or it counts past the end of a
      // stretch that never gets there.
      const span = loopTo - loopFrom;
      at = loopFrom + ((at - loopFrom) % span);
    }
    return at;
  }

  async function play(from) {
    await ready();
    if (context.state === "suspended") await context.resume();
    stop();

    const whole = root.querySelector("#" + "mixer-loop").checked;

    offset = (from === undefined || from === null)
      ? (loopFrom !== null ? loopFrom : 0)
      : from;

    startedAt = context.currentTime;

    for (const layer of layers) {
      const source = context.createBufferSource();
      source.buffer = buffers[layer.name];

      if (loopFrom !== null && loopTo !== null) {
        // A stretch chosen on the strip: the browser wraps
        // it exactly, which is what makes going round a
        // hard bar worth doing.
        source.loop = true;
        source.loopStart = loopFrom;
        source.loopEnd = loopTo;
      } else {
        source.loop = whole;
      }

      source.connect(gains[layer.name]);
      source.start(startedAt, offset);
      sources.push(source);
    }

    const readout = root.querySelector("#" + "mixer-time");

    ticker = setInterval(function () {
      const at = playingAt();
      readout.textContent = at.toFixed(1) + "s";
      follow(at);
    }, 80);
  }

  function follow(at) {
    let current = null;
    for (const bar of bars) {
      const on = at >= bar.start && at < bar.end;
      if (on) current = bar;
      if (on !== bar.element.classList.contains("playing")) {
        bar.element.classList.toggle("playing", on);
      }
    }
    if (current && current !== lastSeen) {
      lastSeen = current;
      current.element.scrollIntoView({
        behavior: "smooth", inline: "center", block: "nearest"
      });
    }
  }

  function markLoop() {
    const note = root.querySelector("#" + "mixer-loop-note");
    for (const bar of bars) {
      const inside = loopFrom !== null && loopTo !== null
        && bar.start >= loopFrom - 0.001 && bar.end <= loopTo + 0.001;
      bar.element.classList.toggle("looped", inside);
    }
    if (loopFrom !== null && loopTo !== null) {
      note.textContent = "Looping "
        + loopFrom.toFixed(1) + "s to " + loopTo.toFixed(1)
        + "s. Click a bar to jump, shift-click another to "
        + "change the stretch, or Clear loop.";
    } else if (loopFrom !== null) {
      note.textContent = "Loop starts at " + loopFrom.toFixed(1)
        + "s. Shift-click a later bar to close the stretch.";
    } else {
      note.textContent = timeline.length
        ? "Click a bar to jump there. Shift-click two bars "
          + "to go round that stretch."
        : "";
    }
  }

  const bars = [];
  let lastSeen = null;
  let offset = 0;

  const strip = root.querySelector("#" + "mixer-strip");

  for (const entry of timeline) {
    const box = document.createElement("div");
    box.className = "mixer-bar";
    box.innerHTML =
      '<div class="number">' + entry.bar + '</div>'
      + '<div class="chord"></div>'
      + '<div class="words"></div>';
    box.querySelector(".chord").textContent = entry.name;
    box.querySelector(".words").textContent = entry.words || "";

    box.addEventListener("click", function (event) {
      if (event.shiftKey && loopFrom !== null) {
        loopTo = Math.max(entry.end, loopFrom + 0.05);
      } else {
        loopFrom = entry.start;
        loopTo = null;
      }
      markLoop();
      play(loopFrom);
    });

    strip.appendChild(box);
    bars.push({
      start: entry.start, end: entry.end, element: box
    });
  }

  markLoop();

  const holder = root.querySelector("#" + "mixer-faders");

  for (const layer of layers) {
    const row = document.createElement("div");
    row.className = "mixer-row";

    const name = document.createElement("span");
    name.className = "mixer-name";
    name.textContent = layer.name;
    name.style.color = layer.colour;

    const slider = document.createElement("input");
    slider.type = "range";
    slider.min = 0;
    slider.max = 1;
    slider.step = 0.05;
    slider.value = layer.level;

    const value = document.createElement("span");
    value.className = "mixer-value";
    value.textContent = Math.round(layer.level * 100) + "%";

    const mute = document.createElement("button");
    mute.className = "mixer-mute";
    mute.textContent = "M";
    let held = null;

    slider.addEventListener("input", function () {
      const level = parseFloat(slider.value);
      value.textContent = Math.round(level * 100) + "%";
      if (gains[layer.name]) {
        // A short ramp rather than a jump: changing a gain
        // instantly clicks, which sounds like a fault.
        gains[layer.name].gain.setTargetAtTime(
          level, context.currentTime, 0.01
        );
      }
      held = null;
    });

    mute.addEventListener("click", function () {
      if (!gains[layer.name]) return;
      if (held === null) {
        held = parseFloat(slider.value);
        slider.value = 0;
      } else {
        slider.value = held;
        held = null;
      }
      slider.dispatchEvent(new Event("input"));
    });

    row.appendChild(name);
    row.appendChild(mute);
    row.appendChild(slider);
    row.appendChild(value);
    holder.appendChild(row);
  }

  root.querySelector("#" + "mixer-play").addEventListener(
    "click", function () { play(); }
  );

  root.querySelector("#" + "mixer-clear").addEventListener(
    "click", function () {
      loopFrom = null;
      loopTo = null;
      markLoop();
      stop();
    }
  );
  root.querySelector("#" + "mixer-stop").addEventListener("click", stop);

  });
}

initialiseMixer();
watch("value", initialiseMixer);
"""

def _page(layers, missing, seconds, timeline=None):
    """
    The HTML and the script that runs it.
    """

    data = html.escape(json.dumps(layers), quote=True)
    strip = html.escape(json.dumps(timeline or []), quote=True)

    note = ""

    if missing:
        note = (
            f'<p class="mixer-note">No chord chart, so '
            f'{" and ".join(name.lower() for name in missing)} '
            f'are not here to mix. Write one in the Chords '
            f'box.</p>'
        )

    return f"""
<div id="mixer" data-layers="{data}" data-timeline="{strip}">
  <style>
    #mixer {{ font-family: sans-serif; }}
    #mixer .mixer-row {{
        display: flex; align-items: center; gap: 12px;
        margin: 6px 0;
    }}
    #mixer .mixer-name {{
        width: 120px; font-size: 13px; font-weight: 600;
    }}
    #mixer input[type=range] {{ flex: 1; max-width: 320px; }}
    #mixer .mixer-value {{
        width: 38px; font-size: 12px; color: #555;
        text-align: right;
    }}
    #mixer button {{
        padding: 6px 14px; font-size: 13px; font-weight: 600;
        margin-right: 8px; cursor: pointer;
    }}
    #mixer .mixer-note {{ font-size: 13px; color: #555; }}
    #mixer .mixer-mute {{
        width: 30px; padding: 4px 0; font-weight: 400;
    }}
    #mixer #mixer-strip {{
        display: flex; gap: 4px; overflow-x: auto;
        padding: 8px 2px; margin: 6px 0;
    }}
    #mixer .mixer-bar {{
        min-width: 84px; border: 1px solid #cfd8dc;
        border-radius: 4px; padding: 6px 8px; cursor: pointer;
        background: #fff; flex: 0 0 auto;
    }}
    #mixer .mixer-bar.playing {{
        border-color: #2e7d32; background: #e8f5e9;
    }}
    #mixer .mixer-bar.looped {{ background: #fff3e0; }}
    #mixer .mixer-bar .chord {{
        font-weight: 700; font-size: 14px;
    }}
    #mixer .mixer-bar .words {{
        font-size: 11px; color: #555; margin-top: 2px;
        white-space: nowrap; overflow: hidden;
        text-overflow: ellipsis; max-width: 140px;
    }}
    #mixer .mixer-bar .number {{
        font-size: 10px; color: #90a4ae;
    }}
  </style>

  <div class="mixer-row">
    <button id="mixer-play">Play</button>
    <button id="mixer-stop">Stop</button>
    <label style="font-size:13px">
      <input type="checkbox" id="mixer-loop" checked> Loop
    </label>
    <button id="mixer-clear">Clear loop</button>
    <span class="mixer-value" id="mixer-time">0.0s</span>
  </div>

  <div id="mixer-strip"></div>
  <p class="mixer-note" id="mixer-loop-note"></p>

  <div id="mixer-faders"></div>
  {note}
  <p class="mixer-note">
    Moving a fader is heard at once: the parts are playing
    separately and only their levels change.
    {seconds:.1f} seconds.
  </p>
</div>


"""