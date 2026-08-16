"""
A score is printed once and played in the order its repeats
say.

These pin the unfolding step in import_musicxml: what
happens to notes, words, beats and feedback when a score has
repeats, endings, a D.C. or a D.S. - and what happens when
its markings are something the expander cannot make sense of.

Each fixture proves one thing. The real ones come from
music21's own bundled corpus (public-domain compositions,
provenance in tests/fixtures/musicxml/README.md); the two
synthetic ones exist for cases no real file in hand shows.
Every number asserted here was measured on the file first,
not derived from a rule.
"""

import os
from fractions import Fraction

import pytest

FIXTURES = os.path.join(
    os.path.dirname(__file__), "fixtures", "musicxml"
)


def fixture(name):
    return os.path.join(FIXTURES, name)


def imported(name, label="0", verse=1):
    from musicxml_import import import_musicxml

    return import_musicxml(fixture(name), label, verse)


def beats(durations):
    return sum(float(Fraction(d)) for d in durations.split())


# --- unfolded ---------------------------------------------------


def test_a_dal_segno_al_fine_is_played_back_to_the_fine():
    """
    Handel, Lascia ch'io pianga: 174 beats printed, 264
    played, and the second pass is the stretch from the segno
    to the Fine, sung again - the same syllables in the same
    order.

    231, not 232: one measure (10) briefly splits into two
    voices - a doubled note with no lyric, ordinary divisi,
    not a second sung line - and the melody-reading loop used
    to flatten it in as an extra note. Read apart, that note
    is correctly not part of the sung line. Total beats (264)
    are unaffected; only the note/syllable count moves.
    """

    pitches, durations, lyrics, bpm, feedback, chart, poly, key = (
        imported("Lascia_chio_pianga.mxl")
    )

    assert "Repeats unfolded (D.S. al Fine)" in feedback
    assert "174 beats printed, 264 played" in feedback

    syllables = lyrics.split()

    # One syllable token per sung note, on both passes.
    assert len(syllables) == 231

    # The second pass (66 notes) is a contiguous stretch of
    # the first, word for word - the segno to the Fine.
    second = syllables[165:]
    first = syllables[:165]

    assert any(
        first[start:start + len(second)] == second
        for start in range(len(first) - len(second) + 1)
    )


def test_a_restated_key_at_the_segno_is_not_a_change():
    """
    The D.S. lands on a bar carrying the same key signature
    already in force; unfolded, that signature is seen twice.
    Only genuine changes are reported.
    """

    key = imported("Lascia_chio_pianga.mxl")[7]

    assert key == "A, D from beat 48"


def test_a_da_capo_unfolds_every_part_to_the_same_length():
    """
    Beethoven Op. 59 No. 2, third movement: two repeats with
    endings and a plain D.C., on all four parts. The whole
    score is unfolded at once, so every part comes back the
    same length; and the D.C. is consumed by the unfolding,
    not left behind as an unplaced mark.
    """

    from musicxml_import import parts_in

    labels = parts_in(fixture("movement3.mxl"))
    assert len(labels) == 4

    played = {
        round(beats(imported("movement3.mxl", label)[1]), 2)
        for label in labels
    }

    assert len(played) == 1

    feedback = imported("movement3.mxl")[4]

    assert "Repeats unfolded (2 repeats with 4 endings, D.C.)" in feedback
    assert "could not" not in feedback


def test_a_da_capo_written_as_words_is_read_and_words_travel_with_it():
    """
    Synthetic: "D.C. al Fine" as plain text, no <sound> tag,
    and word ends written as trailing spaces (the printing
    convention). The score plays C D E F, then C D E again;
    "hap py" is hyphenated on both passes, because the word
    end is stamped on the syllable before unfolding, not
    looked up by position in the printed text.
    """

    pitches, durations, lyrics, bpm, feedback, chart, poly, key = (
        imported("synthetic-dc-al-fine.xml")
    )

    assert pitches.split() == ["C4", "D4", "E4", "F4", "C4", "D4", "E4"]
    assert lyrics.split() == ["hap-", "py", "day", "song", "hap-", "py", "day"]
    assert "Repeats unfolded (D.C. al Fine): 12 beats printed, 20 played" in feedback


# --- refused or dropped ------------------------------------------


def test_markup_the_expander_rejects_falls_back_to_the_printed_order():
    """
    Beethoven Op. 132: repeats, endings and a D.C. al Fine,
    with an ending bracket the file never opens. The expander
    refuses; the import keeps the printed order, once through,
    and says so, naming the first bar past which the numbers
    stop matching a performance.

    3628, not this quartet's printed 3747: Violin I genuinely
    divides into two voices in 40 measures (real double-stops,
    not a file error), and the melody-reading loop used to
    flatten both together, inflating the total. Read apart -
    see test_the_bridges_two_voices_are_read_apart, the same
    fix, found on Mulan and general to every part - the total
    drops to what one voice actually plays. This test cares
    about the refusal shape, not this number; it is pinned so
    a future change to voice-reading has to look at this file
    too, not because 3628 means anything on its own.
    """

    pitches, durations, lyrics, bpm, feedback, chart, poly, key = (
        imported("opus132.mxl")
    )

    assert "could not be unfolded" in feedback
    assert "D.C. al Fine" in feedback
    assert "imported as printed, once through" in feedback
    assert "after bar 265" in feedback

    # Once through, one voice: the printed length of Violin I's
    # own line, not the two voices' flattened-together total.
    assert beats(durations) == 3628.0


def test_a_broken_ending_bracket_is_a_refusal_not_a_crash():
    """
    Haydn Op. 74 No. 1, third movement: an <ending> with no
    number and no start. Genuinely broken markup from the
    encoder, checked in the raw XML - not the expander being
    strict. Same fallback shape as above.
    """

    feedback = imported("haydn_opus74no1_movement3.mxl")[4]

    assert "repeat markings (3 repeats with 2 endings)" in feedback
    assert "could not be unfolded" in feedback
    assert "after bar 14" in feedback


def test_a_navigation_mark_the_expander_drops_is_named():
    """
    Synthetic: one repeat plus two D.C. directives. music21
    unfolds the repeat and ignores both D.C.s with no error -
    checked, not assumed. The import notices, because a
    D.C. it honoured is consumed and one it dropped is left
    behind, and says which happened.
    """

    pitches, durations, lyrics, bpm, feedback, chart, poly, key = (
        imported("synthetic-repeat-two-dc.xml")
    )

    assert pitches.split() == ["C4", "C4", "D4", "E4"]
    assert "Repeats unfolded (1 repeat, D.C.): 12 beats printed, 16 played" in feedback
    assert "The D.C. could not be placed and was left as printed" in feedback


# --- nothing to unfold -------------------------------------------


def test_a_score_with_no_repeats_says_nothing_about_them():
    """
    O Holy Night: no repeat marks at all. No sentence about
    unfolding, no sentence about refusing.
    """

    feedback = imported("o-holy-night-satb.mxl", "1")[4]

    assert "unfold" not in feedback
    assert "once through" not in feedback


# --- two voices in one staff -------------------------------------


def test_the_bridges_two_voices_are_read_apart():
    """
    Mulan's bridge (raw measures 31-34, played from beat
    172.5 once the repeat is unfolded) is real polyphony in
    one staff: the main line continues while the men's
    chorus answers "Be a man" underneath, in a second voice.
    Read as one flattened stream - the way a part with no
    voices is read - the two lines' notes and rests interleave
    into neither line: wrong durations, and notes from the
    wrong line landing where the other line was holding one,
    for everything after the first such measure.

    parts_in() offers each singing voice as its own entry, in
    the same list import_musicxml selects from; the main line
    is read clean once split apart from what was under it.
    """

    from musicxml_import import parts_in, import_musicxml

    labels = parts_in(fixture("mulan-ill-make-a-man-out-of-you.mxl"))

    assert labels[0].startswith("0  Soprano,")
    assert labels[1] == "1  Soprano, second voice, 22 notes, 16 with words"

    pitches, durations, lyrics, bpm, feedback, chart, poly, key = (
        imported("mulan-ill-make-a-man-out-of-you.mxl", labels[0])
    )

    beat = 0.0
    at_beat = {}
    for pitch, length in zip(pitches.split(), durations.split()):
        at_beat[round(beat, 2)] = pitch
        beat += float(Fraction(length))

    # The main line through the bridge, at its played position -
    # clean, not interleaved with the second voice underneath it.
    assert at_beat[171.5] == "C5"
    assert at_beat[172.5] == "B4"
    assert at_beat[173.5] == "A4"
    assert at_beat[174.5] == "G4"


def test_the_second_voice_carries_its_own_real_words():
    """
    The chorus's "Be a man" is real, sung text - not decoration
    to discard. It is marked in the file as verse 2 of the
    second voice (verse 1 there is nearly all held notes,
    underscore tokens, with one "Be a man!" of its own near the
    end) - the same numbered-verse mechanism the app already
    uses for a carol's several verses, reused here rather than
    invented.
    """

    from musicxml_import import verses_in, import_musicxml

    label = "1  Soprano, second voice, 22 notes, 16 with words"

    assert verses_in(fixture("mulan-ill-make-a-man-out-of-you.mxl"), label) == [1, 2]

    pitches, durations, lyrics, bpm, feedback, chart, poly, key = (
        imported("mulan-ill-make-a-man-out-of-you.mxl", label, verse=2)
    )

    assert "Be a man" in lyrics
    assert lyrics.count("Be a man") >= 3


def test_an_unlyriced_second_voice_does_not_clutter_the_part_list():
    """
    Mulan's two piano parts also split into voices in several
    measures - ordinary two-hand engraving, not a second sung
    line. Neither hand carries a lyric, so parts_in() offers
    each piano part once, not twice: a voice split is only
    worth surfacing as a choice when there is a real second
    thing to choose.
    """

    from musicxml_import import parts_in

    labels = parts_in(fixture("mulan-ill-make-a-man-out-of-you.mxl"))

    piano_labels = [label for label in labels if "Piano" in label]

    assert len(piano_labels) == 2
    assert not any("voice" in label for label in piano_labels)





def test_a_key_change_is_read_at_its_beat_on_a_real_score():
    """
    Haydn Op. 74 No. 1: C major to A major at beat 180.0 of
    a 3/4 movement - bar 61. Measured on the file. (The
    score's repeats are refused, above, so these are printed
    beats.)
    """

    pitches, durations, lyrics, bpm, feedback, chart, poly, key = (
        imported("haydn_opus74no1_movement3.mxl")
    )

    assert key == "C, A from beat 180"
    assert "to A major at bar 61" in feedback


def test_the_mulan_gate():
    """
    The file this whole plan started from. Measured by hand,
    before any code: 296 beats printed, 348 played (a
    52-beat repeat, measures 3-15, played twice into two
    different endings), and a key change at beat 208, not
    the old, wrong 156 a raw walk gave it.

    This is the same fixture test_music.py's
    test_harmony_respects_a_real_key_change and
    test_a_zero_semitone_transpose_of_a_modulating_piece_is_a_no_op
    use - both were silently skipping (a stale hardcoded
    Only the feedback sentence and the key are asserted here,
    not the returned duration total: Mulan genuinely uses two
    voices in one staff in several measures (real notation,
    not a file error - checked in the score directly), which
    a separate, pre-existing bug in the note-reading loop
    double-counts. Confirmed pre-existing, not caused by this
    change: the same inflation (296 real beats read as 320)
    happens on the raw, unexpanded score too. Out of scope
    here - the "several voices in one staff" corner the
    module's own docstring already names, now with a real
    fixture proving it wrong. Its own item.
    """

    from musicxml_import import parts_in

    path = fixture("mulan-ill-make-a-man-out-of-you.mxl")
    label = parts_in(path)[0]

    pitches, durations, lyrics, bpm, feedback, chart, poly, key = (
        imported("mulan-ill-make-a-man-out-of-you.mxl", label)
    )

    assert "1 repeat with 2 endings" in feedback
    assert "296 beats printed, 348 played" in feedback
    assert key == "G, Ab from beat 208"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Pre-existing, unrelated to unfolding: a length in "
        "this file reaches the duration writer as a float, "
        "not a Fraction. Its own item; this pins that it is "
        "still open."
    ),
)
def test_a_real_transposing_part_imports():
    """
    Weber, Concertino for clarinet: a real Bb part (M2). The
    fixture is here for the read path; the import currently
    raises on it before anything about repeats runs.
    """

    imported("weber_concertino_clarinet.mxl")