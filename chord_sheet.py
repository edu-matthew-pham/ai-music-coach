# chord_sheet.py

"""
The chord sheet: every chord you need on one instrument, at
once, for preparing before playback - or for looking up a
key's notes and chords with no song loaded at all.

The mixer shows one chord at a time, following the playhead.
This is the other view: all of them side by side. It draws
nothing new - every picture is the one the mixer already
draws (instrument_diagrams), stacked the same way, so the
two can never disagree.

Plain Python and plain strings, no interface: main.py puts
the results on the page. Nothing here reads or writes the
key box or the chart box beyond being handed their text -
the key chosen here is a view setting of its own, never the
song's key (DESIGN.md: it is usually two things).
"""

import html
import re

from chord_detector import DIATONIC
from chords import read_chart
from harmony import MAJOR_SCALES, RELATIVE_MINORS, read_key
from instrument_diagrams import (
    INSTRUMENTS,
    _base_instrument_name,
    chord_overlay_for,
    scale_overlay_for,
    shape_overlay_for,
    structure_for,
)
from notes import NOTE_SEMITONES


# Browsing starts here when no song says otherwise.
DEFAULT_BROWSE_KEY = "C major"

_MINOR_TO_MAJOR = {minor: major for major, minor in RELATIVE_MINORS.items()}


def browse_keys():
    """
    The 24 keys offered for browsing, as (label, value)
    pairs, each major followed by its relative minor in the
    same order the key box uses. Minor keys are listed on
    their own here, unlike the key box (which names a key
    signature, major and minor together), because a minor
    key marks a different home note: A minor is C major's
    seven notes with A as home.
    """

    keys = []

    for major in MAJOR_SCALES:
        keys.append((f"{major} major", f"browse:{major} major"))
        minor = RELATIVE_MINORS[major]
        keys.append((f"{minor} minor", f"browse:{minor} minor"))

    return keys


def parse_browse_key(label):
    """
    ("C major" or "A minor") -> (signature key, home note).
    The signature is the major key whose seven notes are
    used; home is the note marked as home on the Scale
    picture. Raises ValueError for anything else.
    """

    name, _, mode = label.strip().partition(" ")

    if mode == "major" and name in MAJOR_SCALES:
        return name, name

    if mode == "minor" and name in _MINOR_TO_MAJOR:
        return _MINOR_TO_MAJOR[name], name

    raise ValueError(f"'{label}' is not a key this sheet offers.")


def key_chords(signature, home):
    """
    The seven chords built on the key's own notes, in order
    from home: C Dm Em F G Am Bdim in C major, Am Bdim C Dm
    Em F G in A minor. Qualities come from the same DIATONIC
    table the chord detector uses; the root names come from
    the key's own scale, so F sharp major has E sharp, not F.
    """

    scale = MAJOR_SCALES[signature]
    chords = [
        scale[index] + quality
        for index, (_, quality) in enumerate(DIATONIC)
    ]

    start = next(
        index for index, note in enumerate(scale)
        if NOTE_SEMITONES[note] % 12 == NOTE_SEMITONES[home] % 12
    )

    return chords[start:] + chords[:start]


def song_sections(key_text, chart_text):
    """
    The song's own keys and the chords each one plays, read
    from the two boxes' text: [{"key", "from_beat", "chords"}]
    in order, one per stretch of the piece that has chords.
    A chord belongs to the key in force where it starts, and
    appears once per stretch however often it recurs.

    [] when there is no song to speak of: an empty chart, or
    boxes that cannot be read yet (a key half typed). The
    sheet then simply browses.
    """

    try:
        changes = read_key(key_text)
        chords, _ = read_chart(chart_text)
    except ValueError:
        return []

    sections = []

    for index, (beat, key) in enumerate(changes):

        end = (
            changes[index + 1][0]
            if index + 1 < len(changes) else float("inf")
        )

        names = []

        for start, _length, name in chords:
            if beat <= start < end and name not in names:
                names.append(name)

        if names:
            sections.append(
                {"key": key, "from_beat": beat, "chords": names}
            )

    return sections


def choices(key_text, chart_text):
    """
    What the sheet's key dropdown offers: the song's own
    keys first (when there is a song), then all 24 browsing
    keys. Values are "song:N" or "browse:<key>".
    """

    offered = []
    sections = song_sections(key_text, chart_text)

    for index, section in enumerate(sections):
        where = (
            "from the song" if index == 0
            else f"from the song, from beat {section['from_beat']:g}"
        )
        offered.append(
            (f"{section['key']} major - {where}", f"song:{index}")
        )

    return offered + browse_keys()


def default_selection(key_text, chart_text):
    """
    Where the sheet starts: the song's first key if there is
    a song, otherwise C major.
    """

    if song_sections(key_text, chart_text):
        return "song:0"

    return f"browse:{DEFAULT_BROWSE_KEY}"


def resolve(selection, key_text, chart_text):
    """
    A dropdown value -> what to draw, and what to say about
    where the key came from:

        {"signature", "home", "chords", "from_song", "line"}

    A song choice that no longer exists (the song changed
    under it) falls back to the default rather than failing.
    """

    sections = song_sections(key_text, chart_text)

    kind, _, value = (selection or "").partition(":")

    if kind == "song" and value.isdigit() and int(value) < len(sections):
        section = sections[int(value)]
        where = (
            "" if int(value) == 0
            else f" (from beat {section['from_beat']:g})"
        )

        return {
            "signature": section["key"],
            "home": section["key"],
            "chords": section["chords"],
            "from_song": True,
            "line": (
                f"Key: {section['key']} major, from the song{where}. "
                f"Showing the chords the song plays."
            ),
        }

    try:
        label = value if kind == "browse" else DEFAULT_BROWSE_KEY
        signature, home = parse_browse_key(label)
    except ValueError:
        label = DEFAULT_BROWSE_KEY
        signature, home = parse_browse_key(label)

    if sections:
        opening = sections[0]["key"]
        line = (
            f"Key: {label}, your choice. The song's own key is "
            f"{opening} major."
        )
    else:
        line = f"Key: {label}. No song loaded - browsing."

    return {
        "signature": signature,
        "home": home,
        "chords": key_chords(signature, home),
        "from_song": False,
        "line": line,
    }


def instrument_families():
    """
    {family: [variant names]} straight from INSTRUMENTS, in
    its order - the one place the instrument list lives.
    """

    families = {}

    for name in INSTRUMENTS:
        families.setdefault(_base_instrument_name(name), []).append(name)

    return families


def variant_label(instrument):
    """"Piano, 2 octaves" -> "2 octaves"."""

    return instrument.partition(", ")[2]


def stack(structure, *overlays):
    """
    Overlays laid over a structure picture. Every layer of
    one instrument shares one coordinate system, so the
    insides of the overlays simply go on top.
    """

    inner = "".join(
        re.search(r">(.*)</svg>\s*$", overlay, re.S).group(1)
        for overlay in overlays
    )

    return structure[: structure.rindex("</svg>")] + inner + "</svg>"


SHOW_SHAPE = "Chord shape"
SHOW_NOTES = "Chord notes"

# Both on to start: the two layers are different colours, so
# together they stay readable.
DEFAULT_SHOW = [SHOW_SHAPE, SHOW_NOTES]


def chord_picture(signature, instrument, chord_name, show=None):
    """
    One chord's picture on one instrument. `show` is which of
    the two chord layers to draw: the beginner shape, every
    place the chord's notes fall, or both (the default).
    Returns (svg, note) where note says anything the reader
    needs to know about what they are looking at.

    A card is never blank. A chord with no shape shows its
    notes whatever is ticked (and says so, if the shape was
    asked for); with nothing ticked, the notes are shown too.
    """

    show = DEFAULT_SHOW if show is None else list(show)

    want_shape = SHOW_SHAPE in show
    want_notes = SHOW_NOTES in show

    structure = structure_for(instrument)
    shape = (
        shape_overlay_for(signature, instrument, chord_name)
        if want_shape else None
    )
    notes = chord_overlay_for(signature, instrument, chord_name)

    if not want_shape and not want_notes:
        return (
            stack(structure, notes),
            "Nothing ticked - showing the chord's notes.",
        )

    if want_shape and shape is None:
        return (
            stack(structure, notes),
            "No standard shape - showing the chord's notes.",
        )

    # Notes underneath, the shape on top of them.
    layers = ([notes] if want_notes else []) + (
        [shape] if want_shape else []
    )

    return stack(structure, *layers), ""


def scale_picture(signature, home, instrument):
    return stack(
        structure_for(instrument),
        scale_overlay_for(signature, instrument, home=home),
    )


_GRID = (
    "display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));"
    "gap:14px;margin-top:10px"
)

_CARD = (
    "border:1px solid var(--border-color-primary,#ccc);border-radius:8px;"
    "padding:8px 10px"
)


def sheet_html(selection, key_text, chart_text, instrument, show=None):
    """
    The sheet for one instrument: the key's notes, then a card
    for every chord. HTML for a gr.HTML block.
    """

    state = resolve(selection, key_text, chart_text)
    signature = state["signature"]

    parts = [
        '<div class="chord-sheet">',
        f'<div style="{_CARD}"><b>Notes of the key</b>'
        f'<div style="font-size:0.85em;opacity:0.75">Home is orange; '
        f'green notes are in the key.</div>'
        f'{scale_picture(signature, state["home"], instrument)}</div>',
        f'<div style="{_GRID}">',
    ]

    for name in state["chords"]:
        picture, note = chord_picture(
            signature, instrument, name, show
        )
        note_html = (
            f'<div style="font-size:0.85em;opacity:0.75">'
            f'{html.escape(note)}</div>' if note else ""
        )
        parts.append(
            f'<div style="{_CARD}"><b>{html.escape(name)}</b>'
            f'{note_html}{picture}</div>'
        )

    parts.append("</div></div>")

    return "".join(parts)
