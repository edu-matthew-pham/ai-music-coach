"""
The second opinion has to be worth having.

These check the comparison itself, with a detector passed
in, so they run whether or not CREPE is installed: the
witness is optional and the tests cannot depend on it.
"""

import numpy as np

from pitch_witness import (
    compare_traces,
    describe_comparison,
    octaves_apart,
    second_opinion,
    crepe_available
)


def test_two_detectors_hearing_the_same_thing_agree():
    trace = np.array([60.0, 60.1, 59.9, 60.0])

    result = compare_traces(trace, trace)

    assert result["compared"] == 4
    assert result["octave_frames"] == 0
    assert result["agrees"]


def test_an_octave_apart_is_recognised_as_an_octave():
    """
    The failure this exists to catch: the same note, one
    detector an octave below the other.
    """

    low = np.array([48.0, 48.0, 48.0])
    high = low + 12

    result = compare_traces(low, high)

    assert result["octave_frames"] == 3
    assert result["octave_direction"] == 1
    assert not result["agrees"]


def test_a_wrong_note_is_not_mistaken_for_an_octave():
    """
    Seven semitones apart is a disagreement about which
    note, not about which octave, and saying "octave" of
    it would send someone to the wrong setting.
    """

    first = np.array([60.0, 60.0])
    second = np.array([67.0, 67.0])

    result = compare_traces(first, second)

    assert result["octave_frames"] == 0
    assert not result["agrees"]


def test_small_differences_count_as_agreement():
    """
    Twenty cents is two detectors describing one note. A
    singer does not need telling that two machines
    disagree by less than they can hear.
    """

    first = np.array([60.0, 60.0])
    second = np.array([60.2, 60.2])

    result = compare_traces(first, second)

    assert result["agrees"]
    assert result["octave_frames"] == 0


def test_only_frames_both_detectors_voiced_are_compared():
    """
    One detector hearing silence where the other hears a
    note is a different question from the two hearing
    different notes.
    """

    first = np.array([60.0, np.nan, 60.0, np.nan])
    second = np.array([60.0, 60.0, np.nan, np.nan])

    result = compare_traces(first, second)

    assert result["compared"] == 1


def test_nothing_in_common_is_reported_not_guessed():
    first = np.array([np.nan, np.nan])
    second = np.array([60.0, 60.0])

    result = compare_traces(first, second)

    assert result["compared"] == 0
    assert result["agrees"] is None
    assert "no frames" in describe_comparison(result)


def test_octaves_apart_needs_to_be_close_to_an_octave():
    assert octaves_apart(60.0, 72.0) == 1
    assert octaves_apart(60.0, 48.0) == -1
    assert octaves_apart(60.0, 60.0) == 0

    # Ten semitones is not an octave, however near.
    assert octaves_apart(60.0, 70.0) == 0

    assert octaves_apart(60.0, float("nan")) == 0


def test_a_missing_witness_is_not_an_error():
    """
    CREPE is optional. Without it the app is complete, and
    the feedback says how to enable it rather than
    failing.
    """

    said = describe_comparison(None)

    assert "no detector installed" in said
    assert "pip install torchcrepe" in said


def test_a_detector_can_be_passed_in():
    """
    Which is how this is tested without the package, and
    how another detector could be tried later.
    """

    def pretend(sound, sample_rate):
        return (
            np.array([0.0, 0.01]),
            np.array([48.0, 48.0])
        )

    result = second_opinion(
        np.zeros(100), 16000,
        np.array([60.0, 60.0]),
        detector=pretend
    )

    assert result["octave_frames"] == 2
    assert result["octave_direction"] == -1


def test_the_words_name_the_direction_and_point_at_the_setting():
    low = np.array([60.0, 60.0, 60.0])

    said = describe_comparison(compare_traces(low, low - 12))

    assert "octave lower" in said
    assert "Octave setting" in said


def test_availability_names_the_backend_or_nothing():
    """
    Which backend, not merely whether: the two are the
    same model by different roads, and a disagreement
    reads differently depending on which answered.
    """

    assert crepe_available() in ("torchcrepe", "crepe", None)


def test_the_second_opinion_is_off_unless_asked_for():
    """
    It costs a second detector's worth of waiting, and the
    judging does not depend on it, so nothing runs unless
    the box is ticked.
    """

    import numpy as np

    from music import analyse_performance

    rate = 22050
    times = np.linspace(0, 2, rate * 2, False)
    sound = (0.3 * np.sin(2 * np.pi * 261.63 * times)).astype("float32")

    quiet, _, _ = analyse_performance(
        (rate, sound), "C4 C4", "1 1", 120
    )

    assert "Second opinion" not in quiet

    asked, _, _ = analyse_performance(
        (rate, sound), "C4 C4", "1 1", 120,
        second_opinion_on=True
    )

    assert "Second opinion" in asked


def test_asking_without_the_package_says_how_to_get_it():
    """
    An absent witness is not a failure: the feedback says
    what is missing and the judging is unaffected.
    """

    import numpy as np

    from music import analyse_performance
    from pitch_witness import crepe_available

    if crepe_available():
        return

    rate = 22050
    times = np.linspace(0, 2, rate * 2, False)
    sound = (0.3 * np.sin(2 * np.pi * 261.63 * times)).astype("float32")

    text, performance, tuning = analyse_performance(
        (rate, sound), "C4 C4", "1 1", 120,
        second_opinion_on=True
    )

    assert "pip install torchcrepe" in text

    # And the judging still happened.
    assert performance is not None
    assert tuning is not None


def test_a_detector_that_fails_is_an_absent_opinion():
    """
    A backend can be installed and still unusable - a half
    installed torch raises about a missing library when it
    is imported. A second opinion that cannot be had is an
    absent one, not a failed comparison: what the judging
    says about the singing does not depend on it.
    """

    import numpy as np

    def broken(sound, sample_rate):
        raise OSError("libtorch_global_deps.so: not found")

    result = second_opinion(
        np.zeros(100), 16000, np.array([60.0]), detector=broken
    )

    assert result["compared"] == 0
    assert "could not be run" in describe_comparison(result)


def test_availability_never_raises_whatever_is_installed():
    """
    Asked before anything else runs, so it has to answer
    rather than throw.
    """

    assert crepe_available() in ("torchcrepe", "crepe", None)