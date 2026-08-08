# key_detector.py

"""
Name the key a piece of music is in.

The method is Krumhansl-Schmuckler: listeners rate how well
each of the twelve pitches fits a key, and those ratings
form a profile for major and for minor. The music's own
profile - how much time it spends on each pitch - is
correlated against all twenty four keys, and the best
match is the key it sounds like it is in.

This answers a different question from harmony.py's
keys_containing. That asks which keys the app could build
a harmony in, a strict yes or no per note. This asks what
the music is, which is a matter of degree: a piece in D
minor remains in D minor despite the odd accidental.
"""

from notes import note_to_midi, is_rest


# What each key is conventionally called. Flat keys go by
# their flat names: the key of Bb is never called A#, even
# though the tonic is the same sound.
MAJOR_NAMES = [
    "C", "Db", "D", "Eb", "E", "F",
    "F#", "G", "Ab", "A", "Bb", "B"
]

MINOR_NAMES = [
    "C", "C#", "D", "Eb", "E", "F",
    "F#", "G", "G#", "A", "Bb", "B"
]


# How well each pitch fits a key, from the tonic upward,
# as measured by Krumhansl and Kessler's listening
# experiments. The tonic fits best, the fifth next, and
# the notes outside the scale worst.
MAJOR_PROFILE = [
    6.35, 2.23, 3.48, 2.33, 4.38, 4.09,
    2.52, 5.19, 2.39, 3.66, 2.29, 2.88
]

MINOR_PROFILE = [
    6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
    2.54, 4.75, 3.98, 2.69, 3.34, 3.17
]


def time_on_each_pitch(pitches, durations):
    """
    How many beats the music spends on each of the twelve
    pitches, whichever octave they fall in.
    """

    spent = [0.0] * 12

    for pitch, beats in zip(pitches, durations):

        if is_rest(pitch):
            continue

        spent[note_to_midi(pitch) % 12] += beats

    return spent


def correlation(profile, spent):
    """
    Pearson correlation between a key profile and the time
    the music spends on each pitch.
    """

    count = len(profile)

    mean_profile = sum(profile) / count
    mean_spent = sum(spent) / count

    above = sum(
        (profile[i] - mean_profile) * (spent[i] - mean_spent)
        for i in range(count)
    )

    below_profile = sum(
        (value - mean_profile) ** 2 for value in profile
    ) ** 0.5

    below_spent = sum(
        (value - mean_spent) ** 2 for value in spent
    ) ** 0.5

    if below_profile == 0 or below_spent == 0:
        return 0.0

    return above / (below_profile * below_spent)


def rotate(profile, steps):
    """
    The same profile, started from a different tonic.
    """

    return profile[-steps:] + profile[:-steps]


def detect_key(pitches, durations):
    """
    The keys this music might be in, best match first.

    Returns a list of (name, score) such as
    ("D minor", 0.81), covering all twenty four keys.
    The scores are correlations: close scores mean the
    music genuinely suits either key, which short or
    plain melodies often do.
    """

    spent = time_on_each_pitch(pitches, durations)

    scored = []

    for tonic in range(12):

        scored.append((
            f"{MAJOR_NAMES[tonic]} major",
            correlation(rotate(MAJOR_PROFILE, tonic), spent)
        ))

        scored.append((
            f"{MINOR_NAMES[tonic]} minor",
            correlation(rotate(MINOR_PROFILE, tonic), spent)
        ))

    scored.sort(key=lambda pair: -pair[1])

    return scored


def describe_key(pitches, durations, margin=0.05):
    """
    A sentence naming the music's key, honest about doubt.

    A clear winner is named alone. A near tie is named as
    a pair, since a short melody often genuinely fits two
    keys and picking one would be a guess dressed up as an
    answer.
    """

    scored = detect_key(pitches, durations)

    best_name, best_score = scored[0]
    next_name, next_score = scored[1]

    if best_score - next_score < margin:
        return (
            f"This sounds like {best_name} or {next_name}."
        )

    return f"This sounds like {best_name}."