# mixer_data.py

"""
The data half of the mixer, feeding the real MusicMixer
component.

separate_layers and the timeline logic already exist and
are already tested - moving from an HTML block to a real
component changed delivery, not synthesis. This module is
the seam: it assembles the dictionary the MusicMixer
component's value expects.

as_wav_data, the timeline builder, and the opening levels
and colours used to live in mixer_block.py, the old gr.HTML
mixer. That file is gone now (main.py talks to the real
component directly); this is where they live.
"""

import base64
import io

import numpy as np
from scipy.io import wavfile

from music import LAYER_NAMES, separate_layers
from harmony import MAJOR_SCALES
from instrument_diagrams import (
    INSTRUMENTS, chord_overlay_for, scale_overlay_for, shape_overlay_for,
    structure_for
)


# Levels a part starts at, matching what the sliders used
# to default to: the tune audible, a click under it, the
# rest waiting to be brought in.
OPENING_LEVELS = {
    "Melody": 1.0,
    "Harmony above": 0.0,
    "Harmony below": 0.0,
    "Bass": 0.0,
    "Chords": 0.0,
    "Metronome": 0.5
}

# The colours the app already uses for these voices, so a
# fader and the part it moves are recognisably the same
# thing on the picture.
LAYER_COLOURS = {
    "Melody": "#2e7d32",
    "Harmony above": "#e65100",
    "Harmony below": "#6a1b9a",
    "Bass": "#00695c",
    "Chords": "#37474f",
    "Metronome": "#90a4ae"
}


def as_wav_data(track, sample_rate):
    """
    One layer as a sound file the browser can decode.

    Sent as data inside the page rather than as a file to
    fetch, because a fetch needs a route and a route needs
    the parts to outlive the request that made them. The
    cost is size, and the size is the reason a phrase is a
    better thing to mix than a whole song.
    """

    samples = np.asarray(track, dtype=np.float32)

    # Sixteen bit, which every browser decodes, and a
    # quarter of the size of float.
    peak = float(np.max(np.abs(samples))) if len(samples) else 0.0

    if peak > 1.0:
        samples = samples / peak

    encoded = (samples * 32767).astype(np.int16)

    buffer = io.BytesIO()

    wavfile.write(buffer, sample_rate, encoded)

    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _timeline(pitch_text, duration_text, key, bpm, chart_text,
              lyric_text, phrase_label):
    """
    The bars of the chart, in seconds.

    So the mixer can follow the music rather than only play
    it: which chord is sounding now, where to jump to, and
    which stretch to go round again.

    One entry per real bar, always - not one per chord run.
    A chord spanning several bars used to swallow them (one
    box claiming to be "bar 1", nothing shown for the bars
    after); a bar with more than one chord change used to
    split into several boxes each claiming to be its own
    bar. Both are the same mistake: a box was a chord run,
    not a bar. Now every bar gets a box, whether or not
    anything is sung in it - an instrumental intro is
    present and numbered like any other bar - and a bar's
    own chord changes (including a half-beat split written
    "A>B") sit inside that one box, each carrying its
    position within the bar rather than the song.

    Beats are turned into seconds here because the browser
    should not have to know what a beat is. It knows where
    it is in a sound file, and this says what is happening
    at that moment.
    """

    from music import selected_piece
    from chords import read_chart

    piece = selected_piece(
        pitch_text, duration_text, lyric_text, key,
        chart_text, phrase_label
    )

    if not piece.chart or not piece.chart.strip():
        return []

    chords, bars = read_chart(piece.chart)

    if not bars:
        return []

    per_beat = 60.0 / float(bpm)

    # The words under each bar, so the strip reads as the
    # song rather than as a row of chord names. Matched by
    # when they are sung, which is what the picture does.
    words_at = []

    position = 0.0
    tokens = iter(piece.lyrics.split() if piece.lyrics else [])

    for pitch, length in zip(piece.pitches, piece.durations):

        if pitch != "R":

            try:
                words_at.append((position, next(tokens)))

            except StopIteration:
                pass

        position += float(length)

    strip = []

    for number, (bar_start, bar_length) in enumerate(bars):

        bar_end = bar_start + bar_length

        bar_chords = []

        for chord_start, chord_length, name in chords:

            chord_end = chord_start + chord_length

            # No overlap with this bar at all.
            if chord_end <= bar_start or chord_start >= bar_end:
                continue

            # A chord already sounding when the bar opens
            # sits at the bar's own beat 0, however far
            # back it actually started - the same rule
            # invariant 2's slicing already follows. One
            # this way, at most, per bar: a genuinely new
            # start clamps to where it really begins.
            beat_in_bar = max(chord_start, bar_start) - bar_start

            bar_chords.append({
                "name": name,
                "beat_in_bar": beat_in_bar,
                "carried": chord_start < bar_start
            })

        words = " ".join(
            word for beat, word in words_at
            if bar_start <= beat < bar_end
        )

        strip.append({
            "bar": number + 1,
            "start": bar_start * per_beat,
            "end": bar_end * per_beat,
            "beats": bar_length,
            "chords": bar_chords,
            "words": words,
            "key": piece.key_at(bar_start)
        })

    return strip


def _diagrams(key, timeline):
    """
    The instrument pictures the mixer's diagram panel
    stacks, three layers per instrument, plus one alternate
    to the chord layer:

    - structure: the instrument itself (keys, frets,
      strings), key-independent, always sent - it is not a
      toggleable layer, since a picture of marks with no
      instrument under them is illegible.
    - scale: the notes of every distinct key this piece
      actually uses, transparent, for the Scale toggle - one
      entry per key name (most pieces use only one, so this
      is a one-entry dict in the ordinary case), since a
      modulating piece's Scale layer has to show the right
      key's notes on both sides of the change, not the
      opening key for the whole song.
    - chords: one transparent overlay per distinct chord
      this song's chart actually uses, for the "Chord
      notes" toggle - every place the chord's tones occur.
    - shapes: one transparent overlay per distinct chord,
      for the "Chord shape" toggle - one concrete beginner
      voicing instead of every occurrence. Missing for a
      chord this instrument has no standard shape for
      (violin has none at all; guitar only covers major,
      minor, dominant, and minor-seventh) - the panel falls
      back to the chords entry for that one card rather
      than showing nothing.

    Every instrument is included regardless of which the
    player has toggled on - the toggle is a display choice
    the browser makes with data it already has, the same
    way the Notes and Lyrics panels already work. Asking
    Python to rebuild the mixer value every time a toggle
    changes would make the toggle a round trip instead of
    a CSS switch.

    A chord name the chart uses but the theory module
    cannot read (a typo that slipped past chart validation
    elsewhere) is skipped rather than sent broken - the
    strip still shows the name; only its picture is
    missing, which is visible and correctable rather than
    a page that fails to render.
    """

    if not key:
        return {}

    from harmony import read_key, KeyError_
    from chords import ChartError

    try:
        key_changes = read_key(key)

    except KeyError_:
        return {}

    opening_key = key_changes[0][1]

    if opening_key not in MAJOR_SCALES:
        return {}

    structure = {
        instrument: structure_for(instrument)
        for instrument in INSTRUMENTS
    }

    # One Scale overlay per distinct key the piece actually
    # uses, not just the opening one - a modulating piece's
    # Scale layer would otherwise show the wrong key's notes
    # for every bar after the change (or, before this fix,
    # the whole panel would go blank: the guard above used to
    # reject the box's own multi-key text outright, since it
    # is not itself a single valid key name). Every bar in
    # the timeline carries its own key (Piece.key_at, the
    # same lookup transpose and harmony already use), so the
    # frontend picks the right entry at the playhead.
    distinct_keys = sorted({name for _, name in key_changes})

    scale = {
        key_name: {
            instrument: scale_overlay_for(key_name, instrument)
            for instrument in INSTRUMENTS
        }
        for key_name in distinct_keys
    }

    chord_names = sorted({
        chord["name"]
        for bar in timeline
        for chord in bar["chords"]
    })

    chords = {instrument: {} for instrument in INSTRUMENTS}
    shapes = {instrument: {} for instrument in INSTRUMENTS}

    for chord_name in chord_names:
        for instrument in INSTRUMENTS:

            try:

                # Spelled in the piece's opening key. The
                # marks themselves never move with the key -
                # checked directly: chord_overlay_for("G", ...)
                # and chord_overlay_for("Ab", ...) for the
                # same chord differ only in their text labels,
                # never in a mark's position - and a single
                # chord name can occur in more than one key's
                # section of a modulating piece, so there is
                # no one key that is straightforwardly
                # "correct" to spell it in. Left as a smaller,
                # cosmetic known gap rather than solved here.
                chords[instrument][chord_name] = chord_overlay_for(
                    opening_key, instrument, chord_name
                )

                shape = shape_overlay_for(
                    opening_key, instrument, chord_name
                )

                if shape is not None:
                    shapes[instrument][chord_name] = shape

            except ChartError:
                continue

    return {
        "structure": structure,
        "scale": scale,
        "chords": chords,
        "shapes": shapes,
    }


def _note_timeline(pitch_text, duration_text, key, bpm, chart_text,
                    harmony_style, lyric_text, phrase_label):
    """
    Every note, in seconds, pitch-placed and layer-tagged.

    Same shape as _timeline(), one level finer: a box per
    note instead of per bar, for the mixer's note view. The
    layers are read the same way separate_layers builds the
    audio for them, so the picture and the sound can never
    disagree about what the harmony or bass actually is.

    Melody carries the words underneath it, same as
    tuning_plot.py draws them. The generated harmony and
    bass lines never have their own lyrics - they are not
    independent sung parts, they are voices derived from
    the melody. A second, independently sung melody line
    (a duet, say) would be a different feature - another
    imported voice with its own words - not something this
    reads from what is here.
    """

    from music import selected_piece, harmony_line, bass_line
    from notes import note_to_midi, is_rest

    piece = selected_piece(
        pitch_text, duration_text, lyric_text, key,
        chart_text, phrase_label
    )

    per_beat = 60.0 / float(bpm)

    def walk(pitches, durations, colour, layer, words=None):

        notes = []
        position = 0.0
        word_at = 0

        for pitch, length in zip(pitches, durations):

            length = float(length)

            if is_rest(pitch):
                position += length
                continue

            entry = {
                "start": position * per_beat,
                "length": length * per_beat,
                "midi": note_to_midi(pitch),
                "layer": layer,
                "colour": colour
            }

            if words is not None and word_at < len(words):
                entry["word"] = words[word_at]
                word_at += 1

            notes.append(entry)
            position += length

        return notes

    all_notes = []

    all_notes += walk(
        piece.pitches, piece.durations, LAYER_COLOURS["Melody"],
        "Melody", words=piece.lyrics.split() if piece.lyrics else None
    )

    for name, steps in (("Harmony above", 2), ("Harmony below", -2)):

        harmony = harmony_line(
            piece.pitches, piece.durations, key,
            steps=steps, style=harmony_style, chart_text=piece.chart
        )

        all_notes += walk(
            harmony, piece.durations, LAYER_COLOURS[name], name
        )

    if piece.chart and piece.chart.strip():

        bass = bass_line(piece.pitches, piece.durations, piece.chart)

        all_notes += walk(
            bass, piece.durations, LAYER_COLOURS["Bass"], "Bass"
        )

    return all_notes


def _phrase_timeline(pitch_text, duration_text, key, bpm, lyric_text):
    """
    Where each phrase starts and ends, in seconds, with a
    label to click on.

    A phrase is a line of the lyrics - the same unit the
    retired phrase dropdown used, read the same way, via
    Piece.phrases(), and labelled the same way it was: the
    opening words of that line, so a phrase reads as
    something a person recognises rather than a number.

    Falls back to treating the whole piece as one phrase
    when there is no more than one - matching the dropdown,
    which showed only "Whole part" in that case.
    """

    from piece import Piece
    from music import MusicInputError
    from midi_import import join_syllables

    try:
        piece = Piece.read(pitch_text, duration_text, lyric_text)

    except MusicInputError:
        return []

    found = piece.phrases()

    if len(found) <= 1:
        return []

    per_beat = 60.0 / float(bpm)

    durations = [float(length) for length in piece.durations]

    def time_at(index):
        return sum(durations[:index]) * per_beat

    lines = [
        line for line in (lyric_text or "").split("\n")
        if line.strip()
    ]

    phrases = []

    for position, (first, last) in enumerate(found):

        if position < len(lines):
            label = join_syllables(lines[position].split())

        else:
            label = " ".join(piece.pitches[first:first + 5])

        phrases.append({
            "start": time_at(first),
            "end": time_at(last + 1),
            "label": f"{position + 1}. {label}"
        })

    return phrases


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

    notes = _note_timeline(
        pitch_text, duration_text, key, bpm, chart_text,
        harmony_style, lyric_text, phrase_label
    )

    phrases = _phrase_timeline(
        pitch_text, duration_text, key, bpm, lyric_text
    )

    diagrams = _diagrams(key, timeline)

    return {
        "layers": layers,
        "timeline": timeline,
        "notes": notes,
        "phrases": phrases,
        "diagrams": diagrams,
        "bpm": float(bpm),
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


def loop_notes(pitch_text, duration_text, lyric_text, key,
               chart_text, mixer_value):
    """
    The stretch of the music a selected loop covers, as a
    Piece - or None if nothing is usably selected.

    The reverse of the walk _note_timeline does: that walk
    turns each note's beat position into seconds; this reads
    seconds back and finds which notes they cover. Uses the
    bpm the mixer was built at, carried in mixer_value,
    rather than whatever the BPM box currently says - the
    loop's seconds were fixed at build time and mean nothing
    at a tempo chosen afterwards.

    A small tolerance absorbs float rounding across the
    beats-to-seconds-and-back trip, not genuine ambiguity
    about which notes were meant - it is far smaller than
    any real note.
    """

    from piece import Piece

    region = loop_region(mixer_value)

    if region is None:
        return None

    loop_start, loop_end = region
    bpm = mixer_value.get("bpm")

    if not bpm:
        return None

    piece = Piece.read(
        pitch_text, duration_text, lyric_text, key, chart_text
    )

    per_beat = 60.0 / float(bpm)
    starts = piece.starts()

    TOLERANCE = 0.05

    first = None
    last = None

    for index, beat_start in enumerate(starts):

        seconds = beat_start * per_beat

        if loop_start - TOLERANCE <= seconds < loop_end + TOLERANCE:

            if first is None:
                first = index

            last = index

    if first is None:
        return None

    return piece.slice(first, last)