import pytest

from playback import (
    note_to_frequency,
    make_note,
    mix_tracks
)


def test_a4_frequency():
    assert note_to_frequency("A4") == pytest.approx(
        440,
        abs=0.01
    )


def test_c4_frequency():
    assert note_to_frequency("C4") == pytest.approx(
        261.63,
        abs=0.01
    )


def test_one_beat_length():
    sound = make_note(
        "A4",
        beats=1,
        bpm=120,
        sample_rate=8000
    )

    # 120 BPM = 0.5 seconds per beat.
    assert len(sound) == 4000


def test_mix_tracks():
    track_1 = [1, 0, -1]
    track_2 = [-1, 0, 1]

    assert mix_tracks(
        track_1,
        track_2
    ) == [0, 0, 0]

def test_click_fills_exactly_one_beat():
    from playback import make_click

    click = make_click(bpm=120, sample_rate=8000)

    # 120 BPM = half a second per beat.
    assert len(click) == 4000


def test_count_in_is_four_beats():
    from playback import make_count_in, COUNT_IN_BEATS

    count_in = make_count_in(bpm=120, sample_rate=8000)

    assert COUNT_IN_BEATS == 4
    assert len(count_in) == 4 * 4000


def test_metronome_keeps_the_length():
    from playback import make_melody, add_metronome

    rate, melody = make_melody(
        ["C4", "E4"],
        [1, 1],
        120,
        8000
    )

    with_clicks = add_metronome(melody, 2, 120, 8000)

    assert len(with_clicks) == len(melody)


def test_metronome_clicks_are_quieter_than_the_count_in():
    """
    The count-in has to be obvious. The clicks under the
    music only have to be audible.
    """

    from playback import make_click

    count_click = make_click(120, 8000)
    quiet_click = make_click(120, 8000, loud=0.3)

    assert max(quiet_click) < max(count_click)


def test_click_shrinks_at_absurd_tempos():
    """
    The click is capped at a tenth of the beat, so even a
    tempo no musician would use produces sensible audio
    rather than a click longer than its own beat.
    """

    from playback import make_click

    click = make_click(bpm=2000, sample_rate=8000)

    # At 2000 BPM a beat is 0.03 seconds = 240 samples.
    assert len(click) == 240

    # And the sound never outgrows the silence entirely.
    quiet = sum(1 for value in click if value == 0)

    assert quiet > 0