# fretted_tab.py

"""
The melody as guitar and ukulele tab: one line for each string,
time running across the page the way tab is read, a fret number
where each note falls. Stage 4 of PLAN-melody-lanes.md; the plan
is PLAN-fretted-tab.md.

A note can be played in several places on a neck, so a rule has
to choose. The rules are built in layers, each adding one idea to
the last, so a strange result can be traced to one layer:

    1. Nearest the nut: for every note, the lowest fret that
       plays it. Built.
    2. Stay in a position: one hand position per phrase.
       (Not built yet.)
    3. Smart shifting. (Parked, a later lever.)

Two halves, kept apart like melody_lanes.py:

    fretted_blocks(piece, instrument, fingering)  plain data
    tab_html(...)                                 the drawing

Plain Python, no interface. It is handed a Piece (already read
from the boxes) and never reads or writes the boxes itself.
"""

import html

from instrument_diagrams import (
    STRING_TUNINGS,
    _absolute_pitch,
    _base_instrument_name,
    _frets_shown_for,
)
from notes import is_rest


# --- the fingering choices --------------------------------------

NEAREST_NUT = "Nearest the nut"

FINGERINGS = [NEAREST_NUT]


# --- the instrument ---------------------------------------------

# What each string is called on the tab, in the order the tuning
# list is stored: the first is the bottom line of the tab, the
# last the top. The ukulele is re-entrant (its G is higher than
# its C), so lines are counted by where the string is, never by
# pitch.
STRING_NAMES = {
    "Guitar": ["low E", "A", "D", "G", "B", "high E"],
    "Ukulele": ["G", "C", "E", "A"],
}


def _open_pitches(instrument):
    base = _base_instrument_name(instrument)

    return [_absolute_pitch(note) for note in STRING_TUNINGS[base]]


def string_names(instrument):
    return STRING_NAMES[_base_instrument_name(instrument)]


def instrument_range(instrument):
    """
    (lowest, highest) pitch the neck can sound, each as
    {"pitch", "note"}. The lowest is the lowest string by pitch
    (the ukulele's C, not its G); the highest is the highest
    string's note at the last fret shown.
    """

    from melody_lanes import _name

    opens = _open_pitches(instrument)
    low = min(opens)
    high = max(opens) + _frets_shown_for(instrument)

    return (
        {"pitch": low, "note": _name(low)},
        {"pitch": high, "note": _name(high)},
    )


def candidates(pitch, instrument):
    """
    Every place a pitch can be played: [(string, fret)], lowest
    fret first, then the lower line first. String 0 is the bottom
    line of the tab. [] when no string reaches it.
    """

    reach = _frets_shown_for(instrument)
    places = [
        (string, pitch - open_pitch)
        for string, open_pitch in enumerate(_open_pitches(instrument))
        if 0 <= pitch - open_pitch <= reach
    ]

    return sorted(places, key=lambda place: (place[1], place[0]))


# --- the data ---------------------------------------------------

def _why(note, string, fret, instrument):
    name = string_names(instrument)[string]

    if fret == 0:
        return f"open {name} string - the nearest the nut there is"

    return (
        f"fret {fret} on the {name} string - the lowest fret "
        f"that plays {note}"
    )


def fretted_blocks(piece, instrument, fingering=NEAREST_NUT):
    """
    Every sounding note of the piece as one block:

        {"string", "fret", "start", "length", "note", "pitch",
         "lyric", "in_range", "where", "why"}

    start and length are in beats from the start of the piece
    handed in. string counts from the bottom line of the tab (0)
    and fret is 0 for an open string; both are None for a note
    the neck cannot play (in_range False, where "below" or
    "above"). note is the name as written in the boxes, without
    its octave. why says in a line how the place was chosen.
    Rests leave a gap and are not blocks.
    """

    if fingering != NEAREST_NUT:
        raise ValueError(f"No fingering called {fingering}.")

    from melody_lanes import _lyrics_per_note

    low, _high = instrument_range(instrument)
    starts = piece.starts()
    lyrics = _lyrics_per_note(piece)
    blocks = []

    for index, written in enumerate(piece.pitches):

        if is_rest(written):
            continue

        pitch = _absolute_pitch(written)
        places = candidates(pitch, instrument)
        note = written[:-1]

        if places:
            string, fret = places[0]
            where = None
            why = _why(note, string, fret, instrument)
        else:
            string = fret = None
            where = "below" if pitch < low["pitch"] else "above"
            why = f"{note} is {where} the neck"

        blocks.append({
            "string": string,
            "fret": fret,
            "start": starts[index],
            "length": piece.durations[index],
            "note": note,
            "pitch": pitch,
            "lyric": lyrics[index],
            "in_range": bool(places),
            "where": where,
            "why": why,
        })

    return blocks


def range_message(blocks, instrument):
    """
    In words, how many notes are off the neck and what would fix
    it; "" when every note is on it. Never moves a note.
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
            f"below the lowest string ({low['note']})"
        )

    if above:
        parts.append(
            f"{above} {'note is' if above == 1 else 'notes are'} "
            f"above the last fret shown ({high['note']})"
        )

    def fits_after(shift):
        return all(
            candidates(block["pitch"] + shift, instrument)
            for block in blocks
        )

    if fits_after(12):
        fix = "Octave up in the Song section would bring every note on."
    elif fits_after(-12):
        fix = "Octave down in the Song section would bring every note on."
    else:
        fix = (
            "No single octave shift brings every note on - the "
            "song is wider than this neck."
        )

    return (
        " and ".join(parts)
        + ". They are drawn in red on the top line. "
        + fix
    )


# --- the drawing ------------------------------------------------

MELODY_COLOUR = "#7b1fa2"
OUT_OF_RANGE_COLOUR = "#c62828"

BEAT_PX = 48
LINE_GAP = 26
LEFT_MARGIN = 62
RIGHT_MARGIN = 12
HEADING_HEIGHT = 20
LYRIC_HEIGHT = 26
ROW_GAP = 18

# A row of tab is never longer than this many beats.
BEATS_PER_ROW = 16


def row_starts(piece):
    """
    Where each row of tab begins, in beats: at the start of every
    phrase (the lyric lines; a rest between two belongs to the
    phrase it follows), so a row is a phrase and a change of hand
    position, when there is one, falls at a row break. A phrase
    longer than BEATS_PER_ROW is cut at the latest bar line that
    keeps the row within it (the chart's bars, else every four
    beats), or at the limit itself if there is no bar line to use.
    """

    starts = piece.starts()
    total = piece.beats()
    bars = sorted(_bar_starts(piece.chart, total))
    cuts = [starts[first] for first, _last in piece.phrases()] or [0.0]
    cuts[0] = 0.0

    rows = []

    for index, begin in enumerate(cuts):
        end = cuts[index + 1] if index + 1 < len(cuts) else total
        here = begin
        rows.append(here)

        while end - here > BEATS_PER_ROW + 0.001:
            usable = [
                bar for bar in bars
                if here + 0.001 < bar <= here + BEATS_PER_ROW + 0.001
            ]
            here = max(usable) if usable else here + BEATS_PER_ROW
            rows.append(here)

    return rows


def _bar_starts(chart_text, total_beats):
    """The chart's own bars, else every four beats."""

    from chords import read_chart

    try:
        _chords, bars = read_chart(chart_text or "")
    except ValueError:
        bars = []

    starts = [start for start, _length in bars if start < total_beats]

    if starts:
        return starts

    return [float(beat) for beat in range(0, int(total_beats) + 1, 4)]


def _row_spans(total_beats, starts):
    """[(first, last)] beats of each row. Without starts, rows of
    BEATS_PER_ROW from the beginning."""

    if not starts:
        count = max(1, -(-int(total_beats + 0.999) // BEATS_PER_ROW))
        starts = [row * BEATS_PER_ROW for row in range(count)]

    ends = list(starts[1:]) + [total_beats]

    return list(zip(starts, ends))


def tab_html(blocks, instrument, total_beats, chart_text="",
             starts=None):
    """
    The tab for one instrument as HTML: the strings as lines, the
    fret number of each note on its line, the words under each
    note. It wraps into rows that begin at `starts` (beats; see
    row_starts) - a row a phrase - or, without them, into rows of
    BEATS_PER_ROW beats. A note that cannot be played is a red
    block on a line of its own above the strings. total_beats is
    how long the stretch is.
    """

    import math

    names = string_names(instrument)
    count = len(names)
    spare = any(not block["in_range"] for block in blocks)
    spans = _row_spans(total_beats, starts)
    widest = max(last - first for first, last in spans)
    row_width = int(LEFT_MARGIN + widest * BEAT_PX + RIGHT_MARGIN)
    lines = count + (1 if spare else 0)
    row_height = (
        HEADING_HEIGHT + lines * LINE_GAP + LYRIC_HEIGHT + ROW_GAP
    )
    height = len(spans) * row_height

    bars = {round(start, 4) for start in _bar_starts(chart_text, total_beats)}
    row_firsts = [first for first, _last in spans]

    def line_y(row, string):
        """Centre of a string's line in a row; 0 is the bottom."""

        top = row * row_height + HEADING_HEIGHT
        up = count - 1 - string

        return top + (up + (1 if spare else 0)) * LINE_GAP + LINE_GAP / 2

    def off_y(row):
        return row * row_height + HEADING_HEIGHT + LINE_GAP / 2

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {row_width} {height}" width="100%" '
        f'role="img" aria-label="The melody as tab">'
    ]

    for row, (first, last) in enumerate(spans):
        right = LEFT_MARGIN + (last - first) * BEAT_PX

        # the strings, named at the left
        for string in range(count):
            y = line_y(row, string)
            parts.append(
                f'<line x1="{LEFT_MARGIN}" x2="{right}" y1="{y}" '
                f'y2="{y}" stroke="#90a4ae" stroke-width="1"/>'
                f'<text x="{LEFT_MARGIN - 8}" y="{y + 4}" font-size="10" '
                f'text-anchor="end" fill="#607d8b">'
                f'{html.escape(names[string])}</text>'
            )

        if spare:
            y = off_y(row)
            parts.append(
                f'<text x="{LEFT_MARGIN - 8}" y="{y + 4}" font-size="10" '
                f'text-anchor="end" fill="{OUT_OF_RANGE_COLOUR}">off</text>'
            )

        # the row's two ends, then bar lines and beat numbers
        top = row * row_height + HEADING_HEIGHT
        bottom = top + lines * LINE_GAP

        for x in (LEFT_MARGIN, right):
            parts.append(
                f'<line x1="{x}" x2="{x}" y1="{top}" y2="{bottom}" '
                f'stroke="#90a4ae" stroke-width="1.5"/>'
            )

        for beat in range(math.ceil(first - 0.001), int(last) + 1):
            x = LEFT_MARGIN + (beat - first) * BEAT_PX

            if float(beat) not in bars or not first < beat < last - 0.001:
                continue

            parts.append(
                f'<line x1="{x}" x2="{x}" y1="{top}" y2="{bottom}" '
                f'stroke="#90a4ae" stroke-width="1.5"/>'
                f'<text x="{x + 3}" y="{top - 6}" font-size="10" '
                f'fill="#78909c">{beat + 1}</text>'
            )

    for block in blocks:
        row = max(
            index for index, first in enumerate(row_firsts)
            if first <= block["start"] + 0.001
        )
        first, last = spans[row]
        x = LEFT_MARGIN + (block["start"] - first) * BEAT_PX
        room = LEFT_MARGIN + (last - first) * BEAT_PX - x
        width = max(min(block["length"] * BEAT_PX - 4, room), 18)

        if block["in_range"]:
            y = line_y(row, block["string"])
            colour = MELODY_COLOUR
            label = str(block["fret"])
        else:
            y = off_y(row)
            colour = OUT_OF_RANGE_COLOUR
            mark = "▼" if block["where"] == "below" else "▲"
            label = html.escape(block["note"]) + mark

        parts.append(
            f'<g><title>{html.escape(block["why"])}</title>'
            f'<rect x="{x}" y="{y - 10}" width="{width}" height="20" '
            f'rx="6" fill="{colour}"/>'
            f'<text x="{x + width / 2}" y="{y + 4}" font-size="11" '
            f'text-anchor="middle" fill="#ffffff">{label}</text></g>'
        )

        if block["lyric"]:
            lyric_y = (
                row * row_height + HEADING_HEIGHT + lines * LINE_GAP + 16
            )
            parts.append(
                f'<text x="{x}" y="{lyric_y}" font-size="12" '
                f'fill="#37474f">{html.escape(block["lyric"])}</text>'
            )

    parts.append("</svg>")

    # Natural size is the most it grows to: one beat is BEAT_PX
    # wide on a wide page, never stretched to fill it.
    return (
        f'<div class="melody-tab" style="max-width:{row_width + 10}px;'
        'max-height:70vh;overflow-y:auto;'
        'border:1px solid var(--border-color-primary,#ccc);'
        'border-radius:8px;padding:4px">'
        + "".join(parts)
        + "</div>"
    )


LEGEND = (
    "Tab: each line is a string, the number is the fret (0 is open), "
    "and the words are under each note. Time runs left to right, a "
    "row for each phrase (a long one is cut at a bar line). Nearest the nut: every note takes its "
    "lowest fret. A suggested fingering, not the only one - hover a "
    "note for why."
)

NOT_YET = (
    "Chords and the instrument picture are not on the tab yet."
)


def fretted_view(piece, instrument, fingering=NEAREST_NUT):
    """
    Everything a guitar or ukulele tab shows for a piece: the
    line about notes off the neck if there is one, the tab, and a
    legend.
    """

    blocks = fretted_blocks(piece, instrument, fingering)

    if not blocks:
        return "<p>No notes to show yet.</p>"

    message = range_message(blocks, instrument)
    warning = (
        f'<div style="color:{OUT_OF_RANGE_COLOUR};margin:4px 0">'
        f"{html.escape(message)}</div>" if message else ""
    )

    return (
        warning
        + tab_html(
            blocks, instrument, piece.beats(), piece.chart,
            row_starts(piece)
        )
        + '<div style="font-size:0.85em;opacity:0.75;margin-top:4px">'
        + html.escape(LEGEND + " " + NOT_YET)
        + "</div>"
    )
