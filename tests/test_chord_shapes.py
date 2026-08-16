"""
The shape mode shows one concrete place to put the hand,
not every place a chord's notes occur - guitar_shape_frets
and piano_shape_for are the data; shape_overlay_for is the
picture built from it, stacking on the same structure the
scale and chord-notes layers already share.
"""

import re

import pytest

from instrument_diagrams import (
    guitar_shape_frets,
    piano_shape_for,
    shape_overlay_for,
    structure_for,
    violin_shape_strings,
)


# Real, standard guitar chord shapes, fret per string low E
# to high e (None for muted). These are the shapes any
# guitar teacher or songbook would show - not a guess this
# app is making up.
KNOWN_SHAPES = {
    ("C", ""): [None, 3, 2, 0, 1, 0],
    ("D", ""): [None, None, 0, 2, 3, 2],
    ("G", ""): [3, 2, 0, 0, 0, 3],
    ("E", ""): [0, 2, 2, 1, 0, 0],
    ("A", ""): [None, 0, 2, 2, 2, 0],
    ("E", "m"): [0, 2, 2, 0, 0, 0],
    ("A", "m"): [None, 0, 2, 2, 1, 0],
    ("D", "m"): [None, None, 0, 2, 3, 1],
    ("E", "7"): [0, 2, 0, 1, 0, 0],
    ("A", "7"): [None, 0, 2, 0, 2, 0],
    ("C", "7"): [None, 3, 2, 3, 1, 0],
    ("D", "7"): [None, None, 0, 2, 1, 2],
    ("G", "7"): [3, 2, 0, 0, 0, 1],
    # Barre chords: the standard shape, not a fallback -
    # these are correctly harder, and the diagram should
    # say so honestly.
    ("F", ""): [1, 3, 3, 2, 1, 1],
    ("B", "m"): [None, 2, 4, 4, 3, 2],
    ("Bb", ""): [None, 1, 3, 3, 3, 1],
    ("F#", ""): [2, 4, 4, 3, 2, 2],
}


@pytest.mark.parametrize("root,quality", KNOWN_SHAPES.keys())
def test_a_shape_matches_the_standard_chord_diagram(root, quality):

    result = guitar_shape_frets(root, quality)

    assert result is not None

    frets, _ = result

    assert [fret for fret, _finger in frets] == KNOWN_SHAPES[(root, quality)]


def test_barre_chords_are_drawn_at_the_correct_fret():
    """
    F is the classic first barre chord, at fret 1 with the
    E-shape. Drawing it honestly - rather than skipping to
    an easier voicing - is the point: the difficulty is
    real, and a beginner should see it.
    """

    frets, barre = guitar_shape_frets("F", "")

    assert barre == 1
    assert frets[0] == (1, 1)  # the barre itself, finger 1


def test_true_opens_are_not_generated_from_the_barre_formula():
    """
    C, D, and G have their own idiosyncratic open fingerings
    that the movable-shape maths would not reproduce (the
    formula would offer a barre shape further up the neck
    instead) - these are hand-written because a beginner
    songbook shows the open shape, not the barre one.
    """

    frets, barre = guitar_shape_frets("C", "")

    assert barre is None
    assert [fret for fret, _finger in frets] == KNOWN_SHAPES[("C", "")]


def test_a_quality_with_no_standard_shape_is_reported_honestly():
    """
    maj7 is outside the four qualities this covers. A
    guessed fingering would be worse than saying nothing -
    the same choice invariant 6 makes anywhere else a guess
    would cost more than a gap.
    """

    assert guitar_shape_frets("C", "maj7") is None
    assert guitar_shape_frets("C", "dim") is None
    assert guitar_shape_frets("C", "sus4") is None


def test_the_higher_position_exists_for_every_shape_the_lower_one_does():
    """
    guitar_shape_frets_higher tracks guitar_shape_frets's own
    "no standard shape" gap (invariant 6) rather than adding
    a second, different one - a quality guitar_shape_frets
    declines has no higher position to offer either.
    """

    from instrument_diagrams import guitar_shape_frets_higher

    assert guitar_shape_frets_higher("C", "maj7") is None
    assert guitar_shape_frets_higher("C", "dim") is None
    assert guitar_shape_frets_higher("C", "sus4") is None

    assert guitar_shape_frets_higher("C", "") is not None


def test_the_higher_position_is_always_a_real_gap_above_the_lower_one():
    """
    Checked against all 48 root/quality combinations this app
    draws: the higher position never sits adjacent to or on
    top of the lower one, and never needs more than fret 13 -
    the number the guitar entry in INSTRUMENTS was widened to
    fit. A collapsed or missing gap would mean the two
    positions aren't a genuine second hand-shape at all.
    """

    from instrument_diagrams import guitar_shape_frets_higher

    roots = ["C", "Db", "D", "Eb", "E", "F", "F#",
             "G", "Ab", "A", "Bb", "B"]
    qualities = ["", "m", "7", "m7"]

    highest_fret_seen = 0

    for root in roots:
        for quality in qualities:

            lower_frets, _ = guitar_shape_frets(root, quality)
            higher_frets, _ = guitar_shape_frets_higher(root, quality)

            lower_top = max(
                f for f, _ in lower_frets if f is not None
            )
            higher_bottom = min(
                f for f, _ in higher_frets
                if f is not None and f > 0
            )
            higher_top = max(
                f for f, _ in higher_frets if f is not None
            )

            assert higher_bottom - lower_top >= 1
            highest_fret_seen = max(highest_fret_seen, higher_top)

    assert highest_fret_seen == 13


def test_the_piano_shape_is_root_and_fifth_against_the_triad():
    """
    Left hand: root and fifth. Right hand: the triad in
    root position. C major - left hand C and G, right hand
    C-E-G.
    """

    left_hand, right_hand = piano_shape_for("C", "")

    assert left_hand == [(0, 5), (7, 1)]
    assert right_hand == [(0, 1), (4, 3), (7, 5)]


def test_the_piano_shape_drops_extensions_for_the_right_hand():
    """
    G7's right hand is still the plain G major triad - the
    seventh is left out of the beginner shape the same way
    a detected chart's chord names stay plain: a simpler
    shape a beginner can actually play is worth more than
    an exact one they cannot.
    """

    _, right_hand = piano_shape_for("G", "7")

    semitones = {semitone for semitone, _finger in right_hand}

    assert semitones == {7, 11, 2}  # G, B, D - not the F


def test_every_piano_shape_mark_actually_renders():
    """
    piano_shape_for's data was correct the whole time this
    bug existed - the drawing function silently dropped
    every right-hand mark, because its own lookup table for
    "where is this semitone on the keyboard" only covered
    one octave while the right hand is drawn an octave above
    the left. A data test alone could not have caught this;
    only counting what the picture actually contains does.
    """

    from instrument_diagrams import (
        LEFT_HAND_COLOUR, SHAPE_COLOUR, shape_overlay_for
    )

    shape = shape_overlay_for("C", "Piano", "C")

    assert shape.count("<circle") == 5
    assert shape.count(LEFT_HAND_COLOUR) == 2
    assert shape.count(SHAPE_COLOUR) == 3


def test_a_shape_overlay_stacks_on_the_same_structure():
    """
    The whole point of a shape overlay is landing exactly
    on the instrument picture underneath it.
    """

    for instrument in ("Piano", "Guitar"):

        structure = structure_for(instrument)
        shape = shape_overlay_for("C", instrument, "C")

        structure_box = re.search(r'viewBox="([^"]+)"', structure).group(1)
        shape_box = re.search(r'viewBox="([^"]+)"', shape).group(1)

        assert structure_box == shape_box


def test_violin_both_positions_now_shows_two_genuine_shapes():
    """
    A double stop now has a real second, higher-position
    variant (violin_shape_strings_higher, searched within
    third position's own frame) - a genuine second hand
    shape, not first position's shape re-shown, the same way
    guitar and ukulele's barre shapes combine two real
    positions. "Violin, both positions" draws both, using
    SHAPE_COLOUR and HIGHER_SHAPE_COLOUR the same way the
    fretted instruments already do.
    """

    from instrument_diagrams import SHAPE_COLOUR, HIGHER_SHAPE_COLOUR

    first = shape_overlay_for("C", "Violin, first position", "C")
    both = shape_overlay_for("C", "Violin, both positions", "C")

    assert first is not None
    assert both is not None
    assert first != both
    assert SHAPE_COLOUR in both
    assert HIGHER_SHAPE_COLOUR in both


def test_violin_higher_position_covers_every_chord_with_a_real_third():
    """
    Every one of the app's 24 root/quality combinations finds
    a genuine double stop within third position's own frame,
    and every one uses a real third rather than falling back
    to a fifth - checked against actual chord tones, not just
    that a fret number exists.
    """

    from instrument_diagrams import (
        violin_shape_strings_higher, VIOLIN_STRINGS, NOTE_SEMITONES,
        _note_at
    )
    from chords import CHORD_QUALITIES

    for root in ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]:
        for quality in ["", "m"]:

            shaped = violin_shape_strings_higher(root, quality)
            assert shaped is not None, f"{root}{quality} has no higher position"

            low_i, low_f, high_i, high_f = shaped

            sounded = {
                _note_at(VIOLIN_STRINGS[low_i], low_f) % 12,
                _note_at(VIOLIN_STRINGS[high_i], high_f) % 12,
            }

            root_st = NOTE_SEMITONES[root] % 12
            third_interval = CHORD_QUALITIES[quality][1]
            third_st = (root_st + third_interval) % 12

            assert root_st in sounded, f"{root}{quality} is missing its own root"
            assert third_st in sounded, f"{root}{quality} fell back to a fifth"


def test_an_unsupported_quality_falls_back_to_nothing_not_an_error():
    """
    The caller (the mixer's diagram panel) is expected to
    fall back to the all-positions chord overlay when this
    returns None - it should never raise for a chord this
    app otherwise knows how to play.
    """

    assert shape_overlay_for("C", "Guitar", "Cmaj7") is None
    assert shape_overlay_for("C", "Guitar", "Cdim") is None
    assert shape_overlay_for("C", "Guitar", "Csus4") is None


def test_piano_covers_every_quality_a_triad_voicing_can_represent():
    """
    Unlike guitar, where a shape is only "standard" for the
    handful of qualities a songbook actually teaches, a
    root-position triad in fingers 1-3-5 is a genuinely
    uniform, playable voicing for any quality with a real
    triad underneath it - dim and aug included. Piano's
    wider coverage than guitar's is a real difference
    between the instruments, not an inconsistency.
    """

    for quality in ("dim", "aug", "sus2", "sus4", "6", "m6", "maj7"):
        assert shape_overlay_for("C", "Piano", "C" + quality) is not None


def test_a_muted_string_is_visibly_marked_not_silently_skipped():
    """
    C major on guitar mutes its low E string. That string
    has to show up as visibly different in the shape layer -
    a player reading the shape needs to know not to strum it,
    and a string that just has no dot on it looks identical
    to an open one. Was a margin "X" (standard chart
    notation), then a faded line the full length of the
    string; now a red X mark at the nut, the same spot and
    size class as the open-string ring, so "don't play this"
    is one definite mark in the place a player already looks,
    not a change of state spread the whole neck. Whatever the
    exact mark, the invariant holds: a muted string is
    marked, not dropped.
    """

    shape = shape_overlay_for("C", "Guitar", "C")

    from instrument_diagrams import MUTED_COLOUR

    assert shape.count(f'stroke="{MUTED_COLOUR}"') == 2
    assert ">X</text>" not in shape


def test_an_open_string_is_a_hollow_ring_at_the_nut():
    """
    D minor on guitar plays its D string open. That's a note
    that sounds with no finger down - drawn as a hollow ring
    on the string right at the nut, the same place and size
    class as a fretted dot, outlined instead of filled. Same
    visual language as the fretted marks beside it rather
    than a margin "O": one kind of mark for "a note sounds
    here", filled or not depending on whether a finger is
    involved.
    """

    shape = shape_overlay_for("C", "Guitar", "Dm")

    assert 'fill="none" stroke="#6a1b9a"' in shape
    assert ">O</text>" not in shape


def test_the_shape_layer_never_shares_a_colour_with_chord_notes():
    """
    Scale, Chord notes and Chord shape are independent
    layers that can all be shown together - useful for
    seeing every place a chord's notes fall on the neck or
    keyboard alongside the one beginner voicing, for working
    out an arpeggio or right-hand accompaniment beyond the
    fixed shape. If the two chord layers shared a colour, a
    shape mark would sit invisibly on top of a matching
    chord-notes mark exactly where the two are meant to be
    told apart.
    """

    from instrument_diagrams import CHORD_TONE_COLOUR, SHAPE_COLOUR

    assert SHAPE_COLOUR != CHORD_TONE_COLOUR

    guitar_shape = shape_overlay_for("C", "Guitar", "C")
    assert CHORD_TONE_COLOUR not in guitar_shape

    piano_shape = shape_overlay_for("C", "Piano", "C")
    assert CHORD_TONE_COLOUR not in piano_shape


def test_every_layer_that_can_show_together_has_its_own_colour():
    """
    The same collision that made a shape mark invisible on
    top of a chord-notes mark once already happened a second
    time with Scale, which is on the same instrument picture
    and can be shown alongside Chord shape too. Checking the
    whole set together, rather than one pair at a time, is
    the check that would have caught both.
    """

    from instrument_diagrams import (
        CHORD_TONE_COLOUR,
        HOME_COLOUR,
        IN_KEY_COLOUR,
        LEFT_HAND_COLOUR,
        SHAPE_COLOUR,
    )

    colours = [
        IN_KEY_COLOUR, HOME_COLOUR, CHORD_TONE_COLOUR,
        SHAPE_COLOUR, LEFT_HAND_COLOUR,
    ]

    assert len(colours) == len(set(colours))


# Real, well-known beginner violin double stops - the
# classic "two adjacent open strings, a fifth apart" family,
# and one where the root needs a stopped finger.
KNOWN_VIOLIN_SHAPES = {
    ("D", ""): {"D", "A"},   # open D, open A
    ("G", ""): {"G", "D"},   # open G, open D
    ("A", ""): {"A", "E"},   # open A, open E
}


@pytest.mark.parametrize("root,quality", KNOWN_VIOLIN_SHAPES.keys())
def test_a_violin_shape_matches_a_known_beginner_double_stop(root, quality):
    """
    D, G, and A major each have a real, classic beginner
    double stop: two adjacent strings, both open, a fifth
    apart - root and fifth, no finger needed at all. If the
    algorithm didn't find these, favouring open strings
    would be a claim it doesn't actually keep.
    """

    from instrument_diagrams import VIOLIN_STRINGS

    low_i, low_fret, high_i, high_fret = violin_shape_strings(root, quality)

    assert low_fret == 0
    assert high_fret == 0

    sounding = {
        VIOLIN_STRINGS[low_i][:-1], VIOLIN_STRINGS[high_i][:-1]
    }

    assert sounding == KNOWN_VIOLIN_SHAPES[(root, quality)]


def test_a_violin_shape_always_includes_the_root():
    """
    A double stop without its root does not read as that
    chord - the root has to be one of the two notes, on
    whichever string reaches it.
    """

    from instrument_diagrams import VIOLIN_STRINGS, NOTE_SEMITONES, _note_at

    for root in ["C", "D", "Eb", "F#", "A", "B"]:

        low_i, low_fret, high_i, high_fret = violin_shape_strings(root, "")

        root_semitone = NOTE_SEMITONES[root] % 12

        sounding = {
            _note_at(VIOLIN_STRINGS[low_i], low_fret),
            _note_at(VIOLIN_STRINGS[high_i], high_fret),
        }

        assert root_semitone in sounding


def test_violin_shapes_cover_every_root_and_quality():
    """
    Unlike guitar, where a shape only exists for the
    handful of qualities a songbook actually teaches, every
    root and quality this app supports has a reachable
    double stop within VIOLIN_SHAPE_MAX_FRET on some
    adjacent string pair - a full-coverage result, the same
    kind piano's triad voicing already has and guitar's
    fixed shapes don't.
    """

    from chords import CHORD_QUALITIES

    roots = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]

    for root in roots:
        for quality in CHORD_QUALITIES:
            assert violin_shape_strings(root, quality) is not None


def test_a_violin_shape_stacks_on_the_same_structure():

    structure = structure_for("Violin, first position")
    shape = shape_overlay_for("C", "Violin, first position", "D")

    structure_box = re.search(r'viewBox="([^"]+)"', structure).group(1)
    shape_box = re.search(r'viewBox="([^"]+)"', shape).group(1)

    assert structure_box == shape_box


def test_a_violin_shape_uses_the_shared_shape_colour():

    from instrument_diagrams import CHORD_TONE_COLOUR, SHAPE_COLOUR

    shape = shape_overlay_for("C", "Violin, first position", "D")

    assert SHAPE_COLOUR in shape
    assert CHORD_TONE_COLOUR not in shape


# Every ukulele shape checked against the actual chord tones
# it plays - real evidence the fingering is correct, not
# just documentation of what was typed in.
UKULELE_KNOWN_SHAPES = {
    ("C", ""): [0, 0, 0, 3],
    ("D", ""): [2, 2, 2, 0],
    ("G", ""): [0, 2, 3, 2],
    ("A", "m"): [2, 0, 0, 0],
}


@pytest.mark.parametrize("root,quality", UKULELE_KNOWN_SHAPES.keys())
def test_a_ukulele_shape_matches_the_verified_fingering(root, quality):

    from instrument_diagrams import ukulele_shape_frets

    result = ukulele_shape_frets(root, quality)

    assert result is not None

    frets, _barre = result

    assert [fret for fret, _finger in frets] == UKULELE_KNOWN_SHAPES[(root, quality)]


def test_every_ukulele_shape_plays_the_correct_chord_tones():
    """
    Fret positions checked against the theory module directly,
    the same cross-check guitar's shapes already get - real
    evidence the shape sounds like the chord it's named for,
    independent of whether it happens to be the fingering any
    particular teacher would choose.
    """

    from instrument_diagrams import (
        UKULELE_SHAPES, ukulele_shape_frets, STRING_TUNINGS, _note_at
    )
    from notes import NOTE_SEMITONES
    from chords import chord_semitones

    tuning = STRING_TUNINGS["Ukulele"]

    for root, quality in UKULELE_SHAPES:

        frets, _barre = ukulele_shape_frets(root, quality)

        played = {
            _note_at(string, fret)
            for string, (fret, _finger) in zip(tuning, frets)
        }

        tones = set(chord_semitones(root + quality))

        assert played <= tones, f"{root}{quality} plays a wrong note"

        assert NOTE_SEMITONES[root] % 12 in played, (
            f"{root}{quality} is missing its own root"
        )


def test_a_ukulele_barre_is_finger_one_and_nothing_else_is_guessed():
    """
    Only two finger facts are ever claimed for a ukulele
    shape: open (no finger) and barre (finger 1, wherever
    two or more strings share a fret) - both genuinely
    certain regardless of which teacher is asked. Every
    other fretted note is left as a plain, unlabelled mark,
    since which finger a teacher would choose for it is not
    something this table was ever meant to claim to know.
    """

    from instrument_diagrams import ukulele_shape_frets

    # D major barres three strings at fret 2.
    frets, barre = ukulele_shape_frets("D", "")

    assert barre == 2

    barred = [f for f, finger in frets if f == 2]
    assert len(barred) == 3

    for fret, finger in frets:
        if fret == 0:
            assert finger is None
        elif fret == barre:
            assert finger == 1
        else:
            assert finger is None


def test_ukulele_has_no_shape_for_an_odd_quality_or_unlisted_spelling():
    """
    Every root/quality this app supports (major, minor) now
    has a real shape, across both natural and accidental
    roots - but the table is still a plain string lookup, not
    an enharmonic one: only the spelling actually stored
    ("Gb", not "F#") resolves, and a quality outside major/
    minor was never covered at all.
    """

    from instrument_diagrams import ukulele_shape_frets

    assert ukulele_shape_frets("F#", "") is None
    assert ukulele_shape_frets("C", "maj7") is None
    assert ukulele_shape_frets("Bb", "m") is not None


def test_a_ukulele_shape_stacks_on_the_same_structure():

    structure = structure_for("Ukulele")
    shape = shape_overlay_for("C", "Ukulele", "C")

    structure_box = re.search(r'viewBox="([^"]+)"', structure).group(1)
    shape_box = re.search(r'viewBox="([^"]+)"', shape).group(1)

    assert structure_box == shape_box


def test_ukulele_and_guitar_do_not_share_shape_data():
    """
    Ukulele is not a transposed guitar - the two instruments
    have genuinely different shapes for the same chord name,
    since the tuning itself is different, not just the range.
    """

    from instrument_diagrams import guitar_shape_frets, ukulele_shape_frets

    guitar_c, _ = guitar_shape_frets("C", "")
    ukulele_c, _ = ukulele_shape_frets("C", "")

    assert [f for f, _ in guitar_c] != [f for f, _ in ukulele_c]


def test_guitars_compact_fret_range_fits_every_shape():
    """
    8 is not a round number chosen for looks - it's the
    actual highest fret any guitar shape this app draws
    uses (the Eb family's barre reaches it). A smaller
    compact range would silently cut that shape off
    mid-picture rather than draw it wrong or refuse it,
    which is worse than either.
    """

    from instrument_diagrams import (
        GUITAR_TRUE_OPENS, GUITAR_E_SHAPE, guitar_shape_frets
    )

    roots = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]

    max_fret = 0

    for root in roots:
        for quality in GUITAR_E_SHAPE:
            result = guitar_shape_frets(root, quality)
            if result is None:
                continue
            frets, _barre = result
            for fret, _finger in frets:
                if fret is not None:
                    max_fret = max(max_fret, fret)

    assert max_fret == 8
    assert shape_overlay_for("C", "Guitar, 8 frets", "Eb") is not None


def test_ukuleles_own_range_is_smaller_than_guitars():
    """
    Even with every accidental root added, ukulele's shapes
    never pass fret 6 (Db minor, the one shape that had to
    stand in for a real fingering needing a muted string) -
    still comfortably smaller than guitar's own range, and
    its short scale means a player is less likely to go far
    up the neck at all regardless.
    """

    from instrument_diagrams import (
        UKULELE_SHAPES, ukulele_shape_frets, _frets_shown_for
    )

    max_fret = 0

    for root, quality in UKULELE_SHAPES:
        frets, _barre = ukulele_shape_frets(root, quality)
        for fret, _finger in frets:
            if fret is not None:
                max_fret = max(max_fret, fret)

    assert max_fret == 6

    assert _frets_shown_for("Ukulele, 6 frets") == 6
    assert _frets_shown_for("Ukulele, 10 frets") == 10
    assert _frets_shown_for("Guitar, 8 frets") == 8
    assert _frets_shown_for("Guitar, 13 frets") == 13


def test_ukuleles_higher_position_covers_every_root_it_claims_to():
    """
    Every root/quality ukulele_shape_frets_higher returns a
    shape for lands within the instrument's real 10-fret
    range, at least 3 frets above its own primary shape's
    highest fret, and plays the chord it's named for - checked
    against chord_semitones for the actual tones and root, not
    just that a fret number exists. 17 of the 24 root/quality
    combinations have one; the other 7 are covered by
    test_ukuleles_higher_position_needs_a_genuine_gap.
    """

    from instrument_diagrams import (
        ukulele_shape_frets, ukulele_shape_frets_higher, NOTE_SEMITONES
    )
    from chords import chord_semitones

    tuning = ["G4", "C4", "E4", "A4"]

    def semitone_for(note_name):
        letter = note_name[:-1]
        octave = int(note_name[-1])
        return NOTE_SEMITONES[letter] + 12 * (octave + 1)

    covered = 0

    for root in ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]:
        for quality in ["", "m"]:

            shaped = ukulele_shape_frets_higher(root, quality)
            if shaped is None:
                continue

            covered += 1

            frets, _barre = shaped

            sounded = {
                (semitone_for(open_note) + fret) % 12
                for open_note, (fret, _finger) in zip(tuning, frets)
            }
            expected = {
                semitone % 12 for semitone in chord_semitones(root + quality)
            }

            assert sounded == expected
            assert (NOTE_SEMITONES[root] % 12) in sounded
            assert max(fret for fret, _ in frets) <= 10

            primary, _barre = ukulele_shape_frets(root, quality)
            primary_max = max(fret for fret, _ in primary)
            assert min(fret for fret, _ in frets) - primary_max >= 3

    assert covered == 17


def test_ukuleles_higher_position_needs_a_genuine_gap():
    """
    Not every chord gets a second position - the same
    min-3-fret-gap rule guitar's own E-shape/A-shape choice
    already holds itself to means some roots have nothing
    that clears it within the instrument's real range. B and
    Bm are two of the closed anchors themselves, so nothing
    can shift onto them from elsewhere and still clear the
    gap; the rest are cases where every candidate lands too
    close to the primary shape to count as a genuinely
    different hand position.
    """

    from instrument_diagrams import ukulele_shape_frets_higher

    for root, quality in [
        ("B", ""), ("B", "m"), ("Ab", ""), ("Ab", "m"),
        ("Db", "m"), ("Gb", "m"), ("G", "m"),
    ]:
        assert ukulele_shape_frets_higher(root, quality) is None


def test_the_compact_view_never_draws_a_second_position():
    """
    Widening the guitar fret range and adding a higher
    position must not change anything about the existing
    compact single-position drawing - HIGHER_SHAPE_COLOUR
    should never appear at 8 (guitar) or 6 (ukulele) frets.
    """

    from instrument_diagrams import (
        fretted_chord_shape_overlay, HIGHER_SHAPE_COLOUR
    )

    guitar_compact = fretted_chord_shape_overlay(
        "Eb", "Eb", instrument="Guitar", frets_shown=8
    )
    ukulele_compact = fretted_chord_shape_overlay(
        "C", "C", instrument="Ukulele", frets_shown=6
    )

    assert HIGHER_SHAPE_COLOUR not in guitar_compact
    assert HIGHER_SHAPE_COLOUR not in ukulele_compact


def test_the_full_view_draws_both_positions():
    """
    Guitar's 13-fret view and ukulele's 10-fret view both
    show the higher position alongside the lower one - the
    one case (guitar's Eb family) that needed the fret
    ceiling raised in the first place.
    """

    from instrument_diagrams import (
        fretted_chord_shape_overlay, SHAPE_COLOUR,
        HIGHER_SHAPE_COLOUR
    )

    guitar_full = fretted_chord_shape_overlay(
        "Eb", "Eb", instrument="Guitar", frets_shown=13
    )
    ukulele_full = fretted_chord_shape_overlay(
        "D", "D", instrument="Ukulele", frets_shown=10
    )

    assert SHAPE_COLOUR in guitar_full
    assert HIGHER_SHAPE_COLOUR in guitar_full
    assert SHAPE_COLOUR in ukulele_full
    assert HIGHER_SHAPE_COLOUR in ukulele_full


def test_a_shared_fret_would_draw_a_split_mark_not_two_dots():
    """
    The split-mark drawing logic (_split_fret_dot) is real and
    load-bearing, but no ukulele chord can reach it anymore:
    the min-3-fret-gap rule ukulele_shape_frets_higher now
    holds itself to (see
    test_ukuleles_higher_position_covers_the_shifted_closed_shape)
    guarantees every fret in a higher position sits above
    every fret in the primary shape, so no single string can
    ever land on the same fret in both. That's a genuine
    change from before this session - ukulele's own C major
    used to be the documented example of an overlapping case,
    kept deliberately; the gap rule that fixed several
    too-close "second positions" removed that overlap too, as
    a side effect of the same fix, not a separate choice.

    Real coverage of the split mark itself now lives with
    violin's Scale layer instead, which is structurally
    different (a note is checked per pitch-class reachability
    from each position, not per fret-per-string) and does
    still guarantee overlap for every key - see
    test_violin_both_positions_scale_shows_every_key_with_overlap
    in test_instrument_diagrams.py.
    """

    from instrument_diagrams import _split_fret_dot

    svg = _split_fret_dot(100, 50, "#2e7d32", "#00838f")

    assert "<path" in svg
    assert "#2e7d32" in svg
    assert "#00838f" in svg