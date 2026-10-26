# melody_lanes.py

"""
The melody on the instrument: the notes of the song (or of one
phrase of it) laid out in lanes - one lane per kalimba tine,
time running down the page, the words beside each note - for
looking over before you play.

Two halves, kept apart (PLAN-melody-lanes.md, decision 2):

    melody_blocks(piece, instrument)  plain data: where each
        note goes and for how long. No drawing.
    lanes_html(...)                   the drawing, from that data.

The data is what a later live view in the mixer would draw
from too, so nothing about a block depends on how it is shown.

Plain Python, no interface, like chord_sheet.py. It is handed a
Piece (already read from the boxes) and never reads or writes
the boxes itself: the song belongs to the boxes, this only
looks at it (DESIGN.md invariant 1).
"""

import html

from instrument_diagrams import (
    KALIMBA_CENTRE_COLOUR,
    KALIMBA_LAYOUT,
    LEFT_HAND_COLOUR,
    RIGHT_HAND_COLOUR,
    _absolute_pitch,
    _base_instrument_name,
    _kalimba_has_bass,
    _kalimba_tines,
    KALIMBA_TINES,
    LEVER_HARP_LAYOUT,
    LEVER_HARP_PLAIN_STRING_COLOUR,
    LEVER_HARP_STRING_COLOURS,
    LEVER_HARP_STRINGS,
    CHORD_TONE_COLOUR,
    PIANO_LAYOUT,
    _octaves_for,
    kalimba_shape_tines,
    lever_harp_shape_strings,
    piano_shape_voicing,
    structure_for,
)
from fretted_tab import DEFAULT_WIDTH, FINGERINGS, NEAREST_NUT, row_starts
from notes import is_rest
from wind_fingerings import WINDS


# --- the lanes of each instrument ------------------------------

OUT_OF_RANGE_COLOUR = "#c62828"

# One lane is wide enough for a note's name inside its block.
LANE_WIDTH = 36

# Which side of the kalimba's centre column a lane is on tells
# the player which thumb takes it: the same colours the scale-in-
# order card uses.
_KALIMBA_CENTRE = len(KALIMBA_TINES["middle"]) // 2


def _kalimba_thumb(column):
    if column < _KALIMBA_CENTRE:
        return "left"

    if column > _KALIMBA_CENTRE:
        return "right"

    return "centre"


THUMB_COLOURS = {
    "left": LEFT_HAND_COLOUR,
    "right": RIGHT_HAND_COLOUR,
    "centre": KALIMBA_CENTRE_COLOUR,
}


def lanes_for(instrument):
    """
    The lanes of one instrument, in the order they are laid
    out left to right, as the player sees them: a list of
    {"index", "label", "sub", "colour"}. The kalimba has one
    lane per column of tines (17): the middle row's note names
    the lane and the top row's sits under it, because a column
    holds one tine of each, and on the 41-key a bass tine too.
    """

    base = _base_instrument_name(instrument)

    if base == "Kalimba":
        return [
            {
                "index": column,
                "label": KALIMBA_TINES["middle"][column],
                "sub": KALIMBA_TINES["top"][column],
                "colour": THUMB_COLOURS[_kalimba_thumb(column)]
                if column == _KALIMBA_CENTRE else "#cfd8dc",
            }
            for column in range(len(KALIMBA_TINES["middle"]))
        ]

    if base == "Lever harp":
        return [
            {
                "index": column,
                "label": note,
                "sub": "",
                "colour": LEVER_HARP_STRING_COLOURS.get(
                    note[0], LEVER_HARP_PLAIN_STRING_COLOUR
                ),
                "kind": "string",
            }
            for column, note in enumerate(LEVER_HARP_STRINGS)
        ]

    if base == "Piano":
        return [
            {
                "index": pitch,
                "label": _name(pitch) if _is_white(pitch) else "",
                "sub": "" if _is_white(pitch) else _name(pitch),
                "colour": "#ffffff" if _is_white(pitch) else "#212121",
                "kind": "white" if _is_white(pitch) else "black",
            }
            for pitch in _piano_pitches(instrument)
        ]

    raise ValueError(f"No lanes for {instrument}.")


# --- the piano's keys and the note names -------------------------

_SHARP_NAMES = [
    "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"
]

# The keyboard's first key. Matthew, 2026-10-25: C3, so that
# middle C (C4) is the first C of the second octave and the
# right hand's shape sits level with the melody.
PIANO_START = 3 * 12


def _is_white(pitch):
    return len(_SHARP_NAMES[pitch % 12]) == 1


def _name(pitch):
    """A pitch as a name with its octave: 48 -> C3."""

    return f"{_SHARP_NAMES[pitch % 12]}{pitch // 12}"


def _piano_pitches(instrument):
    octaves = _octaves_for(instrument)

    return list(range(PIANO_START, PIANO_START + 12 * octaves))


def _kalimba_column(tine):
    return round(
        (tine["x"] - KALIMBA_LAYOUT["left"]) / KALIMBA_LAYOUT["column_width"]
    )


def _place_kalimba(pitch, instrument):
    """
    Where a pitch is played on the kalimba: (lane, row), or
    (None, None) when no tine has it. A note with a tine on
    both rows (F4, C5, F5, C6) uses the middle row, as the chord
    shapes and the scale-in-order card do; a sharp or flat is on
    the top row; on the 41-key the notes below C4 are the bass
    row, in the column they sit under.
    """

    tines = [
        tine for tine in _kalimba_tines(_kalimba_has_bass(instrument))
        if tine["pitch"] == pitch
    ]

    for row in ("middle", "top", "bass"):
        for tine in tines:
            if tine["row"] == row:
                return _kalimba_column(tine), row

    return None, None


def _place_harp(pitch):
    """
    Where a pitch is played on the lever harp: (string, lever).
    A natural note is its own string with the lever down; a
    sharp or flat is the string below with its lever up. None
    when the harp has no string for it.
    """

    for column, note in enumerate(LEVER_HARP_STRINGS):
        if _absolute_pitch(note) == pitch:
            return column, False

    for column, note in enumerate(LEVER_HARP_STRINGS):
        if _absolute_pitch(note) + 1 == pitch:
            return column, True

    return None


def _place(pitch, instrument):
    """
    Where a pitch is played: (lane, row, lever), with lane None
    when the instrument has no way to sound it. row is the
    kalimba's row, lever is the harp's raised lever, both None
    elsewhere.
    """

    base = _base_instrument_name(instrument)

    if base == "Kalimba":
        lane, row = _place_kalimba(pitch, instrument)
        return lane, row, None

    if base == "Lever harp":
        found = _place_harp(pitch)

        if found is None:
            return None, None, None

        return found[0], None, found[1]

    if base == "Piano":
        if pitch in _piano_pitches(instrument):
            return pitch, None, None

        return None, None, None

    raise ValueError(f"No lanes for {instrument}.")


def instrument_range(instrument):
    """
    (lowest, highest) pitch the instrument can sound, each as
    {"pitch", "note"} with the note's name and octave.
    """

    base = _base_instrument_name(instrument)

    if base == "Kalimba":
        tines = _kalimba_tines(_kalimba_has_bass(instrument))
        low = min(tines, key=lambda tine: tine["pitch"])
        high = max(tines, key=lambda tine: tine["pitch"])

        return low, high

    if base == "Lever harp":
        # The top string's lever sounds one higher still.
        low = _absolute_pitch(LEVER_HARP_STRINGS[0])
        high = _absolute_pitch(LEVER_HARP_STRINGS[-1]) + 1

        return (
            {"pitch": low, "note": LEVER_HARP_STRINGS[0]},
            {"pitch": high, "note": _name(high)},
        )

    if base == "Piano":
        pitches = _piano_pitches(instrument)

        return (
            {"pitch": pitches[0], "note": _name(pitches[0])},
            {"pitch": pitches[-1], "note": _name(pitches[-1])},
        )

    raise ValueError(f"No range for {instrument}.")


# What one lane is called, for the line about notes off the
# instrument.
_PART_WORD = {"Kalimba": "tine", "Lever harp": "string", "Piano": "key"}


# --- the data ---------------------------------------------------

def _lyrics_per_note(piece):
    """One syllable (or None) for every note of the piece."""

    from music import read_lyrics

    # No words at all reads as no syllables, not an error.
    sung = read_lyrics(piece.lyrics or "", piece.sung()) or []

    syllables = iter(sung)
    out = []

    for pitch in piece.pitches:
        if is_rest(pitch):
            out.append(None)
            continue

        syllable = next(syllables, None)
        out.append(None if syllable in (None, "", "_") else syllable)

    return out


def melody_blocks(piece, instrument):
    """
    Every sounding note of the piece as one block:

        {"lane", "start", "length", "note", "pitch", "lyric",
         "thumb", "row", "lever", "black", "in_range", "where",
         "written_pitch", "shift"}

    start and length are in beats from the start of the piece
    handed in (a phrase's own start, when it was sliced). lane
    is the lane's index (None when the instrument has no tine
    for the note), thumb is "left", "right" or "centre", row is
    "middle", "top" or "bass" (kalimba only), lever is True
    where a harp string needs its lever up for the note (None
    off the harp), black marks a piano's black key, and where is "below" or "above"
    for a note the instrument cannot sound as written. Such a note
    is moved to the nearest octave that fits: pitch is where it is
    played, written_pitch what the boxes say, and shift how many
    octaves it was moved (+1 up, -1 down, 0 not moved). Only a note
    with no octave that fits keeps in_range False. note is the name
    as written in the boxes, without its octave. Rests leave a gap
    and are not blocks.
    """

    base = _base_instrument_name(instrument)

    if base not in _PART_WORD:
        raise ValueError(f"No lanes for {instrument}.")

    low, high = instrument_range(instrument)
    starts = piece.starts()
    lyrics = _lyrics_per_note(piece)
    blocks = []

    for index, written in enumerate(piece.pitches):

        if is_rest(written):
            continue

        written_pitch = _absolute_pitch(written)
        pitch = written_pitch
        lane, row, lever = _place(pitch, instrument)
        where = None
        shift = 0

        # A note the instrument cannot sound goes to the nearest
        # octave that it can (up from below, down from above), and
        # is flagged. Only a note with no octave that fits at all
        # stays off, in the red strip.
        if lane is None:
            where = "below" if pitch < low["pitch"] else "above"
            step = 12 if where == "below" else -12

            for octaves in range(1, 9):
                found = _place(written_pitch + step * octaves, instrument)

                if found[0] is not None:
                    shift = octaves if step > 0 else -octaves
                    pitch = written_pitch + step * octaves
                    lane, row, lever = found
                    break

        in_range = lane is not None

        blocks.append({
            "lane": lane,
            "start": starts[index],
            "length": piece.durations[index],
            "note": written[:-1],
            "pitch": pitch,
            "written_pitch": written_pitch,
            "shift": shift,
            "lyric": lyrics[index],
            "thumb": (
                _kalimba_thumb(lane)
                if in_range and base == "Kalimba" else None
            ),
            "row": row,
            "lever": lever,
            "black": (
                base == "Piano" and in_range and not _is_white(pitch)
            ),
            "in_range": in_range,
            "where": where,
        })

    return blocks


def _shift_title(block):
    """Hover text for a note moved to another octave."""

    octaves = abs(block["shift"])
    way = "higher" if block["shift"] > 0 else "lower"
    written = _name(block["written_pitch"])
    played = _name(block["pitch"])
    amount = "an octave" if octaves == 1 else f"{octaves} octaves"

    return (
        f"written {written}, which this instrument cannot play - "
        f"shown {amount} {way} on {played}"
    )


def range_message(blocks, instrument):
    """
    In words, how many notes the instrument cannot sound as
    written, where they were drawn, and what would fix it. ""
    when every note is on it as written.
    """

    below = sum(1 for block in blocks if block["where"] == "below")
    above = sum(1 for block in blocks if block["where"] == "above")

    if not below and not above:
        return ""

    low, high = instrument_range(instrument)
    word = _PART_WORD[_base_instrument_name(instrument)]
    parts = []

    if below:
        parts.append(
            f"{below} {'note is' if below == 1 else 'notes are'} "
            f"below the lowest {word} ({low['note']})"
        )

    if above:
        parts.append(
            f"{above} {'note is' if above == 1 else 'notes are'} "
            f"above the highest ({high['note']})"
        )

    stranded = sum(1 for block in blocks if not block["in_range"])
    moved = sum(1 for block in blocks if block["shift"])

    if moved and stranded:
        shown = (
            f"{moved} are shown an octave or more away (amber 8va "
            f"pill) and {stranded} fit nowhere, in the red strip "
            f"at the left"
        )
    elif stranded:
        shown = "they fit nowhere and are in the red strip at the left"
    elif moved == 1:
        shown = "it is shown an octave or more away (amber 8va pill)"
    else:
        shown = (
            "they are shown an octave or more away (amber 8va pill)"
        )

    def fits_after(shift):
        return all(
            _place(block["written_pitch"] + shift, instrument)[0]
            is not None
            for block in blocks
        )

    if fits_after(12):
        fix = "Octave up in the Song section would bring every note on."
    elif fits_after(-12):
        fix = "Octave down in the Song section would bring every note on."
    else:
        fix = (
            "No single octave shift brings every note on - the "
            "song is wider than this instrument."
        )

    return " and ".join(parts) + f"; {shown}. " + fix


# --- the chords --------------------------------------------------

# Where the chord layer goes: near the notes being played (so the
# hands do not have to jump), or where the chord sheet's shape
# puts it. Matthew, 2026-10-25: a toggle; near the melody first.
NEAR_MELODY = "Near the melody"
AS_IN_SHEET = "As in the chord sheet"
PLACEMENTS = [NEAR_MELODY, AS_IN_SHEET]

SHOW_MELODY = "Melody"
SHOW_CHORDS = "Chords"
SHOW_CHOICES = [SHOW_MELODY, SHOW_CHORDS]
DEFAULT_SHOW = [SHOW_MELODY, SHOW_CHORDS]

HEADER_COMPACT = "Compact"
HEADER_LABELS = "Plain labels"
HEADER_SHORT = "Short picture"
HEADER_PICTURE = "Full picture"
# The short picture first (Matthew, 2026-10-26): the instrument
# over its lanes, cropped to its upper part. The full picture is
# tall (kalimba 340px, harp 400px); plain labels are the smallest.
HEADERS = [HEADER_COMPACT, HEADER_SHORT, HEADER_PICTURE, HEADER_LABELS]


def chord_spans(piece):
    """
    The chords of the piece's chart as [{"start", "length",
    "name"}], in beats from the start of the piece handed in, cut
    off at its end. [] when there is no chart or it cannot be
    read (a half-typed chart is not an error here).
    """

    from chords import read_chart

    try:
        chords, _bars = read_chart(piece.chart or "")
    except ValueError:
        return []

    total = piece.beats()

    return [
        {
            "start": start,
            "length": min(length, total - start),
            "name": name,
        }
        for start, length, name in chords
        if start < total
    ]


def _melody_centre(blocks, start, length, instrument):
    """
    The middle of the notes being played from start for length
    beats (their average pitch); failing that, the middle of
    every note of the tune; failing that, the instrument's own
    middle. Notes off the instrument do not count.
    """

    def middle(chosen):
        return sum(b["pitch"] for b in chosen) / len(chosen)

    sounding = [b for b in blocks if b["in_range"]]
    during = [
        b for b in sounding
        if b["start"] < start + length and b["start"] + b["length"] > start
    ]

    if during:
        return middle(during)

    if sounding:
        return middle(sounding)

    low, high = instrument_range(instrument)

    return (low["pitch"] + high["pitch"]) / 2


def _near_pitches(tones, centre, instrument):
    """
    One pitch for each chord tone (a pitch class), the one
    closest to the melody's middle, moved by an octave at a time
    onto the instrument if that is where it is not. [] if a tone
    has no place on the instrument at all.
    """

    pitches = []

    for tone in tones:
        # The pitch of this class within six semitones of centre.
        base = round(centre) - 6
        pitch = base + (tone - base) % 12

        for _ in range(8):
            if _place(pitch, instrument)[0] is not None:
                break

            low, _high = instrument_range(instrument)
            pitch += 12 if pitch < low["pitch"] else -12
        else:
            continue

        pitches.append(pitch)

    return pitches


def _sheet_pitches(name, instrument):
    """
    The pitches of the chord sheet's own shape for a chord on
    this instrument, or None where the sheet has no shape for it.
    """

    from chords import split_chord

    root, quality = split_chord(name)
    base = _base_instrument_name(instrument)

    if base == "Kalimba":
        tines = kalimba_shape_tines(
            root, quality, _kalimba_has_bass(instrument)
        )

        return None if tines is None else [t["pitch"] for t in tines]

    if base == "Lever harp":
        strings = lever_harp_shape_strings(root, quality)

        return None if strings is None else [s["sounding"] for s in strings]

    if base == "Piano":
        voicing = piano_shape_voicing(root, quality, _octaves_for(instrument))

        if voicing is None:
            return None

        return [
            PIANO_START + key for hand in voicing for key, _finger in hand
        ]

    return None


def chord_blocks(piece, instrument, melody, placement=NEAR_MELODY):
    """
    The chord layer as one block per chord tone:

        {"lane", "start", "length", "name", "pitch", "black"}

    start and length are the chord's own, in beats. `melody` is
    the melody's blocks (for "near the melody"). With
    AS_IN_SHEET each chord goes where the chord sheet's beginner
    shape puts it; a chord with no shape there goes near the
    melody instead. A chord this app does not know gives no
    blocks.
    """

    from chords import chord_semitones

    base = _base_instrument_name(instrument)
    out = []

    for span in chord_spans(piece):
        try:
            tones = chord_semitones(span["name"])
        except ValueError:
            continue

        pitches = None

        if placement == AS_IN_SHEET:
            try:
                pitches = _sheet_pitches(span["name"], instrument)
            except ValueError:
                pitches = None

        if pitches is None:
            centre = _melody_centre(
                melody, span["start"], span["length"], instrument
            )
            pitches = _near_pitches(tones, centre, instrument)

        for pitch in pitches:
            lane = _place(pitch, instrument)[0]

            if lane is None:
                continue

            out.append({
                "lane": lane,
                "start": span["start"],
                "length": span["length"],
                "name": span["name"],
                "pitch": pitch,
                "black": base == "Piano" and not _is_white(pitch),
            })

    return out


# --- the drawing -------------------------------------------------

BEAT_PX = 28
HEADER_HEIGHT = 46
TOP_PAD = 10
LEFT_MARGIN = 62
CHORD_MARGIN = 54
RIGHT_MARGIN = 150

# The kalimba's three rows, by colour (a note's row is the thing
# its position does not show): the middle row, the top row's
# sharps and flats, the bass row. The tints are the same hues
# lighter, for the tines in the header pictures. Amber is used
# for nothing else but a note moved an octave.
ROW_COLOURS = {"middle": "#1565c0", "top": "#8e24aa", "bass": "#00897b"}
ROW_TINTS = {"middle": "#90caf9", "top": "#ce93d8", "bass": "#80cbc4"}
OCTAVE_COLOUR = "#ffb300"
OCTAVE_TEXT_COLOUR = "#3e2723"

# A piano's black key is a narrower lane, sitting over the join
# between the two white lanes either side of it.
MELODY_COLOUR = "#7b1fa2"


def _lane_widths(instrument):
    """
    (lane width, black lane width) of an instrument. Each lane is
    as wide as its column of the instrument's own picture, so the
    picture can sit over the lanes and line up.
    """

    base = _base_instrument_name(instrument)

    if base == "Lever harp":
        return LEVER_HARP_LAYOUT["column_width"], 0

    if base == "Piano":
        return PIANO_LAYOUT["white_width"], PIANO_LAYOUT["black_width"]

    return KALIMBA_LAYOUT["column_width"], 0


def _lane_positions(lanes, spare, instrument, left=LEFT_MARGIN):
    """
    x of each lane (and of the out-of-range strip, if any), and
    the x the lanes end at. A piano's white lanes go side by
    side and each black lane is centred on the line after the
    white key before it.
    """

    wide, narrow = _lane_widths(instrument)
    x = left + (wide if spare else 0)
    positions = {}

    for lane in lanes:
        if lane.get("kind") == "black":
            positions[lane["index"]] = x - narrow // 2
        else:
            positions[lane["index"]] = x
            x += wide

    return positions, x


def _lane_width(lane, instrument):
    wide, narrow = _lane_widths(instrument)

    return narrow if lane.get("kind") == "black" else wide


def _picture_x(lane, instrument):
    """Where a lane's left edge falls in the instrument's picture."""

    base = _base_instrument_name(instrument)

    if base == "Lever harp":
        return (
            LEVER_HARP_LAYOUT["left"]
            + lane["index"] * LEVER_HARP_LAYOUT["column_width"]
        )

    if base == "Piano":
        white = PIANO_LAYOUT["white_width"]
        whites_before = sum(
            1 for pitch in range(PIANO_START, lane["index"])
            if _is_white(pitch)
        )

        if lane["kind"] == "black":
            return whites_before * white - PIANO_LAYOUT["black_width"] // 2

        return whites_before * white

    # A kalimba tine is 22 wide in a 36 column, 6 from the left.
    column_width = KALIMBA_LAYOUT["column_width"]

    return lane["index"] * column_width - 1


def visible_lanes(blocks, instrument, extra_pitches=()):
    """
    The lanes to draw. All of them, except on the piano, which
    is cropped to the notes the song uses with two keys spare
    either side (and out to the next white key, so no lane
    starts on a black one), so a song in a few octaves is not a
    keyboard of empty lanes. extra_pitches are notes the crop
    must also hold (the chord layer's).
    """

    lanes = lanes_for(instrument)

    if _base_instrument_name(instrument) != "Piano":
        return lanes

    used = [block["pitch"] for block in blocks if block["in_range"]]
    used += list(extra_pitches)

    if not used:
        return lanes

    low = min(used) - 2
    high = max(used) + 2

    while not _is_white(low):
        low -= 1

    while not _is_white(high):
        high += 1

    return [lane for lane in lanes if low <= lane["index"] <= high]


def _bar_lines(chart_text, total_beats):
    """
    Where the strong lines go: the chart's own bars when the
    song has a chart, else every four beats.
    """

    from chords import read_chart

    try:
        _chords, bars = read_chart(chart_text or "")
    except ValueError:
        bars = []

    starts = [start for start, _length in bars if start < total_beats]

    if starts:
        return starts

    return [float(beat) for beat in range(0, int(total_beats) + 1, 4)]


# The greys the kalimba picture draws its three rows in (see
# instrument_diagrams._kalimba_structure_parts).
KALIMBA_ROW_GREYS = {
    "bass": "#90a4ae", "middle": "#cfd8dc", "top": "#607d8b",
}

# How much of the picture's height the short version keeps.
SHORT_PICTURE_FRACTION = 0.55
SHORT_PICTURE_MINIMUM = 100


COMPACT_HEIGHT = 72


def _compact_header(lanes, positions, instrument, total_width, left,
                    spare, wide):
    """
    A slim strip over the lanes that is less a picture of the
    instrument than a set of cues: on the kalimba one bar a tine
    (the tine's length, a cap in the middle row's blue, a purple
    dot where the top row has a sharp or flat, a green bar where
    the bass row has a tine, the centre tine outlined); on the
    harp a thin string each (C red, F blue, a lever tab on those);
    on the piano the keys. Only a few lanes are named. Returns
    (svg, height).
    """

    base = _base_instrument_name(instrument)
    baseline = 46
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {total_width} {COMPACT_HEIGHT}" width="100%" '
        f'style="display:block;'
        f'background:var(--background-fill-primary,#fff)" '
        f'role="img" aria-label="The instrument, as a strip over '
        f'its lanes">'
    ]

    def name(centre, text, bold=False):
        parts.append(
            f'<text x="{centre}" y="{COMPACT_HEIGHT - 4}" '
            f'font-size="10" text-anchor="middle" '
            f'font-weight="{700 if bold else 400}" '
            f'fill="#37474f">{html.escape(text)}</text>'
        )

    if spare:
        parts.append(
            f'<rect x="{left + 2}" y="30" width="{wide - 4}" '
            f'height="12" rx="2" fill="{OUT_OF_RANGE_COLOUR}"/>'
        )
        name(left + wide / 2, "off")

    if base == "Kalimba":
        bass_lanes = set()

        if _kalimba_has_bass(instrument):
            bass_lanes = {
                _kalimba_column(tine)
                for tine in _kalimba_tines(True) if tine["row"] == "bass"
            }

        middle = len(lanes_for(instrument)) // 2

        for lane in lanes:
            index = lane["index"]
            x = positions[index]
            centre = x + _lane_width(lane, instrument) / 2
            height = max(14, 30 - abs(index - middle) * 1.5)
            top = baseline - height
            is_centre = index == middle

            parts.append(
                f'<rect class="compact-tine" x="{centre - 9}" y="{top}" '
                f'width="18" height="{height}" rx="5" '
                f'fill="{ROW_TINTS["middle"]}"'
                + (' stroke="#263238" stroke-width="1.5"'
                   if is_centre else "")
                + "/>"
                f'<rect x="{centre - 9}" y="{top}" width="18" '
                f'height="7" rx="3.5" fill="{ROW_COLOURS["middle"]}"/>'
                f'<circle class="compact-top" cx="{centre}" '
                f'cy="{top - 6}" r="3" fill="{ROW_COLOURS["top"]}"/>'
            )

            if index in bass_lanes:
                parts.append(
                    f'<rect class="compact-bass" x="{centre - 5}" '
                    f'y="{baseline + 2}" width="10" height="7" rx="3" '
                    f'fill="{ROW_COLOURS["bass"]}"/>'
                )

            if index % 4 == 0 or is_centre:
                name(centre, lane["label"], bold=is_centre)

    elif base == "Lever harp":
        for lane in lanes:
            index = lane["index"]
            x = positions[index]
            centre = x + _lane_width(lane, instrument) / 2
            height = 40 - index * 1.2
            marked = lane["colour"] in LEVER_HARP_STRING_COLOURS.values()

            parts.append(
                f'<rect class="compact-string" x="{centre - 3}" '
                f'y="{baseline - height}" width="6" height="{height}" '
                f'rx="3" fill="{lane["colour"]}"/>'
            )

            if marked:
                parts.append(
                    f'<rect x="{centre - 6}" '
                    f'y="{baseline - height - 5}" width="12" height="4" '
                    f'rx="2" fill="#eceff1" stroke="#90a4ae" '
                    f'stroke-width="0.8"/>'
                )

            if lane["label"].startswith("C"):
                name(centre, lane["label"])

    else:
        for lane in lanes:
            x = positions[lane["index"]]
            lane_width = _lane_width(lane, instrument)

            if lane["kind"] == "white":
                parts.append(
                    f'<rect class="compact-key" x="{x + 2}" y="14" '
                    f'width="{lane_width - 4}" height="30" rx="3" '
                    f'fill="#ffffff" stroke="#90a4ae"/>'
                )

                if lane["label"].startswith("C"):
                    name(x + lane_width / 2, lane["label"], bold=True)

        for lane in lanes:
            if lane["kind"] == "black":
                parts.append(
                    f'<rect class="compact-key" x="{positions[lane["index"]]}" '
                    f'y="14" width="{_lane_width(lane, instrument)}" '
                    f'height="18" rx="3" fill="#263238"/>'
                )

    parts.append("</svg>")

    return "".join(parts), COMPACT_HEIGHT


def _picture_header(lanes, positions, instrument, total_width,
                    short=False):
    """
    The instrument's own picture, cropped to the lanes shown and
    set so that each of its columns is over its lane. Returns
    (svg, height).
    """

    import re

    picture = structure_for(instrument)
    root = re.match(r"<svg[^>]*>", picture).group(0)
    height = int(re.search(r'viewBox="0 0 [\d.]+ ([\d.]+)"', root).group(1))
    inner = picture[len(root):-len("</svg>")]
    full_height = height

    # The kalimba's tines wear the rows' colours (as the notes do),
    # in tints, instead of greys. Done to this copy only; the
    # picture in the other sections is not touched.
    if _base_instrument_name(instrument) == "Kalimba":
        for row, grey in KALIMBA_ROW_GREYS.items():
            inner = inner.replace(
                f'fill="{grey}"', f'fill="{ROW_TINTS[row]}"'
            )

    if short:
        height = min(
            full_height,
            max(SHORT_PICTURE_MINIMUM, int(full_height * SHORT_PICTURE_FRACTION)),
        )

    first = min(lanes, key=lambda lane: positions[lane["index"]])
    start_x = _picture_x(first, instrument)
    shown_width = max(
        positions[lane["index"]] + _lane_width(lane, instrument)
        for lane in lanes
    ) - positions[first["index"]]

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {total_width} {height}" width="100%" '
        f'style="display:block;'
        f'background:var(--background-fill-primary,#fff)" '
        f'role="img" aria-label="The instrument, over its lanes">'
        f'<svg x="{positions[first["index"]]}" y="0" '
        f'width="{shown_width}" height="{height}" '
        f'viewBox="{start_x} 0 {shown_width} {height}">'
        f"{inner}</svg></svg>"
    )

    return svg, height


# --- columns -----------------------------------------------------

# How many strips of the song sit side by side. Auto lets the page
# decide by the width it has; One is the single tall strip; Two is
# two, whatever the width.
COLUMNS_AUTO = "Auto"
COLUMNS_ONE = "One column"
COLUMNS_TWO = "Two columns"
COLUMN_CHOICES = [COLUMNS_AUTO, COLUMNS_ONE, COLUMNS_TWO]

# A column is never drawn narrower than this share of a strip's
# natural width: below that the note names get too small to read.
AUTO_SCALE = 0.72
COLUMN_GAP = 14

# Auto never goes past this many columns, however wide the screen.
MAX_AUTO_COLUMNS = 3


def phrase_ranges(cuts, total_beats, columns=COLUMNS_AUTO):
    """
    The song as one piece per phrase, [(from_beat, to_beat), ...],
    cut at the phrase starts in cuts: the pieces the page packs into
    columns, as many whole phrases to a column as the screen has room
    for (FLOW_JS). One column, or a song of one phrase, is the whole
    song as a single piece.
    """

    if columns == COLUMNS_ONE or total_beats <= 0:
        return [(0, total_beats)]

    points = [0] + sorted({
        cut for cut in (cuts or []) if 0 < cut < total_beats
    }) + [total_beats]

    return list(zip(points, points[1:]))


def _note_slice(blocks, low, high):
    """The notes that BEGIN in [low, high), moved up to the strip."""

    if low == 0 and high >= max(
        (b["start"] + b["length"] for b in blocks), default=0
    ):
        return blocks

    kept = []

    for block in blocks:
        if low <= block["start"] < high:
            moved = dict(block)
            moved["start"] = block["start"] - low
            kept.append(moved)

    return kept


def _span_slice(items, low, high):
    """
    The chord layer's blocks and names that overlap [low, high),
    clipped to it, so a chord running over a cut is on both strips.
    """

    kept = []

    for item in items:
        begin = item["start"]
        end = begin + item["length"]

        if end <= low or begin >= high:
            continue

        moved = dict(item)
        moved["start"] = max(begin, low) - low
        moved["length"] = min(end, high) - max(begin, low)
        kept.append(moved)

    return kept


def lanes_html(blocks, instrument, total_beats, chart_text="",
               chords=None, chord_names=None, header=HEADER_LABELS,
               columns=COLUMNS_ONE, cuts=None):
    """
    The lanes picture for one instrument as HTML: a header that
    stays put (lane names, or the instrument's own picture) and
    the notes scrolling under it, time running down.
    total_beats is how long the stretch is.

    chords is the chord layer's blocks (drawn first, pale, under
    the melody) and chord_names the chord spans for the left
    margin; both None draws the melody alone.

    columns says how many strips side by side (the song is cut at
    the phrase starts in cuts); One column draws the one tall strip.
    """

    chords = chords or []
    chord_names = chord_names or []
    show_chords = bool(chords or chord_names)

    lanes = visible_lanes(
        blocks, instrument, [c["pitch"] for c in chords]
    )
    spare = any(not block["in_range"] for block in blocks)

    wide, narrow = _lane_widths(instrument)
    left = LEFT_MARGIN + (CHORD_MARGIN if show_chords else 0)
    positions, width = _lane_positions(lanes, spare, instrument, left)
    total_width = width + RIGHT_MARGIN

    # --- header: lane names ---
    labels = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {total_width} {HEADER_HEIGHT}" width="100%" '
        f'style="display:block;'
        f'background:var(--background-fill-primary,#fff)" '
        f'role="img" aria-label="The lanes: one per tine">'
    ]

    if spare:
        x = left
        labels.append(
            f'<rect x="{x + 2}" y="22" width="{wide - 4}" '
            f'height="12" rx="2" fill="{OUT_OF_RANGE_COLOUR}"/>'
            f'<text x="{x + wide / 2}" y="16" font-size="9" '
            f'text-anchor="middle" fill="{OUT_OF_RANGE_COLOUR}">off</text>'
        )

    for lane in lanes:
        x = positions[lane["index"]]
        lane_width = _lane_width(lane, instrument)
        edge = (
            ' stroke="#90a4ae" stroke-width="1"'
            if lane["colour"] == "#ffffff" else ""
        )
        labels.append(
            f'<rect x="{x + 2}" y="22" width="{lane_width - 4}" '
            f'height="12" rx="2" fill="{lane["colour"]}"{edge}/>'
            f'<text x="{x + lane_width / 2}" y="16" font-size="10" '
            f'text-anchor="middle" fill="#455a64">'
            f'{html.escape(lane["label"])}</text>'
            f'<text x="{x + lane_width / 2}" y="44" font-size="8" '
            f'text-anchor="middle" fill="#90a4ae">'
            f'{html.escape(lane["sub"])}</text>'
        )

    labels.append("</svg>")
    header_parts = ["".join(labels)]

    if header == HEADER_COMPACT:
        compact, _height = _compact_header(
            lanes, positions, instrument, total_width, left, spare, wide
        )
        header_parts = [compact]

    if header in (HEADER_PICTURE, HEADER_SHORT):
        picture, _height = _picture_header(
            lanes, positions, instrument, total_width,
            short=header == HEADER_SHORT,
        )
        header_parts.append(picture)

    strong = {
        round(start, 4) for start in _bar_lines(chart_text, total_beats)
    }
    lane_by_index = {lane["index"]: lane for lane in lanes}
    alone = not blocks

    def body_svg(low, high, last=True):
        """
        The notes of [low, high) as one scrolling picture. A piece
        that is not the song's last leaves the beat line at its end
        to the piece after it, and keeps only a small margin under.
        """

        span = high - low
        body_height = int(span * BEAT_PX) + (24 if last else 4) + TOP_PAD

        strip_blocks = _note_slice(blocks, low, high)
        strip_chords = _span_slice(chords, low, high) if low or (
            high < total_beats
        ) else chords
        strip_names = _span_slice(chord_names, low, high) if low or (
            high < total_beats
        ) else chord_names

        body = [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {total_width} {body_height}" width="100%" '
            f'style="display:block" '
            f'role="img" aria-label="The melody, notes running down '
            f'the lanes">'
        ]

        body.append(f'<g transform="translate(0,{TOP_PAD})">')

        # White (and ordinary) lanes first, alternating; a piano's
        # black lanes after, so the half of one that overlaps a
        # neighbour is not painted over.
        ordinary = [
            (positions[lane["index"]], _lane_width(lane, instrument))
            for lane in lanes if lane.get("kind") != "black"
        ]
        black = [
            (positions[lane["index"]], _lane_width(lane, instrument))
            for lane in lanes if lane.get("kind") == "black"
        ]

        if spare:
            ordinary.insert(0, (left, wide))

        for order, (x, stripe_width) in enumerate(ordinary):
            shade = "#f3f6f8" if order % 2 == 0 else "none"
            body.append(
                f'<rect x="{x}" y="0" width="{stripe_width}" '
                f'height="{body_height}" fill="{shade}"/>'
            )

        for x, stripe_width in black:
            body.append(
                f'<rect x="{x}" y="0" width="{stripe_width}" '
                f'height="{body_height}" fill="#e3e8ec"/>'
            )

        # The song's own beats: a strip that starts part way in
        # still numbers them from the song's start.
        first_beat = -int(-low // 1)

        last_beat = (
            int(high) if last or high != int(high) else int(high) - 1
        )

        for beat in range(first_beat, last_beat + 1):
            y = (beat - low) * BEAT_PX
            is_bar = float(beat) in strong
            body.append(
                f'<line x1="{left}" x2="{width}" y1="{y}" y2="{y}" '
                f'stroke="{"#90a4ae" if is_bar else "#e0e6ea"}" '
                f'stroke-width="{1.5 if is_bar else 1}"/>'
            )

            if is_bar:
                body.append(
                    f'<text x="{left - 8}" y="{y + 4}" font-size="10" '
                    f'text-anchor="end" fill="#78909c">'
                    f'beat {beat + 1}</text>'
                )

        # The chord layer sits under the melody, paler.
        for chord in strip_chords:
            lane = lane_by_index.get(chord["lane"])

            if lane is None:
                continue

            x = positions[chord["lane"]] + 1
            chord_width = _lane_width(lane, instrument) - 2
            y = chord["start"] * BEAT_PX + 2
            height = max(chord["length"] * BEAT_PX - 4, 4)

            body.append(
                f'<rect x="{x}" y="{y}" width="{chord_width}" '
                f'height="{height}" rx="4" fill="{CHORD_TONE_COLOUR}" '
                f'fill-opacity="{0.55 if alone else 0.25}"/>'
            )

        # Each chord's name and a bar the length of it, in the margin.
        for span_ in strip_names:
            y = span_["start"] * BEAT_PX + 2
            height = max(span_["length"] * BEAT_PX - 4, 4)

            body.append(
                f'<rect x="4" y="{y}" width="4" height="{height}" '
                f'rx="2" fill="{CHORD_TONE_COLOUR}"/>'
            )

            # Half-beat chords get a smaller name; shorter ones keep
            # only their bar.
            if height >= 9:
                size = 12 if height >= 14 else 9
                body.append(
                    f'<text x="14" y="{y + min(12, height - 1)}" '
                    f'font-size="{size}" '
                    f'font-weight="600" fill="{CHORD_TONE_COLOUR}">'
                    f'{html.escape(span_["name"])}</text>'
                )

        for block in strip_blocks:
            y = block["start"] * BEAT_PX + 2
            height = max(block["length"] * BEAT_PX - 4, 8)
            block_width = wide - 8

            if block["in_range"]:
                x = positions[block["lane"]] + 4
                colour = (
                    ROW_COLOURS[block["row"]] if block["row"]
                    else MELODY_COLOUR
                )
                mark = ""

                if block["lever"]:
                    mark = "↑"

                if block["black"]:
                    block_width = narrow - 4
                    x = positions[block["lane"]] + 2
            else:
                x = left + 4
                colour = OUT_OF_RANGE_COLOUR
                mark = "▼" if block["where"] == "below" else "▲"

            label = html.escape(block["note"]) + mark
            shifted = block["in_range"] and block["shift"]

            if shifted:
                body.append(f'<g class="melody-shifted"><title>'
                            f'{html.escape(_shift_title(block))}'
                            f'</title>')

            body.append(
                f'<rect x="{x}" y="{y}" width="{block_width}" '
                f'height="{height}" rx="6" fill="{colour}"/>'
            )

            # A string whose lever must be up wears the lever's tab.
            if block["in_range"] and block["lever"]:
                body.append(
                    f'<rect x="{x + block_width / 2 - 5}" y="{y - 3}" '
                    f'width="10" height="5" rx="1" fill="#eceff1" '
                    f'stroke="#607d8b" stroke-width="1"/>'
                )

            # A very short block has no room to read a name in.
            if height >= 16:
                body.append(
                    f'<text x="{x + block_width / 2}" y="{y + 13}" '
                    f'font-size="{9 if block["black"] else 10}" '
                    f'text-anchor="middle" fill="#ffffff">'
                    f'{label}</text>'
                )

            # An amber pill over the block: which way, and how far,
            # the note was moved to fit the instrument ("8va" as in
            # sheet music; 16va for two octaves).
            if shifted:
                arrow = "▲" if block["shift"] > 0 else "▼"
                text = f'{arrow} {8 * abs(block["shift"])}va'
                pill_width = 14 + 6.2 * len(text)
                centre = x + block_width / 2

                body.append(
                    f'<rect class="octave-flag" '
                    f'x="{centre - pill_width / 2}" y="{y - 10}" '
                    f'width="{pill_width}" height="15" rx="7.5" '
                    f'fill="{OCTAVE_COLOUR}"/>'
                    f'<text x="{centre}" y="{y + 0.8}" font-size="10" '
                    f'font-weight="800" text-anchor="middle" '
                    f'fill="{OCTAVE_TEXT_COLOUR}">{text}</text>'
                )
                body.append("</g>")

            if block["lyric"]:
                body.append(
                    f'<text x="{width + 12}" y="{y + 13}" '
                    f'font-size="12" fill="#37474f">'
                    f'{html.escape(block["lyric"])}</text>'
                )

        body.append("</g></svg>")

        return "".join(body)

    # A cropped keyboard has few lanes; do not let each balloon.
    narrow_cap = (
        int(total_width * 1.8) if len(lanes) < 14 else None
    )
    height_cap = "85vh" if header == HEADER_PICTURE else "70vh"
    frame = (
        f'max-height:{height_cap};overflow-y:auto;'
        'border:1px solid var(--border-color-primary,#ccc);'
        'border-radius:8px'
    )

    ranges = phrase_ranges(cuts, total_beats, columns)

    if len(ranges) == 1:
        narrow_page = f"max-width:{narrow_cap}px;" if narrow_cap else ""

        return (
            f'<div class="melody-lanes" style="{narrow_page}{frame}">'
            '<div style="position:sticky;top:0;z-index:2">'
            + "".join(header_parts)
            + "</div>"
            + body_svg(0, total_beats)
            + "</div>"
        )

    # One piece per phrase, stacked under one header: as it stands
    # that is the one tall strip. In the browser FLOW_JS packs the
    # pieces into columns, as many whole phrases to a column as fit
    # the height left on screen under the controls, and the columns
    # into screens. data-least is the narrowest a column may be
    # (Auto), data-max the most columns, data-cap a cropped
    # keyboard's widest.
    pieces = "".join(
        f'<div class="melody-cell" data-from="{low}">'
        + body_svg(low, high, last=index == len(ranges) - 1)
        + "</div>"
        for index, (low, high) in enumerate(ranges)
    )
    narrow_page = f"max-width:{narrow_cap}px;" if narrow_cap else ""
    mode = "two" if columns == COLUMNS_TWO else "auto"
    most = 2 if columns == COLUMNS_TWO else MAX_AUTO_COLUMNS

    return (
        f'<div class="melody-lanes melody-flow" data-columns="{mode}" '
        f'data-least="{int(total_width * AUTO_SCALE)}" '
        f'data-max="{most}" data-cap="{narrow_cap or 0}" '
        f'style="{narrow_page}{frame}">'
        '<div class="melody-head" style="position:sticky;top:0;'
        'z-index:2">'
        + "".join(header_parts)
        + "</div>"
        + f'<div class="melody-cells">{pieces}</div>'
        + "</div>"
    )


OCTAVE_LEGEND = (
    " An amber pill (▲ 8va up, ▼ 8va down) is a note the "
    "instrument cannot play as written, moved to the nearest octave "
    "that it can; hover for the real note."
)

LEGEND = (
    "Time runs down the page, the words beside each note. On the "
    "kalimba, blue notes are the middle row, purple the top row "
    "(the sharps and flats) and green the bass row."
)

LEGENDS = {
    "Kalimba": LEGEND,
    "Lever harp": (
        "Time runs down the page, the words beside each note. C "
        "strings are red and F strings blue, as on the harp. ↑ with "
        "a small tab means that string's lever must be up for the "
        "note."
    ),
    "Piano": (
        "Time runs down the page, the words beside each note. Wide "
        "lanes are the white keys, narrow ones the black keys. Only "
        "the keys the tune needs, with a little spare, are shown."
    ),
}

CHORD_LEGEND = (
    "Pale pink blocks are the chords, behind the melody; each "
    "chord's name and length are in the left margin."
)


# --- full screen ------------------------------------------------

# Like the chord sheet's: a class on the whole section, toggled in
# the browser, so it reads and writes none of the song's boxes.
# Escape leaves it.
MELODY_CSS = """
#melody.melody-full {
    position: fixed;
    inset: 0;
    z-index: 100000;
    overflow: auto;
    padding: 10px 16px;
    background: var(--background-fill-primary, #fff);
}
/* The section itself scrolls, so the pictures get the whole
   height; the lanes' header still sticks to the top. */
#melody.melody-full .melody-lanes,
#melody.melody-full .melody-tab {
    max-height: none !important;
    overflow: visible !important;
}
#melody.melody-full .melody-lanes { max-width: none !important; }
/* The size choice (34 or 41 keys...) sits on the tab names' line,
   at the right, instead of a line of its own. */
#melody .tabitem, #melody .tabitem > .column { position: static; }
#melody .tabitem .sheet-size {
    position: absolute; top: 0; right: 0; width: auto !important;
}
/* The section is a column with a fixed height here; without this
   its blocks (the phrase list, the status line) are squeezed to fit
   it instead of the section scrolling. */
#melody.melody-full > * { flex-shrink: 0; }
/* The heading and the sentence under it are for the page, not for
   a screen given over to the notes. */
#melody.melody-full .melody-intro { display: none; }
"""

FULL_SCREEN_JS = """
() => {
    const section = document.getElementById('melody');
    const button = document.getElementById('melody-full-button');
    const set = (on) => {
        section.classList.toggle('melody-full', on);
        if (button) {
            button.textContent = on ? 'Exit full screen' : 'Full screen';
        }
    };
    if (!window.__melodyEscape) {
        window.__melodyEscape = true;
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && section.classList.contains('melody-full')) {
                set(false);
            }
        });
    }
    set(!section.classList.contains('melody-full'));
}
"""


# --- columns and pages, in the browser ----------------------------

# Packs the phrase pieces of each .melody-flow into columns and the
# columns into pages: as many whole phrases to a column as fit the
# height left on screen once the controls, tabs and warning line
# above the lanes are counted, and as many columns side by side as
# the width allows (Auto: each at least data-least wide, at most
# data-max; Two: two). One page shows at a time; the ◀ ▶ buttons or
# the ← → keys turn it. A column and a page always begin at a phrase.
# The One column choice never reaches here (Python draws the one tall
# strip, which scrolls).
#
# Only moves the pieces about; it reads and writes none of the
# song's boxes. Runs once, on page load, and lays out again when a
# view is redrawn, the window or a tab changes size, or full screen
# goes on or off.
FLOW_JS = """
() => {
    if (window.__melodyFlow) { return; }
    window.__melodyFlow = true;
    const GAP = %(gap)d;
    const PAGER = 34;

    // The height an element's pictures take at a width: each SVG is
    // drawn at width 100%%, so its viewBox gives it.
    const heightAt = (box, width) => {
        let total = 0;
        box.querySelectorAll('svg').forEach((svg) => {
            const view = svg.viewBox && svg.viewBox.baseVal;
            if (view && view.width) {
                total += view.height * width / view.width;
            }
        });
        return total;
    };

    const show = (flow, page) => {
        const pages = flow.querySelectorAll(':scope > .melody-pages > .melody-page');
        if (!pages.length) { return; }
        page = Math.max(0, Math.min(pages.length - 1, page));
        flow.__page = page;
        pages.forEach((row, index) => {
            row.style.display = index === page ? 'grid' : 'none';
        });
        const pager = flow.querySelector(':scope > .melody-pager');
        if (pager) {
            pager.querySelector('.melody-page-count').textContent =
                'Page ' + (page + 1) + ' of ' + pages.length;
            pager.querySelector('.melody-back').disabled = page === 0;
            pager.querySelector('.melody-next').disabled = page === pages.length - 1;
        }
    };

    const layout = (flow) => {
        const host = flow.parentElement;
        const width = host ? host.clientWidth : 0;
        if (!width) { return; }  // a hidden tab: wait until shown

        const section = flow.closest('#melody');
        const full = !!(section && section.classList.contains('melody-full'));
        const least = Number(flow.dataset.least) || 1;
        const most = Number(flow.dataset.max) || 1;
        const cap = Number(flow.dataset.cap) || 0;
        const columns = flow.dataset.columns === 'two' ? 2 : Math.max(
            1, Math.min(most, Math.floor((width + GAP) / (least + GAP)))
        );

        // Height for a page. Full screen: what is left of the screen
        // under everything above the lanes (the controls stay put,
        // pages turn instead of scrolling). In the page: the lanes'
        // own box.
        let room;
        if (full) {
            const above = flow.getBoundingClientRect().top
                - section.getBoundingClientRect().top + section.scrollTop;
            room = section.clientHeight - above - 16;
        } else {
            room = (parseFloat(getComputedStyle(flow).maxHeight)
                || window.innerHeight * 0.7) - 6;
        }
        room -= PAGER;

        // In the page, one column stays the one tall strip, which
        // scrolls in its box (a page per phrase would be no help).
        const strip = columns === 1 && !full;
        const key = [width, columns, Math.round(room), strip].join(' ');
        const packed = flow.querySelector(':scope > .melody-pages');

        // Gradio patches a redrawn view into the same element, which
        // throws the pages away: then pack again from what is there.
        if (!packed) { flow.__cells = null; }
        if (flow.__key === key && (packed || strip)) { return; }
        flow.__key = key;

        const pool = flow.querySelector(':scope > .melody-cells');
        const head = flow.querySelector(':scope > .melody-head');
        if (!pool || !head) { return; }
        const cells = flow.__cells
            || (flow.__cells = [...pool.querySelectorAll('.melody-cell')]);

        // Back to the one tall strip, then re-pack.
        flow.querySelectorAll(':scope > .melody-pages, :scope > .melody-pager')
            .forEach((n) => n.remove());
        cells.forEach((cell) => pool.appendChild(cell));
        head.style.display = '';
        pool.style.display = '';
        flow.style.overflowY = '';

        if (strip) {
            flow.style.maxWidth = cap ? cap + 'px' : '';
            return;
        }

        flow.style.maxWidth = '';
        let column = (flow.clientWidth - 2 - GAP * (columns - 1)) / columns;
        if (cap) { column = Math.min(column, cap); }
        const space = room - heightAt(head, column);

        const screens = [];
        let screen = [];
        let stack = [];
        let used = 0;

        cells.forEach((cell) => {
            const tall = heightAt(cell, column);
            if (stack.length && used + tall > space) {
                screen.push(stack);
                stack = [];
                used = 0;
                if (screen.length === columns) {
                    screens.push(screen);
                    screen = [];
                }
            }
            stack.push(cell);
            used += tall;
        });
        if (stack.length) { screen.push(stack); }
        if (screen.length) { screens.push(screen); }

        const pages = document.createElement('div');
        pages.className = 'melody-pages';
        screens.forEach((stacks) => {
            const row = document.createElement('div');
            row.className = 'melody-page';
            row.style.cssText = 'gap:' + GAP + 'px;'
                + 'grid-template-columns:repeat(' + columns + ',' + column + 'px);'
                + 'align-items:start';
            stacks.forEach((pieces) => {
                const col = document.createElement('div');
                col.className = 'melody-col';
                const top = head.cloneNode(true);
                top.style.position = 'static';
                top.style.display = '';
                col.appendChild(top);
                pieces.forEach((cell) => col.appendChild(cell));
                row.appendChild(col);
            });
            pages.appendChild(row);
        });

        const pager = document.createElement('div');
        pager.className = 'melody-pager';
        pager.style.cssText = 'display:flex;align-items:center;gap:8px;'
            + 'justify-content:flex-end;height:' + (PAGER - 6) + 'px;'
            + 'margin-bottom:6px;font-size:13px';
        pager.innerHTML =
            '<span style="opacity:.6;margin-right:auto">← → turn the page</span>'
            + '<button type="button" class="melody-back">◀</button>'
            + '<span class="melody-page-count"></span>'
            + '<button type="button" class="melody-next">▶</button>';
        pager.querySelector('.melody-back').onclick = () => show(flow, flow.__page - 1);
        pager.querySelector('.melody-next').onclick = () => show(flow, flow.__page + 1);
        if (screens.length < 2) { pager.style.visibility = 'hidden'; }

        head.style.display = 'none';
        pool.style.display = 'none';
        flow.style.overflowY = 'hidden';
        flow.insertBefore(pager, head);
        flow.appendChild(pages);
        show(flow, flow.__page || 0);
    };

    let pending = false;
    const all = () => {
        if (pending) { return; }
        pending = true;
        requestAnimationFrame(() => {
            pending = false;
            document.querySelectorAll('.melody-flow').forEach(layout);
        });
    };

    // ← → turn the page of the lanes on show (not while typing, or
    // while a choice that uses the arrows itself has the focus).
    document.addEventListener('keydown', (event) => {
        if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') { return; }
        const target = event.target;
        if (target && (target.closest('input, textarea, select, [contenteditable]')
            || target.isContentEditable)) { return; }
        const shown = [...document.querySelectorAll('.melody-flow')]
            .filter((flow) => flow.offsetParent && flow.__key);
        if (!shown.length) { return; }
        shown.forEach((flow) => show(
            flow, (flow.__page || 0) + (event.key === 'ArrowRight' ? 1 : -1)
        ));
        event.preventDefault();
    });

    new MutationObserver(all).observe(document.body, {
        childList: true, subtree: true,
        attributes: true, attributeFilter: ['class', 'style'],
    });
    window.addEventListener('resize', all);
    all();
}
""" % {"gap": COLUMN_GAP}


# --- one view of the song ---------------------------------------

def melody_view(piece, instrument, show=None, header=HEADER_COMPACT,
                placement=NEAR_MELODY, fingering=NEAREST_NUT,
                width=DEFAULT_WIDTH, open_free=True, prefer_low=False,
                fold=True, columns=COLUMNS_AUTO):
    """
    Everything one instrument tab shows for a piece (a phrase
    or the whole tune), as HTML: the out-of-range line if there
    is one, the lanes, and a one-line legend.

    show says which layers to draw (Melody, Chords; both by
    default); a view with neither ticked shows the melody, so it
    is never blank. header is the instrument's own picture over
    the lanes, or plain lane names. placement is where the chord
    layer goes.
    """

    # Guitar and ukulele are tab, read across the page, in their
    # own module (PLAN-fretted-tab.md). The tab is its own picture,
    # so header and placement do not apply; Show does.
    if _base_instrument_name(instrument) in FRETTED:
        from fretted_tab import fretted_view

        return fretted_view(
            piece, instrument, fingering, width, open_free, show,
            prefer_low
        )

    # Flute and alto sax are a chart per note in phrase rows, in
    # their own module (PLAN-wind-melody.md): a note there is a hand
    # shape, not a place, so there are no lanes. Show applies; the
    # header and placement do not.
    if _base_instrument_name(instrument) in WINDS:
        from wind_melody import wind_view

        return wind_view(piece, instrument, show, fold)

    show = DEFAULT_SHOW if show is None else list(show)
    want_melody = SHOW_MELODY in show or SHOW_CHORDS not in show
    want_chords = SHOW_CHORDS in show

    blocks = melody_blocks(piece, instrument)
    message = range_message(blocks, instrument) if want_melody else ""

    if not blocks:
        return "<p>No notes to show yet.</p>"

    chords = []
    names = []

    if want_chords:
        chords = chord_blocks(piece, instrument, blocks, placement)
        names = chord_spans(piece)

    warning = (
        f'<div style="color:{OUT_OF_RANGE_COLOUR};margin:4px 0">'
        f"{html.escape(message)}</div>" if message else ""
    )

    legend = LEGENDS[_base_instrument_name(instrument)]

    if want_melody and any(block["shift"] for block in blocks):
        legend += OCTAVE_LEGEND

    if chords:
        legend += " " + CHORD_LEGEND

    return (
        warning
        + lanes_html(
            blocks if want_melody else [], instrument, piece.beats(),
            piece.chart, chords, names, header, columns,
            row_starts(piece)
        )
        + f'<div style="font-size:0.85em;opacity:0.75;margin-top:4px">'
        f"{html.escape(legend)}</div>"
    )


# --- which instruments have lanes -------------------------------

# Families the view can draw, as {family: [variants]}, taken
# from the one list of instruments (INSTRUMENTS).
# Guitar and ukulele are drawn as tab (fretted_tab.py).
FRETTED = ("Guitar", "Ukulele")

SUPPORTED = ("Kalimba", "Lever harp", "Piano") + FRETTED


def option_rows(family):
    """
    Which option rows a tab needs: (guitar and ukulele options, flute
    and sax options). Every other tab shows neither, so the controls
    over the pictures stay one slim bar.
    """

    return (family in FRETTED, family in WINDS)


def supported_families():
    from chord_sheet import instrument_families

    families = {
        family: variants
        for family, variants in instrument_families().items()
        if family in SUPPORTED
    }

    # The winds are not in INSTRUMENTS (the mixer and the chord sheet
    # have no picture for them), so they join here, one size each,
    # after the others.
    for wind in WINDS:
        families[wind] = [wind]

    return families


def default_variant(family, variants):
    """
    Which size a tab starts on. The kalimba starts on the
    41 keys - the bass row is where a song's lowest notes go.
    """

    if family in WINDS:
        return family

    if family == "Kalimba":
        for name in variants:
            if "41" in name:
                return name

    # A guitar or ukulele starts on its longer neck: fewer notes
    # fall off the end of it.
    if family in FRETTED:
        return variants[-1]

    from chord_sheet import default_variant as sheet_default

    return sheet_default(family, variants)


# --- the page: what the section shows for the boxes' text -------

def phrase_choices(pitch_text, duration_text, lyric_text):
    """The view's own phrase list (its own, never the mixer's)."""

    from music import list_phrases

    return list_phrases(pitch_text, duration_text, lyric_text)


def keep_phrase(label, choices):
    """
    The chosen phrase after the list changed: the same phrase
    number if there still is one, else the whole part.
    """

    from music import WHOLE_PART, phrase_chosen

    if label in choices:
        return label

    number = phrase_chosen(label) if label else None

    if number is not None:
        for choice in choices:
            if phrase_chosen(choice) == number:
                return choice

    return WHOLE_PART


def melody_page(pitch_text, duration_text, lyric_text, key_text,
                chart_text, phrase_label, instruments, show=None,
                header=HEADER_COMPACT, placement=NEAR_MELODY,
                fingering=NEAREST_NUT, width=DEFAULT_WIDTH,
                open_free=True, prefer_low=False, fold=True,
                columns=COLUMNS_AUTO):
    """
    What the Melody section shows for the text of the boxes:
    {"choices", "label", "views", "status"}. Reads the boxes'
    text and nothing else; it cannot write them. Music that
    cannot be read yet (a half-typed box) gives a plain message
    in every tab instead of failing.
    """

    from music import MusicInputError, WHOLE_PART, selected_piece

    choices = phrase_choices(pitch_text, duration_text, lyric_text)
    label = keep_phrase(phrase_label, choices)

    try:
        piece = selected_piece(
            pitch_text, duration_text, lyric_text, key_text,
            chart_text, phrase_label=label,
        )

    except (MusicInputError, ValueError) as problem:
        text = f"<p>{html.escape(str(problem))}</p>"

        return {
            "choices": choices,
            "label": label,
            "views": [text for _ in instruments],
            "status": "",
        }

    status = (
        "The whole tune." if label == WHOLE_PART
        else f"{label.split(':')[0]}."
    )

    return {
        "choices": choices,
        "label": label,
        "views": [
            melody_view(
                piece, name, show, header, placement, fingering,
                width, open_free, prefer_low, fold, columns
            )
            for name in instruments
        ],
        "status": status,
    }
