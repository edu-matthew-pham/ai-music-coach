"""
The shape of the fingering data (wind_fingerings.py). Whether a
fingering is RIGHT is a fact about the instrument that no test here
can check; what can be checked is that the table is well formed, that
it names the chart it came from, and - once a chart has been
transcribed - that it has no gaps.

The completeness tests skip, loudly, while an instrument has no
source chart yet: a skipped test is a to-do, not a pass.
"""

import pytest

import wind_fingerings
from wind_melody import WRITTEN_RANGE

NAMES = list(wind_fingerings.WINDS)


@pytest.mark.parametrize("name", NAMES)
def test_every_key_has_a_unique_id_and_a_name(name):
    layout = wind_fingerings.KEY_LAYOUT[name]
    ids = [key["id"] for key in layout]

    assert len(ids) == len(set(ids))
    assert all(key["name"] for key in layout)


@pytest.mark.parametrize("name", NAMES)
def test_every_key_fits_inside_the_chart_box(name):
    # The box is 44 wide by 100 high (wind_melody.CHART_WIDTH/HEIGHT).
    for key in wind_fingerings.KEY_LAYOUT[name]:
        assert key["x"] >= 0 and key["y"] >= 0
        assert key["x"] + key["w"] <= 44
        assert key["y"] + key["h"] <= 100


@pytest.mark.parametrize("name", NAMES)
def test_no_two_keys_overlap(name):
    layout = wind_fingerings.KEY_LAYOUT[name]

    for index, a in enumerate(layout):
        for b in layout[index + 1:]:
            apart = (
                a["x"] + a["w"] <= b["x"] or b["x"] + b["w"] <= a["x"]
                or a["y"] + a["h"] <= b["y"] or b["y"] + b["h"] <= a["y"]
            )

            assert apart, f"{a['id']} overlaps {b['id']} on the {name}"


@pytest.mark.parametrize("name", NAMES)
def test_every_fingering_uses_only_keys_that_exist(name):
    ids = {key["id"] for key in wind_fingerings.KEY_LAYOUT[name]}

    for pitch, found in wind_fingerings.FINGERINGS[name].items():
        assert set(found["keys"]) <= ids, f"pitch {pitch} on the {name}"


@pytest.mark.parametrize("name", NAMES)
def test_a_fingering_is_inside_the_instruments_written_range(name):
    low, high = WRITTEN_RANGE[name]

    for pitch in wind_fingerings.FINGERINGS[name]:
        assert low <= pitch <= high


@pytest.mark.parametrize("name", NAMES)
def test_filled_data_names_the_chart_it_came_from(name):
    if wind_fingerings.FINGERINGS[name]:
        assert wind_fingerings.SOURCE[name]


@pytest.mark.parametrize("name", NAMES)
def test_every_note_of_the_range_has_a_fingering(name):
    if not wind_fingerings.SOURCE[name]:
        pytest.skip(f"{name}: no chart transcribed yet")

    low, high = WRITTEN_RANGE[name]
    missing = [
        pitch for pitch in range(low, high + 1)
        if pitch not in wind_fingerings.FINGERINGS[name]
    ]

    assert missing == []


@pytest.mark.parametrize("name", NAMES)
def test_no_two_notes_share_a_drawing_unless_the_chart_says_so(name):
    if not wind_fingerings.SOURCE[name]:
        pytest.skip(f"{name}: no chart transcribed yet")

    seen = {}

    for pitch, found in sorted(wind_fingerings.FINGERINGS[name].items()):
        drawing = tuple(sorted(found["keys"]))

        if drawing in seen and not found.get("same_as_lower_octave"):
            pytest.fail(
                f"{name}: {seen[drawing]} and {pitch} draw alike; mark "
                "same_as_lower_octave if the chart does"
            )

        seen[drawing] = pitch
