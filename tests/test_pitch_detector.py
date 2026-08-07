import numpy as np

from playback import make_note
from pitch_detector import detect_pitch


def test_detect_generated_a4():
    sample_rate = 8000

    sound = make_note(
        "A4",
        beats=2,
        bpm=120,
        sample_rate=sample_rate
    )

    sound = np.array(sound)

    note = detect_pitch(
        sound,
        sample_rate
    )

    assert note == "A4"