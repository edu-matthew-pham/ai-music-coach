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

    raise ValueError(f"No lanes for {instrument}.")


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


def instrument_range(instrument):
    """(lowest, highest) pitch the instrument can sound, with names."""

    base = _base_instrument_name(instrument)

    if base == "Kalimba":
        tines = _kalimba_tines(_kalimba_has_bass(instrument))
        low = min(tines, key=lambda tine: tine["pitch"])
        high = max(tines, key=lambda tine: tine["pitch"])

        return low, high

    raise ValueError(f"No range for {instrument}.")


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
         "thumb", "row", "in_range", "where"}

    start and length are in beats from the start of the piece
    handed in (a phrase's own start, when it was sliced). lane
    is the lane's index (None when the instrument has no tine
    for the note), thumb is "left", "right" or "centre", row is
    "middle", "top" or "bass", and where is "below" or "above"
    for a note off the instrument. note is the name as written
    in the boxes, without its octave. Rests leave a gap and
    are not blocks.
    """

    base = _base_instrument_name(instrument)

    if base != "Kalimba":
        raise ValueError(f"No lanes for {instrument}.")

    low, high = instrument_range(instrument)
    starts = piece.starts()
    lyrics = _lyrics_per_note(piece)
    blocks = []

    for index, written in enumerate(piece.pitches):

        if is_rest(written):
            continue

        pitch = _absolute_pitch(written)
        lane, row = _place_kalimba(pitch, instrument)

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
            "thumb": _kalimba_thumb(lane) if in_range else None,
            "row": row,
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
    parts = []

    if below:
        parts.append(
            f"{below} {'note is' if below == 1 else 'notes are'} "
            f"below the lowest tine ({low['note']})"
        )

    if above:
        parts.append(
            f"{above} {'note is' if above == 1 else 'notes are'} "
            f"above the highest ({high['note']})"
        )

    def fits_after(shift):
        return all(
            _place_kalimba(block["pitch"] + shift, instrument)[0]
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

    return (
        " and ".join(parts)
        + ". They are drawn in red in the strip at the left. "
        + fix
    )


# --- the drawing -------------------------------------------------

BEAT_PX = 28
HEADER_HEIGHT = 46
TOP_PAD = 10
LEFT_MARGIN = 62
RIGHT_MARGIN = 150

_ROW_MARK = {"top": "▲", "bass": "▼"}


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


def _lane_positions(lanes, spare):
    """x of each lane (and of the out-of-range strip, if any)."""

    first = LANE_WIDTH if spare else 0
    positions = {
        lane["index"]: LEFT_MARGIN + first + position * LANE_WIDTH
        for position, lane in enumerate(lanes)
    }

    return positions, LEFT_MARGIN + first + len(lanes) * LANE_WIDTH


def lanes_html(blocks, instrument, total_beats, chart_text=""):
    """
    The lanes picture for one instrument as HTML: a header of
    lane names that stays put and the notes scrolling under it,
    time running down. total_beats is how long the stretch is.
    """

    lanes = lanes_for(instrument)
    spare = any(not block["in_range"] for block in blocks)
    positions, width = _lane_positions(lanes, spare)
    total_width = width + RIGHT_MARGIN
    body_height = int(total_beats * BEAT_PX) + 24 + TOP_PAD

    # --- header ---
    header = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {total_width} {HEADER_HEIGHT}" width="100%" '
        f'style="display:block;'
        f'background:var(--background-fill-primary,#fff)" '
        f'role="img" aria-label="The lanes: one per tine">'
    ]

    if spare:
        x = LEFT_MARGIN
        header.append(
            f'<rect x="{x + 2}" y="22" width="{LANE_WIDTH - 4}" '
            f'height="12" rx="2" fill="{OUT_OF_RANGE_COLOUR}"/>'
            f'<text x="{x + LANE_WIDTH / 2}" y="16" font-size="9" '
            f'text-anchor="middle" fill="{OUT_OF_RANGE_COLOUR}">off</text>'
        )

    for lane in lanes:
        x = positions[lane["index"]]
        header.append(
            f'<rect x="{x + 2}" y="22" width="{LANE_WIDTH - 4}" '
            f'height="12" rx="2" fill="{lane["colour"]}"/>'
            f'<text x="{x + LANE_WIDTH / 2}" y="16" font-size="10" '
            f'text-anchor="middle" fill="#455a64">'
            f'{html.escape(lane["label"])}</text>'
            f'<text x="{x + LANE_WIDTH / 2}" y="44" font-size="8" '
            f'text-anchor="middle" fill="#90a4ae">'
            f'{html.escape(lane["sub"])}</text>'
        )

    header.append("</svg>")

    # --- body ---
    body = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {total_width} {body_height}" width="100%" '
        f'style="display:block" '
        f'role="img" aria-label="The melody, notes running down '
        f'the lanes">'
    ]

    body.append(f'<g transform="translate(0,{TOP_PAD})">')

    lane_positions = list(positions.values())

    if spare:
        lane_positions = [LEFT_MARGIN] + lane_positions

    for order, x in enumerate(lane_positions):
        shade = "#f3f6f8" if order % 2 == 0 else "none"
        body.append(
            f'<rect x="{x}" y="0" width="{LANE_WIDTH}" '
            f'height="{body_height}" fill="{shade}"/>'
        )

    strong = {
        round(start, 4) for start in _bar_lines(chart_text, total_beats)
    }

    for beat in range(int(total_beats) + 1):
        y = beat * BEAT_PX
        is_bar = float(beat) in strong
        body.append(
            f'<line x1="{LEFT_MARGIN}" x2="{width}" y1="{y}" y2="{y}" '
            f'stroke="{"#90a4ae" if is_bar else "#e0e6ea"}" '
            f'stroke-width="{1.5 if is_bar else 1}"/>'
        )

        if is_bar:
            body.append(
                f'<text x="{LEFT_MARGIN - 8}" y="{y + 4}" font-size="10" '
                f'text-anchor="end" fill="#78909c">beat {beat + 1}</text>'
            )

    for block in blocks:
        y = block["start"] * BEAT_PX + 2
        height = max(block["length"] * BEAT_PX - 4, 8)

        if block["in_range"]:
            x = positions[block["lane"]] + 4
            colour = THUMB_COLOURS[block["thumb"]]
            mark = _ROW_MARK.get(block["row"], "")
        else:
            x = LEFT_MARGIN + 4
            colour = OUT_OF_RANGE_COLOUR
            mark = "▼" if block["where"] == "below" else "▲"

        label = html.escape(block["note"]) + mark

        body.append(
            f'<rect x="{x}" y="{y}" width="{LANE_WIDTH - 8}" '
            f'height="{height}" rx="6" fill="{colour}"/>'
        )

        # A very short block has no room to read a name in.
        if height >= 16:
            body.append(
                f'<text x="{x + (LANE_WIDTH - 8) / 2}" y="{y + 13}" '
                f'font-size="10" text-anchor="middle" fill="#ffffff">'
                f'{label}</text>'
            )

        if block["lyric"]:
            body.append(
                f'<text x="{width + 12}" y="{y + 13}" font-size="12" '
                f'fill="#37474f">{html.escape(block["lyric"])}</text>'
            )

    body.append("</g></svg>")

    return (
        '<div class="melody-lanes" style="max-height:70vh;'
        'overflow-y:auto;border:1px solid var(--border-color-primary,#ccc);'
        'border-radius:8px">'
        '<div style="position:sticky;top:0;z-index:2">'
        + "".join(header)
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


# --- one view of the song ---------------------------------------

def melody_view(piece, instrument):
    """
    Everything one instrument tab shows for a piece (a phrase
    or the whole tune), as HTML: the out-of-range line if there
    is one, the lanes, and a one-line legend.
    """

    blocks = melody_blocks(piece, instrument)
    message = range_message(blocks, instrument)

    if not blocks:
        return "<p>No notes to show yet.</p>"

    warning = (
        f'<div style="color:{OUT_OF_RANGE_COLOUR};margin:4px 0">'
        f"{html.escape(message)}</div>" if message else ""
    )

    return (
        warning
        + lanes_html(blocks, instrument, piece.beats(), piece.chart)
        + f'<div style="font-size:0.85em;opacity:0.75;margin-top:4px">'
        f"{html.escape(LEGEND)}</div>"
    )


# --- which instruments have lanes -------------------------------

# Families the view can draw, as {family: [variants]}, taken
# from the one list of instruments (INSTRUMENTS).
SUPPORTED = ("Kalimba",)


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
                chart_text, phrase_label, instruments):
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
        "views": [melody_view(piece, name) for name in instruments],
        "status": status,
    }
