# wind_fingerings.py

"""
The fingerings the wind view (wind_melody.py) draws: which keys are
pressed for each written note, on the flute and the alto sax.

This is DATA, and the one part of the wind view that no test can
check - whether a fingering is right is a fact about the instrument,
not about the code. So it is kept apart, and nothing here is guessed:
a note with no entry draws a grey "no fingering yet" chart.

STATUS: empty. Waiting for a standard flute chart and a standard alto
sax chart to transcribe from (PLAN-wind-melody.md, "Where the
fingerings come from"). When they arrive:

  * FINGERINGS is filled from the chart, one entry per written
    pitch, and the sheet it came from is named in SOURCE below;
  * KEY_LAYOUT grows to the keys the chart shows (side, palm and
    trill keys, thumb B-flat, the foot keys) - the layout below is
    only the finger holes, the thumb or octave key and the flute's
    right-hand pinky key, enough to draw with;
  * the structural tests in tests/test_wind_fingerings.py start to
    bite (every note of the range has an entry; no two notes share
    one drawing unless the chart says they do).

Pitch numbers count semitones with C0 = 0 (C4 = 48) and are
WRITTEN pitch: for the alto sax, the note the player reads.
"""

from instrument_diagrams import LEFT_HAND_COLOUR, RIGHT_HAND_COLOUR

# The wind instruments the Melody section can draw.
WINDS = ("Flute", "Alto sax")

SOURCE = {"Flute": None, "Alto sax": None}

THUMB_COLOUR = "#64748b"
PINKY_COLOUR = "#a98bd8"


def _key(key_id, name, x, y, w, h, colour, shape="round"):
    return {
        "id": key_id, "name": name, "x": x, "y": y, "w": w, "h": h,
        "colour": colour, "shape": shape,
    }


# Keys drawn on a chart, on a 44 x 100 box: the left hand's three
# finger keys, the right hand's three, and a thumb (flute) or octave
# (sax) key at the top.
KEY_LAYOUT = {
    "Flute": [
        _key("T", "thumb", 0, 4, 8, 12, THUMB_COLOUR, "pill"),
        _key("L1", "left index", 14, 2, 13, 13, LEFT_HAND_COLOUR),
        _key("L2", "left middle", 14, 17, 13, 13, LEFT_HAND_COLOUR),
        _key("L3", "left ring", 14, 32, 13, 13, LEFT_HAND_COLOUR),
        _key("R1", "right index", 14, 54, 13, 13, RIGHT_HAND_COLOUR),
        _key("R2", "right middle", 14, 69, 13, 13, RIGHT_HAND_COLOUR),
        _key("R3", "right ring", 14, 84, 13, 13, RIGHT_HAND_COLOUR),
        _key("P", "right pinky", 30, 88, 11, 8, PINKY_COLOUR, "pill"),
    ],
    "Alto sax": [
        _key("O", "octave key", 0, 2, 8, 11, THUMB_COLOUR, "pill"),
        _key("L1", "left index", 14, 2, 13, 13, LEFT_HAND_COLOUR),
        _key("L2", "left middle", 14, 17, 13, 13, LEFT_HAND_COLOUR),
        _key("L3", "left ring", 14, 32, 13, 13, LEFT_HAND_COLOUR),
        _key("R1", "right index", 14, 54, 13, 13, RIGHT_HAND_COLOUR),
        _key("R2", "right middle", 14, 69, 13, 13, RIGHT_HAND_COLOUR),
        _key("R3", "right ring", 14, 84, 13, 13, RIGHT_HAND_COLOUR),
    ],
}

# {instrument: {written pitch: {"keys": [key ids], "tag": "remark"}}}
FINGERINGS = {"Flute": {}, "Alto sax": {}}
