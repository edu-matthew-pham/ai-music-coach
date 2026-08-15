# chord_detector.py

"""
Work out the chords from the notes.

A chord is what is sounding at once, so a file with more
than one voice already contains its chords: the four parts
of a hymn spell one out on every beat. Nothing has to be
inferred from a melody alone, which is guesswork; this is
reading what is written.

The method is a beat at a time. Every note sounding during
the beat votes, weighted by how long it sounds for, and the
chord whose notes collect the most votes wins. Runs of the
same chord are then joined, which is what turns a list of
beats into a chart with one entry per change.

This reads; chords.py defines. The vocabulary of chords,
what each is made of, and how a chart is written all live
there.
"""

from chords import CHORD_QUALITIES, CHORD_QUALITIES as QUALITIES, SPLIT
from notes import (
    SHARP_NAMES, FLAT_NAMES, FLAT_KEYS, note_to_midi
)


# The chords worth looking for. Kept deliberately short:
# offering every quality invites the detector to explain a
# passing note by calling a plain triad something exotic,
# and a chart full of thirteenths helps nobody practise.
DETECTED_QUALITIES = ["", "m", "7", "m7", "dim"]


# How much a note outside the chord counts against it.
# Passing notes are ordinary and should not veto a chord,
# but a chord that leaves half the music unexplained is
# the wrong chord.
OUTSIDE_PENALTY = 0.6


# The root gets extra credit for being in the bass, since
# that is what the ear uses to name a chord. Not decisive:
# inversions are ordinary, and a passing bass note should
# not rename the harmony.
BASS_BONUS = 0.35


# What it costs to claim a chord whose notes are not all
# sounding. Without this, any triad in first inversion can
# be renamed as a minor chord built on its bass note, a
# chord which happens to share two notes with it and whose
# third is nowhere to be heard. D, F sharp and A over F
# sharp is a D chord, not an F sharp minor missing its
# C sharp.
MISSING_PENALTY = 0.5


# A beat with almost nothing sounding cannot be named, and
# guessing there produces chords nobody played.
QUIET_BEAT = 0.05


# A pitch heard for less than this share of a beat is
# decoration, not harmony. Without a floor, a whisper of a
# note - the tail of a melody line crossing the beat - can
# rename the chord twice over: it fills the fourth tone of
# a seventh chord that would otherwise pay for missing it,
# and if it happens to lie lowest it collects the whole
# bass bonus. On the Wellerman's chorus a C sounding for
# four percent of the beat turned two honest E flat bars
# into C minor sevenths this way, measured against the
# published sheet. Trace notes are dropped before scoring:
# no credit, no penalty, no claim to the bass.
TRACE_FLOOR = 0.05


# What it costs a seventh chord to claim a beat, beyond
# what its four tones already have to earn on their own
# merits. A seventh explains one more tone than the triad
# it contains, so on a beat where that fourth tone is only
# a passing decoration, the seventh's wider net scoops it
# up for free and reports harmony nobody played: measured
# against A Thousand Years' printed sheet, a sung sixth
# over a plain major triad was repeatedly read as a minor
# seventh built a third below - Bb become Gm7, F became
# Dm7, Eb became Cm7 - the same relative-minor mistake
# each time. A seventh still wins when it is genuinely
# there; it must now win outright, not by default.
SEVENTH_COST = 0.1


# How many different notes have to be sounding before a
# chord can be named at all.
#
# One note is not a chord. A bare melody passage will
# happily match some triad containing that note, and the
# answer is confident, arbitrary and wrong. Two notes are
# thin but real: an open fifth is a chord, and hymns do
# reduce to two voices. Below two, the honest answer is
# silence, and a chart with a gap in it says something
# true where a full one would not.
FEWEST_NOTES = 2


# How close a second name has to be before it is worth
# mentioning. Scaled by how much is sounding, so a busy
# beat and a quiet one are judged alike.
ALTERNATIVE_MARGIN = 0.15


def note_name(semitone, key=None):
    """
    Spell a note the way the key does.

    A chart in B flat major that reads A sharp is the same
    sound written in the wrong dialect, and a singer
    reading it has to translate every bar.
    """

    if key in FLAT_KEYS:
        return FLAT_NAMES[semitone]

    return SHARP_NAMES[semitone]


def weigh_pitches(notes, start, end):
    """
    How long each pitch class sounds during a span.

    Returns (weights, lowest) where weights is a list of
    twelve durations and lowest is the pitch class of the
    lowest note sounding, or None.

    Pitch classes below TRACE_FLOOR of the span's sound are
    zeroed, and the bass is the lowest note of a pitch
    class that survives - a trace note names nothing.
    """

    weights = [0.0] * 12

    for note_start, length, midi_number in notes:

        note_end = note_start + length

        overlap = min(end, note_end) - max(start, note_start)

        if overlap <= 0:
            continue

        weights[midi_number % 12] += overlap

    total = sum(weights)

    for semitone in range(12):

        if weights[semitone] < TRACE_FLOOR * total:
            weights[semitone] = 0.0

    lowest_midi = None

    for note_start, length, midi_number in notes:

        note_end = note_start + length

        overlap = min(end, note_end) - max(start, note_start)

        if overlap <= 0:
            continue

        if weights[midi_number % 12] == 0.0:
            continue

        if lowest_midi is None or midi_number < lowest_midi:
            lowest_midi = midi_number

    lowest = None if lowest_midi is None else lowest_midi % 12

    return weights, lowest


def score_chord(weights, lowest, root, quality, seventh_cost=0.0):
    """
    How well a chord explains what is sounding.

    Every note belonging to the chord counts for it, and
    every note outside counts against, so the winner is the
    chord that leaves least unexplained.

    seventh_cost, when given, additionally costs a seventh
    chord SEVENTH_COST's worth of its own total - see that
    constant. Off by default: this only belongs where a
    winner is being chosen among rival readings of the same
    beat, not in the alternatives and second opinions shown
    alongside it, which exist to surface genuine ambiguity
    rather than to repeat the same bias against it.
    """

    intervals = QUALITIES[quality]

    tones = {(root + interval) % 12 for interval in intervals}

    score = 0.0

    for semitone in range(12):

        if semitone in tones:
            score += weights[semitone]

        else:
            score -= OUTSIDE_PENALTY * weights[semitone]

    total = sum(weights)

    if lowest is not None and lowest == root:
        score += BASS_BONUS * total

    # A chord is a worse explanation for every one of its
    # notes that cannot be heard.
    missing = len([
        semitone for semitone in tones
        if weights[semitone] == 0
    ])

    if missing:
        score -= MISSING_PENALTY * total * missing / len(tones)

    if seventh_cost and len(tones) > 3:
        score -= seventh_cost * total

    return score


def name_chord(weights, lowest, key=None):
    """
    The chord that best explains a span, or None.

    A root's own qualities can tie exactly - a beat with
    only a root and a fifth sounding, no third at all,
    scores identically as major or minor, since neither
    reading explains or contradicts anything the other
    doesn't. Untouched, that tie always fell to major:
    DETECTED_QUALITIES lists "" before "m", and a strict
    greater-than only ever replaces the first candidate
    tried, never matches it. That is not a musical
    preference, it is an accident of a list's order, and it
    was a real, systematic bias, not a rare edge case:
    measured against two published charts, it called
    fifteen genuinely minor bars major in one song alone,
    every one of them a beat where the third simply never
    sounds. On a true tie, and only then, the key breaks it
    instead: a minor scale degree is more often actually
    minor than an arbitrary list position is.

    A wide search has a cost of its own: with sixty
    candidates and only a handful of real notes to judge
    them by, a chord built on the wrong root can still
    explain everything sounding, purely because a key's own
    seven notes overlap so much between neighbours. The
    search only opens that wide when the music has actually
    left the key - a real accidental sounding, a pitch class
    outside the key's own seven notes. Until then, only
    chords whose own tones are all diatonic are considered,
    which is a different and looser thing than only the
    seven plain triads: a dominant seventh built entirely
    from the key's own notes stays reachable without any
    accidental, only a chord that actually needs one does
    not. Measured against real songs: no accidental, no
    change to what already worked: an accidental present,
    the true chord found where the seven-triad list alone
    could never have reached it (Viva la Vida's borrowed
    Db was a false alarm from an earlier key-detection bug,
    but I'm Yours' F minor - built on an A flat the key of C
    does not have - is a real one, and is exactly this
    shape).
    """

    total = sum(weights)

    if total <= QUIET_BEAT:
        return None

    sounding = len([weight for weight in weights if weight > 0])

    if sounding < FEWEST_NOTES:
        return None

    key_tonic = (
        note_to_midi(key + "4") % 12 if key is not None else None
    )

    diatonic_quality = {
        (key_tonic + degree) % 12: quality
        for degree, quality in DIATONIC
    } if key_tonic is not None else {}

    diatonic_notes = {
        (key_tonic + degree) % 12 for degree, _ in DIATONIC
    } if key_tonic is not None else None

    has_accidental = (
        diatonic_notes is not None and any(
            weight > 0 and semitone not in diatonic_notes
            for semitone, weight in enumerate(weights)
        )
    )

    best = None
    best_score = None

    for root in range(12):

        root_best = None
        root_best_score = None

        for quality in DETECTED_QUALITIES:

            if (
                diatonic_notes is not None
                and not has_accidental
                and not all(
                    (root + interval) % 12 in diatonic_notes
                    for interval in QUALITIES[quality]
                )
            ):
                continue

            score = score_chord(
                weights, lowest, root, quality,
                seventh_cost=SEVENTH_COST
            )

            if root_best_score is None or score > root_best_score:
                root_best_score = score
                root_best = quality

            elif (
                score == root_best_score
                and diatonic_quality.get(root) == quality
            ):
                root_best = quality

        if root_best_score is None:
            continue

        if best_score is None or root_best_score > best_score:
            best_score = root_best_score
            best = note_name(root, key) + root_best

    # A chord that explains less than it leaves out is not
    # worth naming.
    if best_score is not None and best_score <= 0:
        return None

    return best


def detect_chords(notes, total_beats, beats_per_bar=4, key=None):
    """
    Name the chord on every beat, then join the repeats.

    Returns a list of (start_beats, length_beats, name).
    """

    if total_beats <= 0:
        return []

    named = []

    for beat in range(int(round(total_beats))):

        weights, lowest = weigh_pitches(
            notes,
            beat,
            beat + 1
        )

        named.append(name_chord(weights, lowest, key))

    # Join runs of the same chord into one entry.
    chords = []

    for beat in range(len(named)):

        name = named[beat]

        if name is None:
            continue

        if chords:

            start, length, previous = chords[-1]

            if previous == name and start + length == beat:
                chords[-1] = (start, length + 1.0, name)
                continue

        chords.append((float(beat), 1.0, name))

    return chords


def fill_gaps(chords, total_beats):
    """
    Stretch chords over the beats nothing was named on.

    A beat of silence between phrases belongs to the chord
    before it, so far as a chart is concerned: charts have
    no way to write nothing, and the alternative is a hole
    where a bar should be.
    """

    if not chords:
        return []

    filled = []

    for position in range(len(chords)):

        start, length, name = chords[position]

        if position + 1 < len(chords):
            next_start = chords[position + 1][0]

        else:
            next_start = total_beats

        filled.append((start, next_start - start, name))

    # The first chord reaches back to the beginning.
    first_start, first_length, first_name = filled[0]

    if first_start > 0:
        filled[0] = (0.0, first_start + first_length, first_name)

    return filled


def write_chart(chords, total_beats, beats_per_bar=4):
    """
    Write chords out in the chart notation.

    One token per beat, a dot carrying the chord on, and a
    bar line every few beats as the time signature says.

    A chord starting exactly on a half beat (X.5 - an
    eighth-note syncopation) keeps that precision, written
    as a split token in its beat's slot: "A>B" when both
    halves are new chords, ">B" when only the second half
    is. Anything not exactly on a half floors to the whole
    beat it starts within, precisely as before - detected
    chords are uncertain in their exact timing and were
    never meant to claim half-beat precision; only a source
    that genuinely states the half (a printed score, or a
    hand-typed split token surviving a round trip) should
    produce one.
    """

    if not chords:
        return ""

    on_half = {}

    for start, length, name in chords:

        fraction = start - int(start)

        if abs(fraction - 0.5) < 1e-6:
            slot = int(start) * 2 + 1

        else:
            slot = int(round(start)) * 2

        on_half[slot] = name

    tokens = []

    total_slots = int(round(total_beats * 2))

    for slot in range(0, total_slots, 2):

        first = on_half.get(slot)
        second = on_half.get(slot + 1)

        if first is not None and second is not None:
            tokens.append(f"{first}{SPLIT}{second}")

        elif first is not None:
            tokens.append(first)

        elif second is not None:
            tokens.append(f"{SPLIT}{second}")

        else:
            tokens.append(".")

    # A chart cannot begin with a dot, or with a bare ">B"
    # (which would mean carrying a chord that was never
    # named) - both are the same problem: nothing to open on.
    if tokens and (tokens[0] == "." or tokens[0].startswith(SPLIT)):
        return ""

    bars = []

    for position in range(0, len(tokens), int(beats_per_bar)):

        bar = tokens[position:position + int(beats_per_bar)]

        bars.append(" ".join(bar))

    return "| " + " | ".join(bars) + " |"


def explain_empty_chart(notes, total_beats):
    """
    Why no chords were found, when none were.

    An empty box with no explanation looks like a fault.
    Usually it means the music is a single line, which is
    not a fault at all: there are no chords in a melody,
    only notes one after another.
    """

    thin = 0

    for beat in range(int(round(total_beats))):

        weights, lowest = weigh_pitches(notes, beat, beat + 1)

        if len([w for w in weights if w > 0]) < FEWEST_NOTES:
            thin += 1

    if total_beats and thin > total_beats * 0.5:
        return (
            "No chords were read: this music is mostly a "
            "single line, and a melody on its own does not "
            "say what the harmony is. Write a chart by "
            "hand if you know it."
        )

    return (
        "No chords were read from this music."
    )


def chart_from_notes(notes, total_beats, beats_per_bar=4, key=None):
    """
    Read a chord chart out of a piece of polyphonic music.
    """

    chords = detect_chords(notes, total_beats, beats_per_bar, key)

    chords = fill_gaps(chords, total_beats)

    return write_chart(chords, total_beats, beats_per_bar)


def other_names_for(weights, lowest, chosen, most=2, key=None):
    """
    What else the same notes could be called.

    Some pitch sets genuinely are two chords: D, F sharp,
    A and B is a D sixth and a B minor seventh at once, and
    which one it is depends on the music around it rather
    than on the notes. Naming only the winner hides that
    the question was open.

    Returns the next best names, closest first.
    """

    total = sum(weights)

    if total <= QUIET_BEAT:
        return []

    scored = []

    for root in range(12):

        for quality in DETECTED_QUALITIES:

            name = note_name(root, key) + quality

            if name == chosen:
                continue

            scored.append(
                (score_chord(weights, lowest, root, quality), name)
            )

    scored.sort(reverse=True)

    best = score_chord_for_name(weights, lowest, chosen, key)

    close = [
        name for score, name in scored
        if best - score <= ALTERNATIVE_MARGIN * total
    ]

    return close[:most]


def score_chord_for_name(weights, lowest, name, key=None):
    """
    Score a chord given the way it is written.
    """

    for root in range(12):

        for quality in DETECTED_QUALITIES:

            if note_name(root, key) + quality == name:
                return score_chord(weights, lowest, root, quality)

    return 0.0


def bass_note_for(weights, lowest, name, key=None):
    """
    The bass note, when it is not the root.

    A chord with a note other than its root at the bottom
    is an inversion, written D/F sharp. The chart notation
    has no way to say that, so it is worth mentioning
    rather than losing.
    """

    if lowest is None:
        return None

    for root in range(12):

        for quality in DETECTED_QUALITIES:

            if note_name(root, key) + quality == name:

                if lowest != root:
                    return note_name(lowest, key)

                return None

    return None


def describe_detection(notes, chords):
    """
    What the chart does not say.

    The chart holds one name per chord because it has to
    parse and be played. Everything else the detection
    knew - the inversions, and the places where another
    name fits just as well - is reported alongside it, for
    the player to judge.
    """

    inversions = []
    alternatives = []

    for start, length, name in chords:

        weights, lowest = weigh_pitches(notes, start, start + length)

        bass = bass_note_for(weights, lowest, name)

        if bass:
            inversions.append(f"{name}/{bass}")

        others = other_names_for(weights, lowest, name)

        if others:
            alternatives.append(
                f"{name} ({' or '.join(others)})"
            )

    lines = []

    if inversions:
        lines.append(
            "Some chords are played over another note: "
            + ", ".join(inversions[:6])
            + "."
        )

    if alternatives:
        lines.append(
            "Some could be named differently: "
            + ", ".join(alternatives[:6])
            + "."
        )

    return " ".join(lines)


def as_midi_object(notes, ticks_per_beat=480):
    """
    Build a MIDI object in memory from a list of notes.

    Chord readers that expect a file can read one of these
    just as well: a file is only a way of carrying notes
    about, and we already have the notes.
    """

    from miditoolkit import MidiFile, Instrument, Note

    midi_object = MidiFile()

    midi_object.ticks_per_beat = ticks_per_beat

    instrument = Instrument(program=0)

    for start, length, midi_number in notes:

        instrument.notes.append(
            Note(
                velocity=80,
                pitch=midi_number,
                start=int(start * ticks_per_beat),
                end=int((start + length) * ticks_per_beat)
            )
        )

    midi_object.instruments.append(instrument)

    # Without this the readers find no music: it is how
    # they know where to stop looking.
    midi_object.max_tick = max(
        (note.end for note in instrument.notes),
        default=0
    )

    return midi_object


def midi_reader_opinion(notes, chords):
    """
    What a chord reader working from the notes makes of it.

    This one does its own segmentation, weighing one beat
    against two before deciding, so it disagrees with us in
    a different way than a namer does: not about what the
    notes are called, but about where one chord ends.
    """

    try:
        from chorder import Dechorder

    except ImportError:
        return ""

    theirs = Dechorder.dechord(as_midi_object(notes))

    differences = []

    for start, length, name in chords:

        beat = int(round(start))

        if beat >= len(theirs):
            continue

        other = str(theirs[beat])

        if other == "None":
            continue

        if root_of(other) != root_of(name):
            differences.append(f"{name} (or {other})")

    if not differences:
        return ""

    return (
        "A reader that decides where chords change would "
        "hear some differently: "
        + ", ".join(differences[:4])
        + "."
    )


def root_of(name):
    """
    The note a chord is built on, however it is written.
    """

    name = str(name).split("/")[0]

    for quality in [
        "maj7", "m7", "dim", "aug", "sus4", "sus2",
        "M7", "M", "m", "7", "o", "+", "6"
    ]:
        if name.endswith(quality):
            name = name[:-len(quality)]
            break

    name = name.replace("-", "b")

    return {
        "Bb": "A#", "Eb": "D#", "Ab": "G#",
        "Db": "C#", "Gb": "F#"
    }.get(name, name)


def second_opinion(notes, chords):
    """
    What another chord namer makes of the same notes.

    Our detector fills the chart; this only comments. It is
    worth hearing because it disagrees usefully: pychord
    names a set of notes strictly and says nothing when a
    passing tone spoils the set, so its silence marks the
    beats where something is sounding that the chord does
    not explain.

    Not needed for the app to work, and this returns
    nothing when it is absent.
    """

    try:
        from pychord.analyzer import find_chords_from_notes

    except ImportError:
        return ""

    differences = []

    for start, length, name in chords:

        weights, lowest = weigh_pitches(notes, start, start + length)

        sounding = [
            SHARP_NAMES[semitone]
            for semitone in range(12)
            if weights[semitone] > 0.2
        ]

        theirs = [
            str(chord)
            for chord in find_chords_from_notes(sounding)
        ]

        if not theirs:
            continue

        if not any(
            chord.split("/")[0] == name for chord in theirs
        ):
            differences.append(
                f"{name} (read elsewhere as {theirs[0]})"
            )

    if not differences:
        return (
            "A second chord reader agrees with all of "
            "these."
        )

    return (
        "A second chord reader would name some of these "
        "differently: "
        + ", ".join(differences[:6])
        + "."
    )


def asides_for(notes, chords, key=None):
    """
    A short note to print under each chord symbol.

    Keyed by the beat the chord starts on, so the picture
    can place them without knowing how they were worked
    out.
    """

    asides = {}

    for start, length, name in chords:

        weights, lowest = weigh_pitches(notes, start, start + length)

        parts = []

        bass = bass_note_for(weights, lowest, name, key)

        if bass:
            parts.append("/" + bass)

        others = other_names_for(
            weights, lowest, name, most=1, key=key
        )

        if others:
            parts.append("or " + others[0])

        if parts:
            asides[round(float(start), 3)] = "  ".join(parts)

    return asides


# The chords a key offers, as scale degrees and quality.
# Diatonic harmony in one line: triads built on each note
# of the major scale, which is where nearly all the chords
# in nearly all songs come from.
DIATONIC = [
    (0, ""),
    (2, "m"),
    (4, "m"),
    (5, ""),
    (7, ""),
    (9, "m"),
    (11, "dim")
]


# What a note on the downbeat is worth against one passing
# by. A melody note's weight is its length, and where it
# falls matters as much as how long it lasts: the ear takes
# the note on the beat as the harmony and hears the rest as
# decoration.
DOWNBEAT_WEIGHT = 2.0
ON_BEAT_WEIGHT = 1.3


# The chords a song reaches for first. Tonic, subdominant
# and dominant carry most of western harmony between them,
# and when a melody fits several chords equally - which it
# often does, since a single note belongs to three of the
# seven - these are the likelier answer. Without this the
# choice falls to whichever was tried first, which is not
# a musical reason.
PRIMARY_BONUS = 0.25

# Which degrees those are depends on where home is. A minor
# key uses the same seven chords as its relative major and
# hears a different one as the tonic: D minor and F major
# share every note, but the first leans on Dm, Gm and Am
# where the second leans on F, Bb and C. Taking the major
# as home in a minor song puts every cadence in the wrong
# place.
PRIMARY_DEGREES = (0, 5, 7)
MINOR_PRIMARY_DEGREES = (9, 2, 4)

TONIC_DEGREE = 0
MINOR_TONIC_DEGREE = 9


# The tonic pulls harder at the ends of a phrase: music
# starts at home and returns there, and the last chord of
# a tune is the tonic far more often than not.
CADENCE_BONUS = 0.4


# How much better a split bar has to be before it is worth
# two chords instead of one. Harmony usually changes at the
# bar, and a chart that changes every other beat is harder
# to read and rarely more true.
SPLIT_MARGIN = 1.25


def chords_of_key(key):
    """
    The chords a major key offers, tonic first.
    """

    from notes import note_to_midi

    tonic = note_to_midi(key + "4") % 12

    return [
        (
            (tonic + degree) % 12,
            quality
        )
        for degree, quality in DIATONIC
    ]


def weigh_melody(pitches, durations, start, end, beats_per_bar=4):
    """
    How much each pitch class matters over a stretch of
    melody.

    Length and position together: a note on the downbeat
    counts for more than one slipping past on an offbeat,
    because that is how the ear decides which notes are the
    harmony and which are decoration.
    """

    from notes import note_to_midi, is_rest

    weights = [0.0] * 12

    beat = 0.0

    for position in range(len(pitches)):

        length = durations[position]

        if beat >= end:
            break

        overlap = min(end, beat + length) - max(start, beat)

        if overlap > 0 and not is_rest(pitches[position]):

            where = beat % beats_per_bar

            if where == 0:
                strength = DOWNBEAT_WEIGHT

            elif where == int(where):
                strength = ON_BEAT_WEIGHT

            else:
                strength = 1.0

            weights[note_to_midi(pitches[position]) % 12] += (
                overlap * strength
            )

        beat += length

    return weights


def fit_chord(weights, candidates, key=None, place=None,
              minor=False):
    """
    The chord of the key that best fits what the melody
    does over a stretch.

    place is "first", "last" or None, which shifts the
    balance toward the tonic at the ends of a phrase.

    Returns (name, score).
    """

    best = None
    best_score = None

    total = sum(weights)

    if total <= QUIET_BEAT:
        return None, 0.0

    for position in range(len(candidates)):

        root, quality = candidates[position]

        tones = {
            (root + interval) % 12
            for interval in QUALITIES[quality]
        }

        score = 0.0

        for semitone in range(12):

            if semitone in tones:
                score += weights[semitone]

            else:
                score -= OUTSIDE_PENALTY * weights[semitone]

        degree = DIATONIC[position][0]

        primaries = (
            MINOR_PRIMARY_DEGREES if minor else PRIMARY_DEGREES
        )

        tonic = MINOR_TONIC_DEGREE if minor else TONIC_DEGREE

        # The chord a step below the tonic in a minor key
        # is the one that leads home, as the dominant does
        # in a major one.
        leading = 4 if minor else 7

        if degree in primaries:
            score += PRIMARY_BONUS * total

        if place in ("first", "last") and degree == tonic:
            score += CADENCE_BONUS * total

        if place == "before last" and degree == leading:
            score += CADENCE_BONUS * total

        if best_score is None or score > best_score:
            best_score = score
            best = note_name(root, key) + quality

    return best, best_score


def suggest_chart_from_melody(
    pitches,
    durations,
    key,
    beats_per_bar=4,
    minor=False
):
    """
    Suggest chords that would fit a melody.

    This is a different question from reading the chords
    off a piece of polyphonic music, and a weaker one. A
    melody does not state its harmony; it implies one, and
    more than one answer is usually defensible. What makes
    the guess reasonable rather than arbitrary is that the
    melody constrains it heavily once the key is known:

    - the chords are the seven the key offers, not any of
      the sixty a detector must weigh
    - a note on the downbeat counts for more than one
      slipping past, because that is how the ear decides
      which notes are harmony and which are decoration
    - tonic, subdominant and dominant are likelier than
      the rest, which is what settles the frequent ties
    - phrases begin and end at home

    One chord to the bar, split in two only where a single
    chord leaves the bar badly explained. Real harmony
    changes at the bar far more often than not, and a chart
    that changes every other beat is harder to read and
    rarely more true.
    """

    total = sum(durations)

    bars = int(round(total / beats_per_bar))

    if bars < 1:
        return ""

    candidates = chords_of_key(key)

    tokens = []

    for bar in range(bars):

        start = bar * beats_per_bar

        if bar == 0:
            place = "first"

        elif bar == bars - 1:
            place = "last"

        elif bar == bars - 2:
            place = "before last"

        else:
            place = None

        whole = weigh_melody(
            pitches, durations, start,
            start + beats_per_bar, beats_per_bar
        )

        one_chord, one_score = fit_chord(
            whole, candidates, key, place, minor
        )

        half = beats_per_bar / 2

        first_half = weigh_melody(
            pitches, durations, start, start + half, beats_per_bar
        )

        second_half = weigh_melody(
            pitches, durations, start + half,
            start + beats_per_bar, beats_per_bar
        )

        first_name, first_score = fit_chord(
            first_half, candidates, key, None, minor
        )

        second_name, second_score = fit_chord(
            second_half, candidates, key, place, minor
        )

        split_better = (
            first_name
            and second_name
            and first_name != second_name
            and first_score + second_score
            > one_score * SPLIT_MARGIN
        )

        bar_tokens = []

        if split_better:
            bar_tokens.append(first_name)
            bar_tokens += ["."] * (int(half) - 1)
            bar_tokens.append(second_name)
            bar_tokens += ["."] * (int(beats_per_bar - half) - 1)

        elif one_chord:
            bar_tokens.append(one_chord)
            bar_tokens += ["."] * (int(beats_per_bar) - 1)

        else:
            # Nothing sounding: hold whatever came before.
            bar_tokens = ["."] * int(beats_per_bar)

        tokens += bar_tokens

    if not tokens or tokens[0] == ".":
        return ""

    lines = []

    for position in range(0, len(tokens), int(beats_per_bar)):

        lines.append(
            " ".join(tokens[position:position + int(beats_per_bar)])
        )

    return "| " + " | ".join(lines) + " |"