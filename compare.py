# compare.py

"""
Compare a performance against the music that was intended.

This module does no signal processing and no formatting. It
takes the notes that were asked for and the pitches that were
heard, and reports the distance between them as plain numbers.

Deciding what those numbers mean, and how to show them, is
left to whatever is displaying the result.
"""

from typing import NamedTuple, Optional

from notes import note_to_midi


class NoteComparison(NamedTuple):
    """
    One target note set against what was actually played.

    target            the note that was asked for, such as C4
    target_midi       that note as a MIDI number
    heard             the nearest note to what was played
    heard_cents       how far that was from its own nearest note
    cents_from_target how far the performance was from the
                      target, positive for sharp. This is not
                      limited to half a semitone: a note an
                      octave high reports 1200.
    """

    target: str
    target_midi: int
    heard: Optional[str]
    heard_cents: Optional[float]
    cents_from_target: Optional[float]

    @property
    def was_detected(self):
        """
        Whether any pitch was found for this note at all.

        A note may go undetected because it was not played,
        or because it was too quiet or breathy to measure.
        These two cases look the same from here.
        """

        return self.cents_from_target is not None

    @property
    def is_target_note(self):
        """
        Whether the performance is nearer the target than it
        is to either neighbouring semitone.

        This is the point where the text description stops
        naming the target note and starts naming another one.
        """

        if not self.was_detected:
            return False

        return abs(self.cents_from_target) < 50


def compare_note(target, pitch):
    """
    Compare one target note against one detected pitch.

    pitch may be None when nothing could be detected.
    """

    target_midi = note_to_midi(target)

    if pitch is None:
        return NoteComparison(
            target=target,
            target_midi=target_midi,
            heard=None,
            heard_cents=None,
            cents_from_target=None
        )

    # Distance from the note that was actually asked for,
    # rather than from the nearest note to what was played.
    cents_from_target = (
        pitch.midi - target_midi
    ) * 100

    return NoteComparison(
        target=target,
        target_midi=target_midi,
        heard=pitch.note,
        heard_cents=pitch.cents,
        cents_from_target=cents_from_target
    )


def compare_sequence(targets, pitches):
    """
    Compare a whole performance against the target music.

    The two lists should be the same length. If they are not,
    the shorter one is padded so that every target note still
    appears in the result.
    """

    comparisons = []

    for position in range(len(targets)):

        if position < len(pitches):
            pitch = pitches[position]

        else:
            pitch = None

        comparisons.append(
            compare_note(targets[position], pitch)
        )

    return comparisons


def summarise(comparisons):
    """
    Count up how a performance went.

    Returns the number of notes played on the right pitch,
    the number that were detected at all, the total, and the
    average distance from the target in cents.

    The average ignores undetected notes, because there is
    no distance to average for those.
    """

    detected = [
        comparison for comparison in comparisons
        if comparison.was_detected
    ]

    on_target = [
        comparison for comparison in detected
        if comparison.is_target_note
    ]

    if len(detected) == 0:
        average_error = None

    else:
        total = sum(
            abs(comparison.cents_from_target)
            for comparison in detected
        )

        average_error = total / len(detected)

    return {
        "total": len(comparisons),
        "detected": len(detected),
        "on_target": len(on_target),
        "average_cents_off": average_error
    }
