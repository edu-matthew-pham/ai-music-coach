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
from notes import is_rest


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
         "thumb", "row", "lever", "black", "in_range", "where"}

    start and length are in beats from the start of the piece
    handed in (a phrase's own start, when it was sliced). lane
    is the lane's index (None when the instrument has no tine
    for the note), thumb is "left", "right" or "centre", row is
    "middle", "top" or "bass" (kalimba only), lever is True
    where a harp string needs its lever up for the note (None
    off the harp), black marks a piano's black key, and where is "below" or "above"
    for a note off the instrument. note is the name as written
    in the boxes, without its octave. Rests leave a gap and
    are not blocks.
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

        pitch = _absolute_pitch(written)
        lane, row, lever = _place(pitch, instrument)

        # A pitch inside the range with no tine (cannot happen on
        # a chromatic kalimba, but the check costs nothing) is
        # off the instrument too.
        in_range = lane is not None

        where = None

        if not in_range:
            where = "below" if pitch < low["pitch"] else "above"

        blocks.append({
            "lane": lane,
            "start": starts[index],
            "length": piece.durations[index],
            "note": written[:-1],
            "pitch": pitch,
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


def range_message(blocks, instrument):
    """
    In words, how many notes are off the instrument, and what
    would fix it. "" when every note is on it. Never moves a
    note: the octave buttons stay the player's to press.
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

    def fits_after(shift):
        return all(
            _place(block["pitch"] + shift, instrument)[0] is not None
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

    return (
        " and ".join(parts)
        + ". They are drawn in red in the strip at the left. "
        + fix
    )


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

HEADER_LABELS = "Plain labels"
HEADER_SHORT = "Short picture"
HEADER_PICTURE = "Full picture"
# The short picture first (Matthew, 2026-10-26): the instrument
# over its lanes, cropped to its upper part. The full picture is
# tall (kalimba 340px, harp 400px); plain labels are the smallest.
HEADERS = [HEADER_SHORT, HEADER_PICTURE, HEADER_LABELS]


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

_ROW_MARK = {"top": "▲", "bass": "▼"}

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


# How much of the picture's height the short version keeps.
SHORT_PICTURE_FRACTION = 0.55
SHORT_PICTURE_MINIMUM = 100


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


def lanes_html(blocks, instrument, total_beats, chart_text="",
               chords=None, chord_names=None, header=HEADER_LABELS):
    """
    The lanes picture for one instrument as HTML: a header that
    stays put (lane names, or the instrument's own picture) and
    the notes scrolling under it, time running down.
    total_beats is how long the stretch is.

    chords is the chord layer's blocks (drawn first, pale, under
    the melody) and chord_names the chord spans for the left
    margin; both None draws the melody alone.
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
    body_height = int(total_beats * BEAT_PX) + 24 + TOP_PAD

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

    if header in (HEADER_PICTURE, HEADER_SHORT):
        picture, _height = _picture_header(
            lanes, positions, instrument, total_width,
            short=header == HEADER_SHORT,
        )
        header_parts.append(picture)

    # --- body ---
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

    strong = {
        round(start, 4) for start in _bar_lines(chart_text, total_beats)
    }

    for beat in range(int(total_beats) + 1):
        y = beat * BEAT_PX
        is_bar = float(beat) in strong
        body.append(
            f'<line x1="{left}" x2="{width}" y1="{y}" y2="{y}" '
            f'stroke="{"#90a4ae" if is_bar else "#e0e6ea"}" '
            f'stroke-width="{1.5 if is_bar else 1}"/>'
        )

        if is_bar:
            body.append(
                f'<text x="{left - 8}" y="{y + 4}" font-size="10" '
                f'text-anchor="end" fill="#78909c">beat {beat + 1}</text>'
            )

    # The chord layer sits under the melody, paler.
    lane_by_index = {lane["index"]: lane for lane in lanes}
    alone = not blocks

    for chord in chords:
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
    for span in chord_names:
        y = span["start"] * BEAT_PX + 2
        height = max(span["length"] * BEAT_PX - 4, 4)

        body.append(
            f'<rect x="4" y="{y}" width="4" height="{height}" rx="2" '
            f'fill="{CHORD_TONE_COLOUR}"/>'
        )

        # Half-beat chords get a smaller name; shorter ones keep
        # only their bar.
        if height >= 9:
            size = 12 if height >= 14 else 9
            body.append(
                f'<text x="14" y="{y + min(12, height - 1)}" '
                f'font-size="{size}" '
                f'font-weight="600" fill="{CHORD_TONE_COLOUR}">'
                f'{html.escape(span["name"])}</text>'
            )

    for block in blocks:
        y = block["start"] * BEAT_PX + 2
        height = max(block["length"] * BEAT_PX - 4, 8)
        block_width = wide - 8

        if block["in_range"]:
            x = positions[block["lane"]] + 4
            colour = (
                THUMB_COLOURS[block["thumb"]] if block["thumb"]
                else MELODY_COLOUR
            )
            mark = _ROW_MARK.get(block["row"], "")

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

        if block["lyric"]:
            body.append(
                f'<text x="{width + 12}" y="{y + 13}" font-size="12" '
                f'fill="#37474f">{html.escape(block["lyric"])}</text>'
            )

    body.append("</g></svg>")

    # A cropped keyboard has few lanes; do not let each balloon.
    narrow_page = (
        f"max-width:{int(total_width * 1.8)}px;" if len(lanes) < 14
        else ""
    )

    return (
        f'<div class="melody-lanes" style="{narrow_page}max-height:{"85vh" if header == HEADER_PICTURE else "70vh"};'
        'overflow-y:auto;border:1px solid var(--border-color-primary,#ccc);'
        'border-radius:8px">'
        '<div style="position:sticky;top:0;z-index:2">'
        + "".join(header_parts)
        + "</div>"
        + "".join(body)
        + "</div>"
    )


LEGEND = (
    "Time runs down the page, the words beside each note. On the "
    "kalimba, blue is the left thumb, purple the right and grey "
    "the centre tine. ▲ is a top-row tine (a sharp or flat), "
    "▼ a bass-row tine."
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


# --- one view of the song ---------------------------------------

def melody_view(piece, instrument, show=None, header=HEADER_SHORT,
                placement=NEAR_MELODY):
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
    # own module (PLAN-fretted-tab.md).
    if _base_instrument_name(instrument) in FRETTED:
        from fretted_tab import fretted_view

        return fretted_view(piece, instrument)

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

    if chords:
        legend += " " + CHORD_LEGEND

    return (
        warning
        + lanes_html(
            blocks if want_melody else [], instrument, piece.beats(),
            piece.chart, chords, names, header
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


def supported_families():
    from chord_sheet import instrument_families

    return {
        family: variants
        for family, variants in instrument_families().items()
        if family in SUPPORTED
    }


def default_variant(family, variants):
    """
    Which size a tab starts on. The kalimba starts on the
    41 keys - the bass row is where a song's lowest notes go.
    """

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
                header=HEADER_SHORT, placement=NEAR_MELODY):
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
            melody_view(piece, name, show, header, placement)
            for name in instruments
        ],
        "status": status,
    }
