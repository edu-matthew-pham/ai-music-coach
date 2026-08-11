# pitch_witness.py

"""
A second opinion on what pitch was sung.

pYIN finds a pitch by looking for repetition in the
waveform. That is exact when the note's own frequency is
present, and guesswork when it is not: a small microphone
rolls off the bottom of a low voice, and what arrives is
the harmonics above a fundamental that is barely there.
Every one of those harmonics is a whole multiple of the
note an octave up as well, so an octave error is not a
bug in the method - it is the honest answer to a question
the recording no longer contains enough to settle.

CREPE was trained on recordings rather than derived from
first principles, so it can infer the missing fundamental
from the shape of what is above it, the way an ear does
with a bass line through a phone speaker.

Which is better on a particular voice through a particular
microphone is not knowable from either description. So
this module runs the second detector alongside the first
and records where they differ, rather than replacing
anything. The disagreements are the data; the decision
comes later, with evidence.

The second detector is optional. The app is complete
without it: with no backend installed the witness reports
that it has no opinion and everything else carries on.

Two backends are recognised. torchcrepe is the one to
install - it is the same model with its weights converted
onto PyTorch, which this app already depends on:

    pip install torchcrepe

The original crepe package is also accepted, but it
carries TensorFlow, which is a large addition and has no
wheels for some recent Pythons.
"""

import numpy as np


# The smallest difference worth reporting. Below this the
# two detectors are describing the same note, and a singer
# does not need telling that two machines disagree by less
# than they can hear.
NOTICEABLE_CENTS = 50

# An octave, in MIDI numbers and in cents.
OCTAVE = 12

# The range asked of the second detector. Wide enough for
# a low voice and for anything the app would draw, rather
# than a speech range that would rule out the bottom notes
# this exists to check.
FLOOR_HZ = 65.0
CEILING_HZ = 1200.0

# Below this the detector is reporting a pitch for silence,
# which is not an opinion worth keeping.
CONFIDENT_ENOUGH = 0.5


def crepe_available():
    """
    Which second detector, if any, can be asked.

    Returns the name of the backend found, or None. Two
    exist because they are the same model reached by
    different roads: crepe carries TensorFlow, torchcrepe
    carries the converted weights on PyTorch, which this
    app already has. torchcrepe is preferred for that
    reason alone - it is a dependency we are not adding.
    """

    # Not only ImportError. A backend can be present and
    # still unusable - a half-installed torch raises an
    # OSError about a missing shared library when it is
    # imported, and a witness that cannot be asked must
    # report that rather than take the judging down with
    # it. Nothing here is load-bearing enough to be worth
    # an exception.
    try:
        import torchcrepe  # noqa: F401

        return "torchcrepe"

    except Exception:
        pass

    try:
        import crepe  # noqa: F401

        return "crepe"

    except Exception:
        return None


def torchcrepe_pitch(sound, sample_rate, model="tiny"):
    """
    torchcrepe's opinion, as MIDI numbers.

    The same shape as trace_pitch returns - times and MIDI
    numbers, NaN where nothing was sounding - so the two
    can be compared frame for frame.

    Its default decoding is not the original CREPE's: it
    follows the most likely path through the frames rather
    than taking the loudest answer in each, which exists
    precisely to stop the octave jumps we are here to
    measure. That makes it a better second opinion for
    this question and a slightly different model from the
    published one, which is worth remembering when reading
    a disagreement.
    """

    import numpy as np
    import torch
    import torchcrepe

    audio = torch.tensor(
        np.asarray(sound, dtype=np.float32)
    ).unsqueeze(0)

    # Five milliseconds, near enough to the frames pYIN
    # returns for the two to line up without resampling.
    hop_length = int(sample_rate / 200.0)

    pitch, periodicity = torchcrepe.predict(
        audio,
        sample_rate,
        hop_length,
        fmin=FLOOR_HZ,
        fmax=CEILING_HZ,
        model=model,
        return_periodicity=True,
        batch_size=512
    )

    frequencies = pitch.squeeze(0).numpy()
    confidence = periodicity.squeeze(0).numpy()

    times = np.arange(len(frequencies)) * hop_length / sample_rate

    midi = np.full(len(frequencies), np.nan)

    for frame in range(len(frequencies)):

        if confidence[frame] < CONFIDENT_ENOUGH:
            continue

        if frequencies[frame] <= 0:
            continue

        midi[frame] = 69 + 12 * np.log2(
            frequencies[frame] / 440.0
        )

    return times, midi


def crepe_pitch(sound, sample_rate, model="tiny"):
    """
    CREPE's opinion of a recording, as MIDI numbers.

    Returns times and MIDI numbers the same shape as
    trace_pitch returns, with NaN where nothing was
    sounding, so the two can be compared frame for frame
    and drawn on the same axis.

    The tiny model is the default deliberately: the point
    here is a second opinion on octaves, which the small
    model settles as well as the large one, and the large
    one is a download nobody asked for.
    """

    import crepe

    times, frequencies, confidence, _ = crepe.predict(
        sound,
        sample_rate,
        model_capacity=model,
        viterbi=True,
        verbose=0
    )

    midi = np.full(len(frequencies), np.nan)

    for frame in range(len(frequencies)):

        if confidence[frame] < CONFIDENT_ENOUGH:
            continue

        if frequencies[frame] <= 0:
            continue

        midi[frame] = 69 + 12 * np.log2(
            frequencies[frame] / 440.0
        )

    return times, midi


def octaves_apart(first, second):
    """
    How many whole octaves separate two MIDI numbers.

    Nought when they are not a whole number of octaves
    apart, which is the ordinary case of two detectors
    disagreeing about tuning rather than about which note
    was sung.
    """

    if first is None or second is None:
        return 0

    if np.isnan(first) or np.isnan(second):
        return 0

    difference = second - first

    nearest = round(difference / OCTAVE)

    if nearest == 0:
        return 0

    # Only if the difference really is close to that many
    # octaves, rather than a large disagreement that
    # happens to be nearby.
    if abs(difference - nearest * OCTAVE) > 1.0:
        return 0

    return nearest


def compare_traces(first_midi, second_midi):
    """
    Where two pitch traces agree, and how they differ.

    Compared frame by frame over the frames both detectors
    called voiced, because a disagreement about whether
    anything was sounding is a different question from a
    disagreement about what note it was.

    Returns a dictionary: how many frames were compared,
    the median difference in cents, how many frames sit a
    whole octave apart, and which way.
    """

    first = np.asarray(first_midi, dtype=float)
    second = np.asarray(second_midi, dtype=float)

    length = min(len(first), len(second))

    first = first[:length]
    second = second[:length]

    both = ~np.isnan(first) & ~np.isnan(second)

    compared = int(np.count_nonzero(both))

    if compared == 0:
        return {
            "compared": 0,
            "median_cents": None,
            "octave_frames": 0,
            "octave_direction": 0,
            "agrees": None
        }

    differences = second[both] - first[both]

    octaves = np.array([
        octaves_apart(a, b)
        for a, b in zip(first[both], second[both])
    ])

    disagreeing = octaves[octaves != 0]

    direction = 0

    if len(disagreeing):
        direction = int(np.sign(np.median(disagreeing)))

    median_cents = float(np.median(differences) * 100)

    return {
        "compared": compared,
        "median_cents": median_cents,
        "octave_frames": int(np.count_nonzero(octaves)),
        "octave_direction": direction,
        "agrees": abs(median_cents) < NOTICEABLE_CENTS
    }


def describe_comparison(comparison):
    """
    The comparison in words, for the feedback.

    Says what the second detector heard and leaves the
    conclusion open: neither detector is the truth, and
    which one to believe on a given microphone is the
    thing being gathered evidence for.
    """

    if comparison is None:
        return (
            "Second opinion: no detector installed. "
            "pip install torchcrepe to enable it."
        )

    if comparison.get("failed"):
        return (
            "Second opinion: the detector could not be "
            "run. The judging above is unaffected."
        )

    if comparison["compared"] == 0:
        return (
            "Second opinion: no frames where both "
            "detectors heard a pitch."
        )

    octave_frames = comparison["octave_frames"]

    share = octave_frames / comparison["compared"]

    if share > 0.2:

        direction = (
            "higher" if comparison["octave_direction"] > 0
            else "lower"
        )

        return (
            f"Second opinion: disagrees on {share:.0%} of "
            f"frames, hearing the part an octave {direction}. "
            f"A small microphone loses the bottom of a low "
            f"voice, which is exactly when this happens - "
            f"the Octave setting is there for it."
        )

    if comparison["agrees"]:
        return (
            f"Second opinion: agrees, within "
            f"{abs(comparison['median_cents']):.0f} cents "
            f"across {comparison['compared']} frames."
        )

    return (
        f"Second opinion: differs by "
        f"{comparison['median_cents']:+.0f} cents across "
        f"{comparison['compared']} frames, but not by an "
        f"octave."
    )


def second_opinion(sound, sample_rate, first_midi,
                   detector=None):
    """
    Ask the second detector and compare it with the first.

    The detector can be passed in, which is how this is
    tested without the package present and how another
    detector could be tried later. Given none, CREPE is
    used if it is installed, and None comes back if it is
    not: an absent witness is not an error.
    """

    if detector is None:

        backend = crepe_available()

        if backend is None:
            return None

        detector = (
            torchcrepe_pitch if backend == "torchcrepe"
            else crepe_pitch
        )

    try:
        times, second_midi = detector(sound, sample_rate)

    except Exception as problem:

        # The same reasoning at the point of use: a second
        # opinion that fails is an absent second opinion,
        # not a failed comparison. What the judging says
        # about the singing does not depend on it.
        return {
            "compared": 0,
            "median_cents": None,
            "octave_frames": 0,
            "octave_direction": 0,
            "agrees": None,
            "failed": str(problem)
        }

    return compare_traces(first_midi, second_midi)