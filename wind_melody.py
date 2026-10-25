# wind_melody.py

"""
The melody on a flute or an alto sax: one small fingering chart per
note, a row for every phrase, left to right, for looking over before
you play (PLAN-wind-melody.md).

A wind instrument has no place per note - a note is a whole hand
shape - so the lanes that suit the kalimba, harp and piano do not
suit it. This is the other renderer over the same song.

Two halves, kept apart like melody_lanes.py:

    wind_blocks(piece, instrument)   plain data: every note with its
        written pitch, its chord role and its fingering. No drawing.
    wind_rows(...)                   the notes cut into phrase rows,
        with the chord tones each row leaves out.
    wind_view(...)                   the page, from those.

Plain Python, no interface, no boxes: it is handed a Piece and
never reads or writes the boxes (DESIGN.md invariant 1).

Pitch numbers count semitones with C0 = 0, so C4 = 48 - the
convention of the rest of the code.

The fingerings are data in wind_fingerings.py, not code. A note
with no entry there draws a grey "no fingering yet" chart: the view
never guesses a fingering.
"""

import html

from chords import chord_at, chord_semitones, chord_spellings
from fretted_tab import row_starts
from instrument_diagrams import (
    CHORD_TONE_COLOUR,
    LEFT_HAND_COLOUR,
    RIGHT_HAND_COLOUR,
    _absolute_pitch,
)
from melody_lanes import (
    OCTAVE_COLOUR,
    OCTAVE_TEXT_COLOUR,
    SHOW_CHORDS,
    SHOW_MELODY,
    DEFAULT_SHOW,
    chord_spans,
)
from notes import FLAT_KEYS, is_rest

import wind_fingerings


# --- the instruments --------------------------------------------

from wind_fingerings import WINDS

# Semitones from the sounding pitch (what the boxes hold, and what
# the chord sheet uses) to the written pitch the player reads and
# fingers. The flute sounds as written. An E-flat alto sax reads a
# major sixth above what sounds.
TRANSPOSE = {"Flute": 0, "Alto sax": 9}

# The written range each can finger, low to high, as pitch numbers:
# the flute C4 to C7 (concert pitch); the alto sax low B-flat to
# high F-sharp (written B-flat 3 to F-sharp 6).
WRITTEN_RANGE = {"Flute": (48, 96), "Alto sax": (46, 78)}

# The alto's written key for each major key it sounds in: the key
# a major sixth up. Anything not listed (a minor key, say) is
# spelled with sharps.
ALTO_WRITTEN_KEY = {
    "C": "A", "G": "E", "D": "B", "A": "F#", "E": "C#", "B": "G#",
    "F#": "D#", "F": "D", "Bb": "G", "Eb": "C", "Ab": "F", "Db": "Bb",
}

_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]


def transposition(instrument):
    return TRANSPOSE[instrument]


def written_key(key, instrument):
    """The key the player reads, named as a key box would."""

    if instrument == "Alto sax":
        return ALTO_WRITTEN_KEY.get(key)

    return key


def spell(pitch, key=None):
    """A pitch number as a note name with its octave: 62 -> D5."""

    names = _FLAT if key in FLAT_KEYS else _SHARP

    return names[pitch % 12] + str(pitch // 12)


# --- the chord a note belongs to --------------------------------

# What each interval above a chord's root is called on a chart.
_ROLES = {
    0: "R", 2: "2", 3: "3", 4: "3", 5: "4",
    6: "5", 7: "5", 8: "5", 9: "6", 10: "7", 11: "7",
}


def chord_roles(name):
    """
    {pitch class: role} for a chord, roles being R, 3, 5, 7 and so
    on: F gives {5: "R", 9: "3", 0: "5"}. Roles are a chord's own
    business and do not depend on the key.
    """

    tones = chord_semitones(name)
    root = tones[0]

    return {
        pitch_class: _ROLES[(pitch_class - root) % 12]
        for pitch_class in tones
    }


def _chord_tuples(piece):
    return [
        (span["start"], span["length"], span["name"])
        for span in chord_spans(piece)
    ]


# --- the data ---------------------------------------------------

def _lyrics_per_note(piece):
    from melody_lanes import _lyrics_per_note as lyrics

    return lyrics(piece)


def _fit(written, low, high):
    """
    (written pitch, octaves moved): a written pitch the instrument
    cannot finger goes to the nearest octave it can (up from below,
    down from above). +1 is one octave up.
    """

    shift = 0

    while written < low and shift < 8:
        written += 12
        shift += 1

    while written > high and shift > -8:
        written -= 12
        shift -= 1

    return written, shift


def wind_blocks(piece, instrument, table=None):
    """
    Every sounding note of the piece as one block:

        {"start", "length", "note", "concert", "pitch",
         "written_pitch", "shift", "lyric", "chord", "role",
         "keys", "tag", "in_range"}

    start and length are beats from the start of the piece. note
    is the name the player reads (written pitch, with its octave);
    concert is the sounding name, or None where it is the same
    (the flute). pitch is the sounding pitch actually played and
    written_pitch what is fingered: a note outside the instrument
    is moved by whole octaves, nearest first, and shift says how
    many (+1 up). chord is the chord the note begins under and
    role its place in it (R, 3, 5, 7...), None for a passing note
    or when there is no chart. keys is the list of keys pressed, or
    None when the table has no fingering for the note; tag is the
    table's own remark ("thumb B-flat", say).

    table is the fingering table (tests pass their own); by
    default it is wind_fingerings.FINGERINGS.
    """

    if instrument not in WINDS:
        raise ValueError(f"No wind view for {instrument}.")

    table = wind_fingerings.FINGERINGS if table is None else table
    fingerings = table.get(instrument, {})
    low, high = WRITTEN_RANGE[instrument]
    shift_by = TRANSPOSE[instrument]
    starts = piece.starts()
    lyrics = _lyrics_per_note(piece)
    chords = _chord_tuples(piece)
    blocks = []

    for index, boxed in enumerate(piece.pitches):

        if is_rest(boxed):
            continue

        sounding = _absolute_pitch(boxed)
        written, shift = _fit(sounding + shift_by, low, high)
        played = written - shift_by
        key = piece.key_at(starts[index])
        read_key = written_key(key, instrument)

        chord = chord_at(chords, starts[index])
        role = (
            chord_roles(chord).get(sounding % 12) if chord else None
        )

        found = fingerings.get(written)

        blocks.append({
            "start": starts[index],
            "length": piece.durations[index],
            "note": spell(written, read_key),
            "concert": (
                spell(played, key) if shift_by else None
            ),
            "pitch": played,
            "written_pitch": written,
            "shift": shift,
            "lyric": lyrics[index],
            "chord": chord,
            "role": role,
            "keys": list(found["keys"]) if found else None,
            "tag": found.get("tag", "") if found else "",
            "in_range": low <= written <= high,
        })

    return blocks


def keys_changed(before, after):
    """
    How many keys differ between two fingerings; None if either
    is unknown. A key down in one and up in the other counts once.
    """

    if before is None or after is None:
        return None

    return len(set(before) ^ set(after))


# --- the rows ---------------------------------------------------

def _row_edges(piece):
    cuts = row_starts(piece)

    return list(zip(cuts, cuts[1:] + [piece.beats()]))


def _missing_tones(piece, instrument, blocks, begin, end, table):
    """
    The chord tones a row leaves out, per chord, as
    [{"chord", "tones": [{"role", "note", "keys", "tag", "pitch",
    "written_pitch"}]}]. A tone is left out when no note of the row,
    sounding under that chord, has its pitch class. Each is shown at
    the octave nearest the row's own notes.
    """

    chords = _chord_tuples(piece)
    inside = [b for b in blocks if begin <= b["start"] < end]
    out = []
    seen = set()

    for start, length, name in chords:
        lo, hi = max(start, begin), min(start + length, end)

        if lo >= hi or name in seen:
            continue

        under = [b for b in inside if lo <= b["start"] < hi]
        heard = {b["pitch"] % 12 for b in under}
        centre = (
            sum(b["pitch"] for b in under) / len(under) if under
            else sum(b["pitch"] for b in inside) / len(inside)
            if inside else 60
        )
        roles = chord_roles(name)
        spellings = chord_spellings(name)
        tones = []

        for pitch_class in chord_semitones(name):

            if pitch_class in heard:
                continue

            # The octave of this pitch class nearest the row's notes.
            nearest = min(
                (p for p in range(24, 100) if p % 12 == pitch_class),
                key=lambda p: (abs(p - centre), p),
            )
            written, _shift = _fit(
                nearest + TRANSPOSE[instrument],
                *WRITTEN_RANGE[instrument]
            )
            found = table.get(instrument, {}).get(written)

            tones.append({
                "role": roles[pitch_class],
                "chord_note": spellings[pitch_class],
                "note": spell(written),
                "keys": list(found["keys"]) if found else None,
                "tag": found.get("tag", "") if found else "",
                "pitch": written - TRANSPOSE[instrument],
                "written_pitch": written,
            })

        seen.add(name)

        if tones:
            out.append({"chord": name, "tones": tones})

    return out


def wind_rows(piece, instrument, table=None):
    """
    The piece as phrase rows: [{"start", "end", "blocks", "chord",
    "missing"}]. chord is the chord the row opens under (None
    without a chart) and missing the chord tones the row leaves
    out (see _missing_tones). A repeated phrase is not folded here:
    the page does that, because it is a view choice.
    """

    table = wind_fingerings.FINGERINGS if table is None else table
    blocks = wind_blocks(piece, instrument, table)
    chords = _chord_tuples(piece)
    rows = []

    for begin, end in _row_edges(piece):
        inside = [b for b in blocks if begin <= b["start"] < end]

        rows.append({
            "start": begin,
            "end": end,
            "blocks": inside,
            "chord": chord_at(chords, begin),
            "missing": (
                _missing_tones(piece, instrument, blocks, begin, end, table)
                if chords else []
            ),
        })

    return rows


def same_row(a, b):
    """Whether two rows play the same notes under the same chords."""

    def signature(row):
        return [
            (blk["written_pitch"], blk["length"], blk["chord"])
            for blk in row["blocks"]
        ]

    return bool(a["blocks"]) and signature(a) == signature(b)


def fold_repeats(rows):
    """
    Rows with a row identical to the one before it folded into
    it: each kept row gains "times" (1 for a row on its own) and
    "last" (the end of the last row it stands for).
    """

    folded = []

    for row in rows:

        if folded and same_row(folded[-1], row):
            folded[-1]["times"] += 1
            folded[-1]["last"] = row["end"]
            continue

        folded.append(dict(row, times=1, last=row["end"]))

    return folded


# --- the drawing ------------------------------------------------

CHART_SCALE = 0.72
CHART_WIDTH = 44
CHART_HEIGHT = 100

# A pill appears when this many keys or more change from the note
# before.
BIG_CHANGE = 4

BEAT_PX = 76
MIN_CELL = 60

PASSING_FILL = "#f3f4f6"
ROLE_FILL = "#fdf2f8"
UNKNOWN_COLOUR = "#9ca3af"
NO_FINGERING_TEXT = "no fingering yet"
ROW_BORDER = "#e5e7eb"


def _key_geometry(instrument):
    return wind_fingerings.KEY_LAYOUT[instrument]


def _chart_html(keys, instrument, scale=CHART_SCALE):
    """
    One fingering chart: a ring for every key, filled where it is
    pressed. keys None draws the grey "no fingering yet" box.
    """

    width, height = CHART_WIDTH * scale, CHART_HEIGHT * scale

    if keys is None:
        return (
            f'<div class="wind-chart wind-unknown" '
            f'style="width:{width:g}px;height:{height:g}px;'
            f'box-sizing:border-box;border:1.5px dashed {UNKNOWN_COLOUR};'
            f"border-radius:6px;display:flex;align-items:center;"
            f'justify-content:center;text-align:center;font-size:9px;'
            f'line-height:1.1;color:{UNKNOWN_COLOUR}">'
            f"{NO_FINGERING_TEXT}</div>"
        )

    parts = [
        f'<div class="wind-chart" style="position:relative;'
        f'width:{width:g}px;height:{height:g}px">'
    ]

    for key in _key_geometry(instrument):
        x, y, w, h, shape, colour = (
            key["x"], key["y"], key["w"], key["h"], key["shape"],
            key["colour"],
        )
        pressed = key["id"] in keys
        radius = "50%" if shape == "round" else "4px"
        fill = colour if pressed else "#ffffff"
        edge = colour if pressed else UNKNOWN_COLOUR
        parts.append(
            f'<div class="wind-key{" wind-down" if pressed else ""}" '
            f'data-key="{key["id"]}" style="position:absolute;'
            f"left:{x * scale:g}px;top:{y * scale:g}px;"
            f"width:{w * scale:g}px;height:{h * scale:g}px;"
            f"box-sizing:border-box;border-radius:{radius};"
            f'border:1.5px solid {edge};background:{fill}"></div>'
        )

    parts.append("</div>")

    return "".join(parts)


def _key_names(instrument, keys):
    names = {k["id"]: k["name"] for k in _key_geometry(instrument)}

    return ", ".join(names[k] for k in keys if k in names)


def _cell_html(block, instrument, previous, show_roles):
    """One note: its chart in a ring, name, concert name, syllable."""

    role = block["role"] if show_roles else None
    width = max(MIN_CELL, block["length"] * BEAT_PX)
    moved = keys_changed(
        previous["keys"] if previous else None, block["keys"]
    )
    pill = ""

    if moved is not None and moved >= BIG_CHANGE:
        pill = (
            f'<span class="wind-change" style="font-size:10px;'
            f"font-weight:600;color:#92400e;background:#fef3c7;"
            f'border-radius:8px;padding:0 6px;height:16px;'
            f'line-height:16px">{moved} keys</span>'
        )

    elif block["shift"]:
        # Moved to another octave: the same amber as the lanes.
        arrow = "▲" if block["shift"] > 0 else "▼"
        times = abs(block["shift"]) * 8
        pill = (
            f'<span class="wind-8va" style="font-size:10px;'
            f"font-weight:700;color:{OCTAVE_TEXT_COLOUR};"
            f"background:{OCTAVE_COLOUR};border-radius:8px;"
            f'padding:0 6px;height:16px;line-height:16px">'
            f"{arrow} {times}va</span>"
        )

    ring = CHORD_TONE_COLOUR if role else "#ffffff"
    fill = ROLE_FILL if role else PASSING_FILL
    names = (
        _key_names(instrument, block["keys"])
        if block["keys"] is not None else "no fingering yet"
    )
    label = (
        f"{instrument} {block['note']}: {names}"
        + (f", chord tone {role}" if role else
           ", passing note" if show_roles and block["chord"] else "")
    )
    concert = (
        f'<span class="wind-concert" style="font-size:10px;'
        f'color:#6b7280;height:12px">{block["concert"]} concert</span>'
        if block["concert"] else ""
    )
    lyric = html.escape(block["lyric"] or "")
    bar = max(14, width - 12)

    return (
        f'<div class="wind-cell" style="width:{width:g}px;display:flex;'
        f'flex-direction:column;align-items:center;gap:2px">'
        f'<div style="height:16px">{pill}</div>'
        f'<div role="img" aria-label="{html.escape(label)}" '
        f'class="wind-ring{" wind-tone" if role else ""}" '
        f"style=\"padding:4px;border-radius:8px;border:2px solid {ring};"
        f'background:{fill}">{_chart_html(block["keys"], instrument)}</div>'
        f'<span class="wind-role" style="font-size:10px;font-weight:700;'
        f'color:{CHORD_TONE_COLOUR};height:12px">{role or ""}</span>'
        f'<span style="font-size:13px;font-weight:600">{block["note"]}</span>'
        f"{concert}"
        f'<span style="font-size:12px">{lyric}</span>'
        f'<div style="height:3px;border-radius:2px;background:#94a3b8;'
        f'width:{bar:g}px;margin-top:2px"></div>'
        f"</div>"
    )


def _missing_html(missing, instrument, many):
    """The 'not in this phrase' column of one row."""

    if not missing:
        return ""

    cells = []

    for group in missing:
        heading = (
            f'<div style="font-size:10px;font-weight:700;'
            f'color:{CHORD_TONE_COLOUR}">over {html.escape(group["chord"])}'
            f"</div>" if many else ""
        )
        tones = "".join(
            f'<div class="wind-missing-tone" style="display:flex;'
            f'flex-direction:column;align-items:center;gap:2px;'
            f'opacity:0.85;width:52px">'
            f'<div style="padding:3px;border-radius:7px;'
            f"border:2px dashed {CHORD_TONE_COLOUR}\">"
            f'{_chart_html(tone["keys"], instrument, CHART_SCALE * 0.8)}'
            f"</div>"
            f'<span style="font-size:10px;font-weight:700;'
            f'color:{CHORD_TONE_COLOUR}">{tone["role"]}</span>'
            f'<span style="font-size:12px;font-weight:600">{tone["note"]}</span>'
            f"</div>"
            for tone in group["tones"]
        )
        cells.append(
            f'<div style="display:flex;flex-direction:column;gap:3px">'
            f'{heading}<div style="display:flex;gap:6px">{tones}</div></div>'
        )

    return (
        f'<div class="wind-missing" style="margin-left:auto;'
        f"padding-left:14px;border-left:1px solid {ROW_BORDER};"
        f'display:flex;flex-direction:column;gap:6px;flex-shrink:0">'
        f'<div style="font-size:10px;color:#6b7280">Not in this phrase</div>'
        f'{"".join(cells)}</div>'
    )


def _row_html(row, instrument, show_melody, show_chords, number, many):
    cells = []
    previous = None

    for block in row["blocks"]:
        cells.append(_cell_html(block, instrument, previous, show_chords))
        previous = block

    name = row["chord"] if show_chords else None
    times = f"×{row['times']}" if row.get("times", 1) > 1 else ""
    label = (
        f"Phrases {number}–{number + row['times'] - 1}"
        if row.get("times", 1) > 1 else f"Phrase {number}"
    )
    badge = (
        f'<span class="wind-chord" style="font-size:15px;font-weight:700;'
        f"color:#9d174d;background:#fce7f3;border-radius:5px;"
        f'padding:2px 8px">{html.escape(name)}</span>' if name else ""
    )
    missing = (
        _missing_html(row["missing"], instrument, many)
        if show_chords else ""
    )

    return (
        f'<div class="wind-row" style="display:flex;gap:14px;'
        f"align-items:flex-start;padding:12px 0;"
        f'border-top:1px solid {ROW_BORDER}">'
        f'<div style="width:76px;flex-shrink:0;display:flex;'
        f'flex-direction:column;gap:4px;align-items:flex-start">'
        f'<span style="font-size:10px;color:#9ca3af;white-space:nowrap">'
        f"{label}</span>"
        f"{badge}"
        f'<span class="wind-times" style="font-size:11px;font-weight:600;'
        f'color:#4b5563">{times}</span></div>'
        f'<div style="display:flex;gap:6px;align-items:flex-end;'
        f'flex-wrap:wrap">{"".join(cells)}</div>'
        f"{missing}</div>"
    )


LEGEND = (
    "One chart per note, filled where a key is pressed. A pill over a "
    "chart counts the keys that change from the note before when it is "
    "four or more."
)
UNKNOWN_LEGEND = (
    " A grey dashed chart means that note has no fingering in the "
    "table yet."
)
SAX_LEGEND = (
    " Big names are written pitch, what the player reads; the grey "
    "line is the concert note the chord sheet uses."
)
CHORD_LEGEND = (
    "A pink ring marks a note that is in the chord (R is its root, "
    "then 3, 5, 7); a note with no ring is passing."
)
MISSING_LEGEND = (
    " The right-hand column lists the chord tones the phrase does "
    "not play."
)


def wind_view(piece, instrument, show=None, fold=True, table=None):
    """
    Everything one wind tab shows for a piece, as HTML: the rows,
    and a one-line legend. show says which layers to draw (Melody,
    Chords; both by default) - Chords is the chord badge, the
    rings and the 'not in this phrase' column. A view with neither
    ticked shows the melody. fold folds an identical phrase
    straight after another into one row marked x2.
    """

    show = DEFAULT_SHOW if show is None else list(show)
    want_chords = SHOW_CHORDS in show
    want_melody = SHOW_MELODY in show or not want_chords

    rows = wind_rows(piece, instrument, table)

    if not any(row["blocks"] for row in rows):
        return "<p>No notes to show yet.</p>"

    shown = fold_repeats(rows) if fold else [
        dict(row, times=1, last=row["end"]) for row in rows
    ]
    many = any(len(row["missing"]) > 1 for row in shown)
    body = []
    number = 1

    for row in shown:
        body.append(_row_html(
            row, instrument, want_melody, want_chords, number, many
        ))
        number += row["times"]

    every = [b for row in rows for b in row["blocks"]]
    legend = LEGEND

    if any(b["keys"] is None for b in every):
        legend += UNKNOWN_LEGEND

    if instrument == "Alto sax":
        legend += SAX_LEGEND

    if want_chords and any(row["chord"] for row in rows):
        legend += " " + CHORD_LEGEND + MISSING_LEGEND

    moved = any(b["shift"] for b in every)

    if moved:
        legend += (
            " An amber pill marks a note moved by an octave to fit "
            "the instrument."
        )

    return (
        f'<div class="wind-rows">{"".join(body)}</div>'
        f'<div style="font-size:0.85em;opacity:0.75;margin-top:4px">'
        f"{html.escape(legend)}</div>"
    )
