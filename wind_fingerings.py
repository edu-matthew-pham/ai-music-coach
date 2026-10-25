# wind_fingerings.py

"""
The fingerings the wind view (wind_melody.py) draws: which keys are
pressed for each written note, on the flute and the alto sax.

This is DATA, transcribed from printed charts (SOURCE below), and the
one part of the wind view no test can prove right - whether a
fingering is correct is a fact about the instrument. What the tests
do check (tests/test_wind_fingerings.py): every note of each range
has an entry, every key named exists, and no two notes draw alike
unless the chart draws them alike. The transcription was also checked
once, mechanically, against the charts' own pixels (the charts are
not in the repo; the result is in BUILDNOTES-append-wind-melody.md).

How it was transcribed (2026-10-26, BUILDNOTES-append-wind-melody.md):
each chart page rendered at 300-400 dpi, every key of every diagram
measured (filled or not) at fixed points from a reference diagram,
the doubtful ones looked at by eye. The flute was read from TWO
charts independently and compared: they agree on every note but
three, listed under FLUTE_DIFFERENCES.

A note's "alternates" are the chart's other fingerings for it, kept
for the alternates toggle (not built yet); the view draws "keys".

Pitch numbers count semitones with C0 = 0 (C4 = 48) and are WRITTEN
pitch: for the alto sax, the note the player reads. Sax fingerings by
written pitch are the same on every saxophone (the McGill chart says
"All Saxes").

A note marked "same_as_lower_octave" is fingered exactly as the note
an octave below and sounds higher by the breath; both charts draw them
alike. The view tags it so two identical charts are not a puzzle.
"""

from instrument_diagrams import LEFT_HAND_COLOUR, RIGHT_HAND_COLOUR

# The wind instruments the Melody section can draw.
WINDS = ("Flute", "Alto sax")

SOURCE = {
    "Flute": (
        "Basic Flute Fingering Chart, Karen Evans Moratz, Flute For "
        "Dummies (Wiley, 2016), cross-checked against the Yamaha flute "
        "fingering chart"
    ),
    "Alto sax": (
        "Saxophone Finger Chart, All Saxes - Standard range, McGill "
        "Music Sax School (mcgillmusic.com)"
    ),
}

# Where the two flute charts differ. The Yamaha chart's fingering is
# the one drawn (it needs no B-foot and no extra pinky key); the
# Dummies one is kept as an alternate. For a player to settle.
FLUTE_DIFFERENCES = {
    82: "B-flat 6: the Dummies chart also holds the D-sharp key down",
    83: "B 6: the Dummies chart also holds the D-sharp key down",
    84: "C 7: the Dummies chart adds the gizmo key (B-foot flutes only)",
}

THUMB_COLOUR = "#64748b"
PINKY_COLOUR = "#a98bd8"
PALM_COLOUR = "#0e7490"
SIDE_COLOUR = "#0e7490"


def _key(key_id, name, x, y, w, h, colour, shape="round"):
    return {
        "id": key_id, "name": name, "x": x, "y": y, "w": w, "h": h,
        "colour": colour, "shape": shape,
    }


# --- the keys drawn, on a 44 x 100 box -------------------------------

# Flute: drawn upright, head end at the top (the charts draw it lying
# down). Left hand's three keys, then the right hand's, with the thumb
# keys at the left, the levers and trill keys beside the fingers, the
# right pinky's D-sharp key, and the foot keys along the bottom.
_FLUTE_LAYOUT = [
    _key("ThB", "thumb B key", 0, 4, 8, 12, THUMB_COLOUR, "pill"),
    _key("ThBb", "thumb B-flat lever", 0, 18, 8, 8, THUMB_COLOUR, "pill"),
    _key("L1", "left index", 16, 2, 12, 12, LEFT_HAND_COLOUR),
    _key("L2", "left middle", 16, 15, 12, 12, LEFT_HAND_COLOUR),
    _key("L3", "left ring", 16, 28, 12, 12, LEFT_HAND_COLOUR),
    _key("Gs", "G-sharp key (left pinky)", 32, 30, 8, 10,
         LEFT_HAND_COLOUR, "pill"),
    _key("RBb", "B-flat lever (right index)", 3, 48, 8, 9,
         RIGHT_HAND_COLOUR, "pill"),
    _key("R1", "right index", 16, 46, 12, 12, RIGHT_HAND_COLOUR),
    _key("Tr1", "first trill key", 33, 55, 6, 6, RIGHT_HAND_COLOUR),
    _key("R2", "right middle", 16, 59, 12, 12, RIGHT_HAND_COLOUR),
    _key("Tr2", "second trill key", 33, 68, 6, 6, RIGHT_HAND_COLOUR),
    _key("R3", "right ring", 16, 72, 12, 12, RIGHT_HAND_COLOUR),
    _key("Ds", "D-sharp key (right pinky)", 31, 77, 10, 8,
         PINKY_COLOUR, "pill"),
    _key("FootCs", "C-sharp roller (right pinky)", 10, 89, 10, 8,
         PINKY_COLOUR, "pill"),
    _key("FootC", "C roller (right pinky)", 22, 89, 10, 8,
         PINKY_COLOUR, "pill"),
    _key("Gizmo", "gizmo key (B-foot flutes)", 35, 90, 6, 6,
         PINKY_COLOUR),
]


def _sax(key_id, name, cx, cy, w, h, colour, shape="pill"):
    """
    A sax key placed as on the McGill chart: (cx, cy) is its centre in
    the chart's own pixels (300 dpi) from the middle of the line
    between the hands, w x h its size; scaled by a quarter into the
    44 x 100 box.
    """

    scale = 0.25
    x = (cx - w / 2 + 81) * scale
    y = (cy - h / 2 + 196) * scale + 1

    return _key(
        key_id, name, round(x, 1), round(y, 1), round(w * scale, 1),
        round(h * scale, 1), colour, shape
    )


# Alto sax: as the McGill chart draws it - the octave key at the left,
# the front F above the first finger, the three palm keys at the top
# right, the left pinky's table (G-sharp, low B, C-sharp, B-flat) at
# the right, the three side keys and the high and alternate F-sharp
# keys at the left of the right hand, and the right pinky's E-flat and
# low C at the bottom left.
_SAX_LAYOUT = [
    _sax("O", "octave key (left thumb)", -60, -115, 22, 40, THUMB_COLOUR),
    _sax("Ff", "front F key", -2, -178, 36, 30, LEFT_HAND_COLOUR),
    _sax("L1", "left index", -3, -140, 42, 42, LEFT_HAND_COLOUR, "round"),
    _sax("Bis", "bis key", 21, -114, 9, 9, LEFT_HAND_COLOUR, "round"),
    _sax("PalmF", "palm F key", 40, -125, 20, 55, PALM_COLOUR),
    _sax("PalmEb", "palm E-flat key", 60, -165, 20, 58, PALM_COLOUR),
    _sax("PalmD", "palm D key", 86, -140, 18, 55, PALM_COLOUR),
    _sax("L2", "left middle", -3, -88, 42, 42, LEFT_HAND_COLOUR, "round"),
    _sax("L3", "left ring", -3, -35, 42, 42, LEFT_HAND_COLOUR, "round"),
    _sax("Gs", "G-sharp key (left pinky)", 62, -29, 44, 16,
         LEFT_HAND_COLOUR),
    _sax("LB", "low B key (left pinky)", 50, -3, 18, 28, LEFT_HAND_COLOUR),
    _sax("LCs", "low C-sharp key (left pinky)", 74, -3, 18, 28,
         LEFT_HAND_COLOUR),
    _sax("LBb", "low B-flat key (left pinky)", 62, 25, 44, 16,
         LEFT_HAND_COLOUR),
    _sax("SideE", "side high E key", -51, -5, 16, 30, SIDE_COLOUR),
    _sax("SideC", "side C key", -51, 31, 16, 28, SIDE_COLOUR),
    _sax("SideBb", "side B-flat key", -51, 69, 16, 32, SIDE_COLOUR),
    _sax("R1", "right index", -3, 35, 42, 42, RIGHT_HAND_COLOUR, "round"),
    _sax("R2", "right middle", -3, 87, 42, 42, RIGHT_HAND_COLOUR, "round"),
    _sax("R3", "right ring", -3, 140, 42, 42, RIGHT_HAND_COLOUR, "round"),
    _sax("HFs", "high F-sharp key", -40, 104, 10, 21, SIDE_COLOUR),
    _sax("AltFs", "alternate F-sharp key", -37, 127, 10, 16, SIDE_COLOUR),
    _sax("REb", "E-flat key (right pinky)", -59, 153, 44, 22, PINKY_COLOUR),
    _sax("RC", "low C key (right pinky)", -59, 180, 44, 20, PINKY_COLOUR),
]

KEY_LAYOUT = {"Flute": _FLUTE_LAYOUT, "Alto sax": _SAX_LAYOUT}


# --- the fingerings --------------------------------------------------

def _f(keys, tag="", alternates=(), same_as_lower_octave=False):
    entry = {"keys": keys.split()}

    if tag:
        entry["tag"] = tag

    if alternates:
        entry["alternates"] = [
            {"keys": k.split(), "tag": t} for k, t in alternates
        ]

    if same_as_lower_octave:
        entry["same_as_lower_octave"] = True

    return entry


_OCTAVE_UP = "same keys as an octave lower"

# The flute sounds as written: C4 (48) to C7 (84). Every primary
# fingering is drawn the same on both charts unless FLUTE_DIFFERENCES
# says otherwise. B-flat: both charts put the 1-and-1 fingering first.
_FLUTE = {
    48: _f("ThB L1 L2 L3 R1 R2 R3 FootC FootCs", "foot C roller"),
    49: _f("ThB L1 L2 L3 R1 R2 R3 FootCs", "foot C-sharp roller"),
    50: _f("ThB L1 L2 L3 R1 R2 R3", "pinky up"),
    51: _f("ThB L1 L2 L3 R1 R2 R3 Ds"),
    52: _f("ThB L1 L2 L3 R1 R2 Ds"),
    53: _f("ThB L1 L2 L3 R1 Ds"),
    54: _f("ThB L1 L2 L3 R3 Ds", alternates=[
        ("ThB L1 L2 L3 R2 Ds", "middle finger F-sharp (Yamaha)"),
    ]),
    55: _f("ThB L1 L2 L3 Ds"),
    56: _f("ThB L1 L2 L3 Gs Ds"),
    57: _f("ThB L1 L2 Ds"),
    58: _f("ThB L1 R1 Ds", "1-and-1 B-flat", alternates=[
        ("ThBb L1 Ds", "thumb B-flat"),
        ("ThB L1 RBb Ds", "lever B-flat"),
    ]),
    59: _f("ThB L1 Ds"),
    60: _f("L1 Ds"),
    61: _f("Ds"),
    62: _f("ThB L2 L3 R1 R2 R3", "first finger up, pinky up"),
    63: _f("ThB L2 L3 R1 R2 R3 Ds"),
    64: _f("ThB L1 L2 L3 R1 R2 Ds", _OCTAVE_UP, same_as_lower_octave=True),
    65: _f("ThB L1 L2 L3 R1 Ds", _OCTAVE_UP, same_as_lower_octave=True),
    66: _f("ThB L1 L2 L3 R3 Ds", _OCTAVE_UP, alternates=[
        ("ThB L1 L2 L3 R2 Ds", "middle finger F-sharp (Yamaha)"),
    ], same_as_lower_octave=True),
    67: _f("ThB L1 L2 L3 Ds", _OCTAVE_UP, same_as_lower_octave=True),
    68: _f("ThB L1 L2 L3 Gs Ds", _OCTAVE_UP, same_as_lower_octave=True),
    69: _f("ThB L1 L2 Ds", _OCTAVE_UP, same_as_lower_octave=True),
    70: _f("ThB L1 R1 Ds", "1-and-1 B-flat; " + _OCTAVE_UP, alternates=[
        ("ThBb L1 Ds", "thumb B-flat"),
        ("ThB L1 RBb Ds", "lever B-flat"),
    ], same_as_lower_octave=True),
    71: _f("ThB L1 Ds", _OCTAVE_UP, same_as_lower_octave=True),
    72: _f("L1 Ds", _OCTAVE_UP, same_as_lower_octave=True),
    73: _f("Ds", _OCTAVE_UP, same_as_lower_octave=True),
    74: _f("ThB L2 L3 Ds"),
    75: _f("ThB L1 L2 L3 Gs R1 R2 R3 Ds"),
    76: _f("ThB L1 L2 R1 R2 Ds"),
    77: _f("ThB L1 L3 R1 Ds"),
    78: _f("ThB L1 L3 R3 Ds"),
    79: _f("L1 L2 L3 Ds", "thumb off"),
    80: _f("L2 L3 Gs Ds", "thumb off"),
    81: _f("ThB L2 R1 Ds"),
    82: _f("ThB R1 Tr1", "first trill key", alternates=[
        ("ThB R1 Tr1 Ds", "with the D-sharp key (Dummies chart)"),
    ]),
    83: _f("ThB L1 L3 Tr2", "second trill key", alternates=[
        ("ThB L1 L3 Tr2 Ds", "with the D-sharp key (Dummies chart)"),
    ]),
    84: _f("L1 L2 L3 Gs R1", "thumb off", alternates=[
        ("L1 L2 L3 Gs R1 Gizmo", "with the gizmo key (Dummies chart, "
         "B-foot flutes)"),
    ]),
}

# The saxophone, written B-flat 3 (46) to F-sharp 6 (78), as the
# McGill chart draws it; its first fingering for a note is the one
# drawn, the others are alternates.
_SAX = {
    46: _f("L1 L2 L3 R1 R2 R3 LBb RC", "low B-flat key"),
    47: _f("L1 L2 L3 R1 R2 R3 LB RC", "low B key"),
    48: _f("L1 L2 L3 R1 R2 R3 RC", "low C key"),
    49: _f("L1 L2 L3 R1 R2 R3 LCs RC", "C-sharp key"),
    50: _f("L1 L2 L3 R1 R2 R3"),
    51: _f("L1 L2 L3 R1 R2 R3 REb", "E-flat key"),
    52: _f("L1 L2 L3 R1 R2"),
    53: _f("L1 L2 L3 R1"),
    54: _f("L1 L2 L3 R2", alternates=[
        ("L1 L2 L3 R1 AltFs", "alternate F-sharp key"),
    ]),
    55: _f("L1 L2 L3"),
    56: _f("L1 L2 L3 Gs", "G-sharp key"),
    57: _f("L1 L2"),
    58: _f("L1 Bis", "bis B-flat", alternates=[
        ("L1 L2 SideBb", "side B-flat"),
        ("L1 R2", "B-flat with the right middle finger"),
    ]),
    59: _f("L1"),
    60: _f("L2", alternates=[("L1 SideC", "side C")]),
    61: _f("", "all keys up"),
    62: _f("O L1 L2 L3 R1 R2 R3"),
    63: _f("O L1 L2 L3 R1 R2 R3 REb"),
    64: _f("O L1 L2 L3 R1 R2"),
    65: _f("O L1 L2 L3 R1"),
    66: _f("O L1 L2 L3 R2", alternates=[
        ("O L1 L2 L3 R1 AltFs", "alternate F-sharp key"),
    ]),
    67: _f("O L1 L2 L3"),
    68: _f("O L1 L2 L3 Gs"),
    69: _f("O L1 L2"),
    70: _f("O L1 Bis", "bis B-flat", alternates=[
        ("O L1 L2 SideBb", "side B-flat"),
        ("O L1 R2", "B-flat with the right middle finger"),
    ]),
    71: _f("O L1"),
    72: _f("O L2"),
    73: _f("O", "octave key only"),
    74: _f("O PalmD", "palm D key"),
    75: _f("O PalmD PalmEb", "palm keys"),
    76: _f("O PalmD PalmEb SideE", "palm keys and side E", alternates=[
        ("O Ff L2 L3", "front F"),
    ]),
    77: _f("O PalmD PalmEb PalmF SideE", "all three palm keys",
          alternates=[("O Ff L2", "front F")]),
    78: _f("O Ff L2 SideBb", "front F", alternates=[
        ("O Ff L2 HFs", "high F-sharp key"),
    ]),
}

# {instrument: {written pitch: {"keys", "tag", "alternates",
#  "same_as_lower_octave"}}}
FINGERINGS = {"Flute": _FLUTE, "Alto sax": _SAX}
