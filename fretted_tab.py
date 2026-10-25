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
    2. Stay in a position: notes are grouped, in advance and over
       the whole tune, into hand positions no wider than a chosen
       number of frets (open strings are free by default), with
       the fewest changes of position, cut at a rest, bar line or
       phrase end where possible. Built.
    3. Smart shifting. (Parked, a later lever.)

Two halves, kept apart like melody_lanes.py:

    fretted_blocks(piece, instrument, fingering)  plain data
    tab_html(...)                                 the drawing

Plain Python, no interface. It is handed a Piece (already read
from the boxes) and never reads or writes the boxes itself.
"""

import html

from instrument_diagrams import (
    CHORD_TONE_COLOUR,
    STRING_TUNINGS,
    _absolute_pitch,
    _base_instrument_name,
    _frets_shown_for,
    guitar_shape_frets,
    ukulele_shape_frets,
)
from notes import is_rest


# --- the fingering choices --------------------------------------

NEAREST_NUT = "Nearest the nut"
STAY_IN_POSITION = "Stay in a position"

FINGERINGS = [NEAREST_NUT, STAY_IN_POSITION]

# How many frets a hand position spans (the span a hand covers
# without moving), and the choices offered. Matthew's idea: a
# width the player can change.
DEFAULT_WIDTH = 5
WIDTHS = [4, 5, 6, 7, 8]


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


def _position_masks(places_list, width, reach, open_free):
    """
    For each note, which windows it fits, as a bit mask: bit lo is
    set when the window of `width` frets starting at fret lo
    (lo = 0 is the open position) holds one of the note's places.
    A note with an open-string place fits every window when open
    strings are free.
    """

    everywhere = (1 << (reach + 1)) - 1
    masks = []

    for places in places_list:
        mask = 0

        for _string, fret in places:
            if fret == 0 and open_free:
                mask = everywhere
                break

            for lo in range(max(0, fret - width + 1), min(fret, reach) + 1):
                mask |= 1 << lo

        masks.append(mask)

    return masks


def _group_notes(masks, natural_cut, prefer_low=False):
    """
    Split the notes (in order) into the fewest runs that each fit
    one window, looking at the whole tune first: among the splits
    with the fewest runs, the fewest cuts at an unnatural place
    (natural_cut[k] says a cut before note k is at a rest, a bar
    line or a phrase start), then the most even runs (smallest sum
    of squared sizes). Returns [(first, last)] note indexes. The
    same input always gives the same answer.

    prefer_low changes the ranking (the caller then passes cuts
    that are phrase starts only): fewest cuts away from a phrase
    start, then the lowest frets - each run's window is the lowest
    one that holds all its notes, and the splits are ranked by the
    total of those windows' lowest frets, counted once per note -
    then fewest runs, then the most even. So the position may change
    at every phrase, to keep to lower frets, but nowhere else unless
    a phrase cannot be held in one position.
    """

    count = len(masks)
    best = [None] * (count + 1)
    best[0] = ((0, 0, 0, 0), None)

    for first in range(count):
        if best[first] is None:
            continue

        cost_before = best[first][0]
        run = None

        for last in range(first, count):
            run = masks[last] if run is None else run & masks[last]

            if not run:
                break

            size = last - first + 1
            low = (run & -run).bit_length() - 1
            unnatural = 0 if first == 0 or natural_cut[first] else 1

            if prefer_low:
                cost = (
                    cost_before[0] + unnatural,
                    cost_before[1] + low * size,
                    cost_before[2] + 1,
                    cost_before[3] + size * size,
                )
            else:
                cost = (
                    cost_before[0] + 1,
                    cost_before[1] + unnatural,
                    0,
                    cost_before[3] + size * size,
                )

            if best[last + 1] is None or cost < best[last + 1][0]:
                best[last + 1] = (cost, first)

    groups = []
    end = count

    while end > 0:
        first = best[end][1]
        groups.append((first, end - 1))
        end = first

    return list(reversed(groups))


def _natural_cuts(grouped, piece, phrases_only=False):
    """
    For each grouped note, whether a cut just before it is at a
    natural pause: after a rest, on a bar line, or at the start of
    a phrase.
    """

    starts = piece.starts()
    phrase_starts = {
        round(starts[first], 3) for first, _last in piece.phrases()
    }
    bars = {
        round(bar, 3)
        for bar in _bar_starts(piece.chart, piece.beats())
    }
    cuts = []
    previous_end = None

    for block in grouped:
        start = round(block["start"], 3)
        after_rest = (
            previous_end is not None and start > previous_end + 0.001
        )

        if phrases_only:
            cuts.append(start in phrase_starts)
        else:
            cuts.append(
                after_rest or start in phrase_starts or start in bars
            )
        previous_end = block["start"] + block["length"]

    return cuts


def _place_in_positions(blocks, places_list, instrument, piece, width,
                        open_free, prefer_low=False):
    """
    Layer 2: give each playable block a place inside a hand
    position. Fills in string, fret, why, segment and position on
    the blocks that have a place.
    """

    reach = _frets_shown_for(instrument)
    width = max(1, min(int(width), reach))
    playable = [i for i, block in enumerate(blocks) if block["in_range"]]

    if not playable:
        return

    grouped = [blocks[i] for i in playable]
    places = [places_list[i] for i in playable]
    masks = _position_masks(places, width, reach, open_free)
    groups = _group_notes(
        masks, _natural_cuts(grouped, piece, prefer_low), prefer_low
    )

    for number, (first, last) in enumerate(groups):
        window = -1

        run = masks[first]
        for index in range(first + 1, last + 1):
            run &= masks[index]

        lo = (run & -run).bit_length() - 1
        window = lo
        used = []

        for index in range(first, last + 1):
            block = grouped[index]
            fits = [
                (fret, string) for string, fret in places[index]
                if (fret == 0 and open_free) or lo <= fret <= lo + width - 1
            ]
            fret, string = min(fits)
            note = block["note"]
            block["string"] = string
            block["fret"] = fret
            block["segment"] = number
            used.append(fret)
            block["why"] = _why_in_position(
                note, string, fret, lo, width, instrument, open_free,
                prefer_low
            )

        fretted = [fret for fret in used if fret > 0]
        label = min(fretted) if fretted else None

        for index in range(first, last + 1):
            grouped[index]["position"] = label


def _why_in_position(note, string, fret, lo, width, instrument, open_free,
                     prefer_low=False):
    text = _why_in_position_text(
        note, string, fret, lo, width, instrument, open_free
    )

    return text + (
        "; Prefer lower positions is on, so this position is the "
        "lowest that holds its phrase" if prefer_low else ""
    )


def _why_in_position_text(note, string, fret, lo, width, instrument,
                          open_free):
    name = string_names(instrument)[string]
    span = f"frets {lo} to {lo + width - 1}"

    if fret == 0:
        return (
            f"open {name} string - open strings are free, so they "
            f"do not count toward the {width}-fret width"
            if open_free else
            f"open {name} string - inside the {span} position"
        )

    return (
        f"fret {fret} on the {name} string - the lowest fret that "
        f"plays {note} inside the {span} position"
    )


def fretted_blocks(piece, instrument, fingering=NEAREST_NUT,
                   width=DEFAULT_WIDTH, open_free=True,
                   prefer_low=False):
    """
    Every sounding note of the piece as one block:

        {"string", "fret", "start", "length", "note", "pitch",
         "lyric", "in_range", "where", "why", "segment", "position"}

    start and length are in beats from the start of the piece
    handed in. string counts from the bottom line of the tab (0)
    and fret is 0 for an open string; both are None for a note
    the neck cannot play (in_range False, where "below" or
    "above"). note is the name as written in the boxes, without
    its octave. why says in a line how the place was chosen.
    Rests leave a gap and are not blocks.

    fingering is NEAREST_NUT (the lowest fret for every note) or
    STAY_IN_POSITION, which groups the notes into hand positions
    of at most `width` frets (open strings are free unless
    open_free is False). segment numbers the position a note is
    in and position is its lowest fretted fret (None for an open-
    strings-only group); both are None for NEAREST_NUT and for
    notes off the neck.
    """

    if fingering not in FINGERINGS:
        raise ValueError(f"No fingering called {fingering}.")

    from melody_lanes import _lyrics_per_note

    low, _high = instrument_range(instrument)
    starts = piece.starts()
    lyrics = _lyrics_per_note(piece)
    blocks = []
    places_list = []

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

        places_list.append(places)
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
            "segment": None,
            "position": None,
        })

    if fingering == STAY_IN_POSITION:
        _place_in_positions(
            blocks, places_list, instrument, piece, width, open_free,
            prefer_low
        )

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

# With hand positions shown, the heading also holds a bracket and
# its label above the beat numbers.
HEADING_HEIGHT_WITH_POSITIONS = 46

# With chords shown the heading also holds each chord's name and a
# small chord box (the kind chord charts and Guitar Pro use).
CHORD_BLOCK_HEIGHT = 78
CHORD_BOX_WIDTH = 44
POSITION_COLOUR = "#00796b"
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


# --- the chords: names with small chord boxes -------------------

def chord_shape(name, instrument):
    """
    The beginner's shape the chord sheet uses for a chord on this
    instrument, as {"frets": [fret or None for each string in the
    tuning order, None being muted], "fingers": [...], "barre":
    fret or None}; None when there is no standard shape for it (or
    the name is not a chord the app knows).
    """

    from chords import split_chord

    try:
        root, quality = split_chord(name)
    except ValueError:
        return None

    base = _base_instrument_name(instrument)
    found = (
        ukulele_shape_frets(root, quality) if base == "Ukulele"
        else guitar_shape_frets(root, quality)
    )

    if found is None:
        return None

    strings, barre = found

    return {
        "frets": [fret for fret, _finger in strings],
        "fingers": [finger for _fret, finger in strings],
        "barre": barre,
    }


def chord_box_svg(shape, x, y):
    """
    A small chord box with its top-left corner at (x, y): the
    strings upright (the first string of the tuning on the left),
    four frets, a dot where a finger goes (with its finger number
    when it is known), a bar for a barre, an open ring above an
    open string and a cross above a muted one. A shape up the neck
    starts at its lowest fret and says which. Elements carry
    classes (chord-dot, chord-open, chord-mute, chord-barre) so
    they can be told apart.
    """

    frets = shape["frets"]
    count = len(frets)
    pressed = [fret for fret in frets if fret]
    first = 1 if not pressed or max(pressed) <= 4 else min(pressed)
    left, top = 6, 12
    gap = (CHORD_BOX_WIDTH - 2 * left) / (count - 1)
    fret_gap = 10
    rows = 4
    bottom = top + rows * fret_gap
    colour = CHORD_TONE_COLOUR

    def string_x(index):
        return x + left + index * gap

    def fret_y(fret):
        return y + top + (fret - first + 0.5) * fret_gap

    parts = [f'<g class="chord-box">']

    # the frets (the nut thick when the box starts at the first fret)
    for line in range(rows + 1):
        thick = line == 0 and first == 1
        parts.append(
            f'<line x1="{string_x(0)}" x2="{string_x(count - 1)}" '
            f'y1="{y + top + line * fret_gap}" '
            f'y2="{y + top + line * fret_gap}" stroke="#78909c" '
            f'stroke-width="{2.5 if thick else 0.8}"/>'
        )

    # the strings
    for index in range(count):
        parts.append(
            f'<line x1="{string_x(index)}" x2="{string_x(index)}" '
            f'y1="{y + top}" y2="{y + bottom}" stroke="#78909c" '
            f'stroke-width="0.8"/>'
        )

    # the bar of a barre, under the dots
    if shape["barre"] and first <= shape["barre"] <= first + rows - 1:
        covered = [
            index for index, fret in enumerate(frets)
            if fret == shape["barre"]
        ]
        parts.append(
            f'<rect class="chord-barre" x="{string_x(min(covered)) - 3.5}" '
            f'y="{fret_y(shape["barre"]) - 3.5}" '
            f'width="{string_x(max(covered)) - string_x(min(covered)) + 7}" '
            f'height="7" rx="3.5" fill="{colour}"/>'
        )

    for index, fret in enumerate(frets):
        sx = string_x(index)

        if fret is None:
            parts.append(
                f'<text class="chord-mute" x="{sx}" y="{y + top - 3}" '
                f'font-size="8" text-anchor="middle" fill="#607d8b">'
                f'x</text>'
            )
        elif fret == 0:
            parts.append(
                f'<circle class="chord-open" cx="{sx}" '
                f'cy="{y + top - 6}" r="2.3" fill="none" '
                f'stroke="#607d8b" stroke-width="0.9"/>'
            )
        else:
            parts.append(
                f'<circle class="chord-dot" cx="{sx}" cy="{fret_y(fret)}" '
                f'r="3.6" fill="{colour}"/>'
            )

            if shape["fingers"][index]:
                parts.append(
                    f'<text x="{sx}" y="{fret_y(fret) + 2.4}" '
                    f'font-size="6.5" text-anchor="middle" '
                    f'fill="#ffffff">{shape["fingers"][index]}</text>'
                )

    if first > 1:
        parts.append(
            f'<text class="chord-base" x="{string_x(count - 1) + 4}" '
            f'y="{fret_y(first) + 2.5}" font-size="7" fill="#607d8b">'
            f'{first}fr</text>'
        )

    parts.append("</g>")

    return "".join(parts)


def chord_layer(piece, instrument):
    """
    The chart's chords for the tab: [{"start", "length", "name",
    "shape"}], shape None where the chord has no standard shape.
    """

    from melody_lanes import chord_spans

    return [
        {**span, "shape": chord_shape(span["name"], instrument)}
        for span in chord_spans(piece)
    ]


def _row_spans(total_beats, starts):
    """[(first, last)] beats of each row. Without starts, rows of
    BEATS_PER_ROW from the beginning."""

    if not starts:
        count = max(1, -(-int(total_beats + 0.999) // BEATS_PER_ROW))
        starts = [row * BEATS_PER_ROW for row in range(count)]

    ends = list(starts[1:]) + [total_beats]

    return list(zip(starts, ends))


def tab_html(blocks, instrument, total_beats, chart_text="",
             starts=None, chords=None):
    """
    The tab for one instrument as HTML: the strings as lines, the
    fret number of each note on its line, the words under each
    note. It wraps into rows that begin at `starts` (beats; see
    row_starts) - a row a phrase - or, without them, into rows of
    BEATS_PER_ROW beats. A note that cannot be played is a red
    block on a line of its own above the strings. total_beats is
    how long the stretch is.

    chords (see chord_layer) puts each chord's name above the tab
    where it starts, with its small chord box when the chord lasts
    long enough to leave room for one (a beat); a chord of half a
    beat gets its name alone and a shorter one only a tick.
    """

    import math

    names = string_names(instrument)
    count = len(names)
    spare = any(not block["in_range"] for block in blocks)
    positioned = any(block["segment"] is not None for block in blocks)
    chords = chords or []
    heading = (
        HEADING_HEIGHT_WITH_POSITIONS if positioned else HEADING_HEIGHT
    ) + (CHORD_BLOCK_HEIGHT if chords else 0)
    spans = _row_spans(total_beats, starts)
    widest = max(last - first for first, last in spans)
    row_width = int(LEFT_MARGIN + widest * BEAT_PX + RIGHT_MARGIN)
    lines = count + (1 if spare else 0)
    row_height = (
        heading + lines * LINE_GAP + LYRIC_HEIGHT + ROW_GAP
    )
    height = len(spans) * row_height

    bars = {round(start, 4) for start in _bar_starts(chart_text, total_beats)}
    row_firsts = [first for first, _last in spans]

    def line_y(row, string):
        """Centre of a string's line in a row; 0 is the bottom."""

        top = row * row_height + heading
        up = count - 1 - string

        return top + (up + (1 if spare else 0)) * LINE_GAP + LINE_GAP / 2

    def off_y(row):
        return row * row_height + heading + LINE_GAP / 2

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
        top = row * row_height + heading
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
                f'<text x="{x + 3}" y="{row * row_height + 14}" '
                f'font-size="10" '
                f'fill="#78909c">{beat + 1}</text>'
            )

    # The chords, above each row.
    for chord in chords:
        row = max(
            index for index, first in enumerate(row_firsts)
            if first <= chord["start"] + 0.001
        )
        first, last = spans[row]
        x = LEFT_MARGIN + (chord["start"] - first) * BEAT_PX
        room = chord["length"] * BEAT_PX
        y = row * row_height + 20
        name = html.escape(chord["name"])

        parts.append(
            f'<line x1="{x}" x2="{x}" y1="{y}" y2="{y + 8}" '
            f'stroke="{CHORD_TONE_COLOUR}" stroke-width="1.5"/>'
        )

        if room < 24:
            continue

        parts.append(
            f'<text class="chord-name" x="{x + 3}" y="{y + 11}" '
            f'font-size="12" font-weight="600" '
            f'fill="{CHORD_TONE_COLOUR}">{name}</text>'
        )

        if chord["shape"] is not None and room >= CHORD_BOX_WIDTH:
            parts.append(chord_box_svg(chord["shape"], x + 2, y + 14))

    # A bracket and a label over each stretch of notes in one hand
    # position, row by row.
    if positioned:
        pieces = {}

        for block in blocks:
            if block["segment"] is None:
                continue

            row = max(
                index for index, first in enumerate(row_firsts)
                if first <= block["start"] + 0.001
            )
            key = (block["segment"], row)
            first, last = spans[row]
            begin = LEFT_MARGIN + (block["start"] - first) * BEAT_PX
            end = min(
                begin + block["length"] * BEAT_PX - 4,
                LEFT_MARGIN + (last - first) * BEAT_PX,
            )
            low, high = pieces.get(key, (begin, end))
            pieces[key] = (min(low, begin), max(high, end))

        labels = {
            block["segment"]: block["position"]
            for block in blocks if block["segment"] is not None
        }

        for (segment, row), (begin, end) in sorted(pieces.items()):
            top = row * row_height + heading
            y = top - 12
            fret = labels[segment]
            text = "open strings" if fret is None else f"fret {fret} position"

            parts.append(
                f'<path d="M{begin} {y + 5} V{y} H{end} V{y + 5}" '
                f'fill="none" stroke="{POSITION_COLOUR}" '
                f'stroke-width="1.5"/>'
                f'<text x="{begin + 2}" y="{y - 4}" font-size="10" '
                f'font-weight="600" fill="{POSITION_COLOUR}">{text}</text>'
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
                row * row_height + heading + lines * LINE_GAP + 16
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
    "row for each phrase (a long one is cut at a bar line). A "
    "suggested fingering, not the only one - hover a note for why."
)

LEGEND_NUT = " Nearest the nut: every note takes its lowest fret."

LEGEND_POSITION = (
    " Stay in a position: the green brackets are hand positions, "
    "each at most {width} frets wide, as few as the tune allows and "
    "changing at a pause where it can. {open}"
)

LEGEND_LOW = (
    " Prefer lower positions is on: the position may change at each "
    "phrase, and each is the lowest that holds the phrase, so the "
    "hand sits lower on the neck but moves more than with it off."
)

LEGEND_CHORDS = (
    "Chord names are over the tab where each chord starts, with a "
    "small chord box (open ring, cross for a string not played, "
    "dots for fingers)."
)


def fretted_view(piece, instrument, fingering=NEAREST_NUT,
                 width=DEFAULT_WIDTH, open_free=True, show=None,
                 prefer_low=False):
    """
    Everything a guitar or ukulele tab shows for a piece: the
    line about notes off the neck if there is one, the tab, and a
    legend.
    """

    show = ["Melody", "Chords"] if show is None else list(show)
    want_chords = "Chords" in show
    want_melody = "Melody" in show or not want_chords

    all_blocks = fretted_blocks(
        piece, instrument, fingering, width, open_free, prefer_low
    )

    if not all_blocks:
        return "<p>No notes to show yet.</p>"

    blocks = all_blocks if want_melody else []
    chords = chord_layer(piece, instrument) if want_chords else []
    message = range_message(blocks, instrument) if blocks else ""
    warning = (
        f'<div style="color:{OUT_OF_RANGE_COLOUR};margin:4px 0">'
        f"{html.escape(message)}</div>" if message else ""
    )

    if not blocks:
        legend = ""
    elif fingering == STAY_IN_POSITION:
        shown = max(1, min(int(width), _frets_shown_for(instrument)))
        legend = LEGEND + LEGEND_POSITION.format(
            width=shown,
            open=(
                "Open strings are free: they do not count toward the "
                "width." if open_free else
                "Open strings count toward the width."
            ),
        ) + (LEGEND_LOW if prefer_low else "")
    else:
        legend = LEGEND + LEGEND_NUT

    return (
        warning
        + tab_html(
            blocks, instrument, piece.beats(), piece.chart,
            row_starts(piece), chords
        )
        + '<div style="font-size:0.85em;opacity:0.75;margin-top:4px">'
        + html.escape(
            (legend + " " + (LEGEND_CHORDS if chords else "")).strip()
        )
        + "</div>"
    )
