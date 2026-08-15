# harmony.py

from notes import (
    NOTE_SEMITONES,
    note_to_midi,
    midi_to_note,
    is_rest
)


# Every major key, each spelled the way its key signature
# spells it: sharp keys in sharps, flat keys in flats. F
# sharp major genuinely contains an E sharp, which is the
# same sound as F but not the same note name.
MAJOR_SCALES = {
    "C": ["C", "D", "E", "F", "G", "A", "B"],
    "G": ["G", "A", "B", "C", "D", "E", "F#"],
    "D": ["D", "E", "F#", "G", "A", "B", "C#"],
    "A": ["A", "B", "C#", "D", "E", "F#", "G#"],
    "E": ["E", "F#", "G#", "A", "B", "C#", "D#"],
    "B": ["B", "C#", "D#", "E", "F#", "G#", "A#"],
    "F#": ["F#", "G#", "A#", "B", "C#", "D#", "E#"],
    "Db": ["Db", "Eb", "F", "Gb", "Ab", "Bb", "C"],
    "Ab": ["Ab", "Bb", "C", "Db", "Eb", "F", "G"],
    "Eb": ["Eb", "F", "G", "Ab", "Bb", "C", "D"],
    "Bb": ["Bb", "C", "D", "Eb", "F", "G", "A"],
    "F": ["F", "G", "A", "Bb", "C", "D", "E"]
}


# The minor key that shares each major key's notes. A
# piece in D minor uses the notes of F major, which is why
# the app can harmonise minor music without knowing
# anything about minor keys: the scale is the same seven
# notes started in a different place.
RELATIVE_MINORS = {
    "C": "A",
    "G": "E",
    "D": "B",
    "A": "F#",
    "E": "C#",
    "B": "G#",
    "F#": "D#",
    "Db": "Bb",
    "Ab": "F",
    "Eb": "C",
    "Bb": "G",
    "F": "D"
}


def key_choices():
    """
    How the keys are offered, as (label, value) pairs.

    Each key is named both ways, since a key signature
    belongs to a major key and its relative minor equally,
    and a singer working from a minor piece should not
    have to know which major to ask for.
    """

    return [
        (f"{major} major / {RELATIVE_MINORS[major]} minor", major)
        for major in MAJOR_SCALES
    ]


class KeyError_(ValueError):
    """
    Something about the key box stops it being read.

    Named with a trailing underscore because `KeyError` is
    already a Python builtin with a different meaning
    entirely - a dict lookup failure, not a music one - and
    shadowing it would be its own source of confusion.
    """


def read_key(key_text):
    """
    Read the key box into a timeline.

    Returns a list of (beat, key_name) pairs, sorted by
    beat. A piece that never changes key - every piece
    before this format existed, and most pieces after -
    parses to a single entry at beat 0, so a caller asking
    "what key is in force at beat B" gets the same one
    answer for every B, the same as reading `Piece.key`
    directly always has.

    The opening key is a bare name, with no "from" clause -
    "G" or "G, Ab from beat 156" are both legal, and the
    first is exactly today's format, unchanged. A later key
    is written "KEY from beat N", N strictly increasing:
    beats, not bars, because a Piece has no bars of its own
    outside a chart, and a key change is a fact about the
    piece whether or not one exists yet.
    """

    text = key_text.strip()

    if len(text) == 0:
        raise KeyError_("Choose a key first, such as C or G.")

    changes = []

    for position, entry in enumerate(text.split(",")):

        entry = entry.strip()

        if position == 0:

            if " from beat " in entry:
                raise KeyError_(
                    "The opening key has no 'from beat' - "
                    "only a key that arrives partway through "
                    "does, as in 'G, Ab from beat 156'."
                )

            name = entry
            beat = 0.0

        else:

            if " from beat " not in entry:
                raise KeyError_(
                    f"'{entry}' needs its own 'from beat N', "
                    "as in 'Ab from beat 156'."
                )

            name, _, beat_text = entry.partition(" from beat ")

            name = name.strip()

            try:
                beat = float(beat_text.strip())

            except ValueError:
                raise KeyError_(
                    f"'{beat_text.strip()}' is not a beat "
                    "number this app understands."
                )

        if name not in MAJOR_SCALES:
            raise KeyError_(
                f"'{name}' is not a key this app knows."
            )

        if changes and beat <= changes[-1][0]:
            raise KeyError_(
                "Each key change has to arrive later than "
                "the one before it."
            )

        changes.append((beat, name))

    return changes


def format_key(changes):
    """
    The reverse of read_key: a timeline back into the box's
    own text.

    A single-entry timeline - the ordinary case - writes as
    a bare key name, identical to what has always been
    typed into this box. Only a genuine change grows the
    ", KEY from beat N" tail.
    """

    if not changes:
        return ""

    opening = changes[0][1]

    tail = "".join(
        f", {name} from beat {beat:g}"
        for beat, name in changes[1:]
    )

    return opening + tail


def key_at(changes, beat):
    """
    Which key is in force at a given beat, from a timeline.

    The one canonical walk - Piece.key_at, transpose_chart
    and transpose_music all call this rather than each
    keeping their own copy, found worth doing once the same
    ten lines had been written a third time. A single-entry
    timeline (the ordinary case) returns that one key for
    every beat, since there is nothing else it could return.
    """

    result = changes[0][1]

    for change_beat, change_key in changes:

        if change_beat > beat:
            break

        result = change_key

    return result


def build_scale_notes(key, lowest=24, highest=108):
    """
    Build all notes belonging to a major key across
    a useful range of octaves.
    """

    scale = MAJOR_SCALES[key]

    # Match each scale pitch name to its semitone.
    scale_by_semitone = {}

    for pitch in scale:
        semitone = NOTE_SEMITONES[pitch]
        scale_by_semitone[semitone] = pitch

    notes = []

    for midi_number in range(lowest, highest + 1):

        semitone = midi_number % 12

        if semitone in scale_by_semitone:

            pitch = scale_by_semitone[semitone]
            octave = (midi_number // 12) - 1

            notes.append(
                (midi_number, pitch + str(octave))
            )

    return notes


def keys_containing(pitches):
    """
    Which of the supported keys contain every one of
    these notes.

    Used to suggest a workable key when the chosen one
    does not fit the music.
    """

    workable = []

    for key in MAJOR_SCALES:

        scale_semitones = set()

        for pitch in MAJOR_SCALES[key]:
            scale_semitones.add(NOTE_SEMITONES[pitch])

        fits = True

        for pitch in pitches:
            if is_rest(pitch):
                continue
            if note_to_midi(pitch) % 12 not in scale_semitones:
                fits = False
                break

        if fits:
            workable.append(key)

    return workable


def nearest_position(scale_notes, note_midi):
    """
    Where a note sits in a scale, or where it sits closest.

    Music borrows notes from outside its key all the time:
    a passing sharp, a blue seventh. Rather than refuse to
    harmonise the whole piece over one of them, such a note
    is treated as the nearest scale note. The harmony keeps
    moving in parallel and one interval comes out slightly
    unusual, which is what a singer improvising a line
    would do anyway.
    """

    best = None
    best_distance = None

    for position in range(len(scale_notes)):

        midi_number, note_name = scale_notes[position]

        distance = abs(midi_number - note_midi)

        if best_distance is None or distance < best_distance:
            best = position
            best_distance = distance

    return best


def notes_outside(pitches, durations=None, key="C"):
    """
    The notes of this music that the key does not contain.

    They can still be harmonised, at the nearest note in
    the scale, but they are worth naming so nobody is
    surprised by the interval that results.

    `key` is either a single key name or a full timeline -
    a list of (beat, name) pairs, Piece.key_changes' own
    shape - for a piece that genuinely modulates: each note
    is checked against whichever key was actually in force
    at its own beat, not one key for the whole piece.
    `durations` is needed to know where each note sits;
    left as None, every note is assumed one beat long, which
    the lookup never notices unless the key genuinely
    changes underneath it.
    """

    if durations is None:
        durations = [1.0] * len(pitches)

    key_changes = [(0.0, key)] if isinstance(key, str) else key

    scale_semitones_by_key = {
        name: {
            NOTE_SEMITONES[note] for note in MAJOR_SCALES[name]
        }
        for _, name in key_changes
    }

    outside = []

    beat = 0.0

    for pitch, length in zip(pitches, durations):

        if is_rest(pitch):
            beat += float(length)
            continue

        scale_semitones = scale_semitones_by_key[
            key_at(key_changes, beat)
        ]

        if note_to_midi(pitch) % 12 not in scale_semitones:
            if pitch not in outside:
                outside.append(pitch)

        beat += float(length)

    return outside


def move_in_scale(note, key="C", steps=-2):
    """
    Move a note through a major scale.

    steps=-2 means move down two scale positions,
    producing a third below.
    """

    scale_notes = build_scale_notes(key)

    note_midi = note_to_midi(note)

    current_position = nearest_position(
        scale_notes,
        note_midi
    )

    if current_position is None:
        raise ValueError(
            "That key has no notes to harmonise with."
        )

    new_position = current_position + steps

    if new_position < 0 or new_position >= len(scale_notes):
        raise ValueError(
            "Harmony note is outside the supported range."
        )

    new_midi, new_note = scale_notes[new_position]

    return new_note


def make_harmony(pitches, durations=None, key="C", steps=-2):
    """
    Create a harmony line for a sequence of pitches.

    Default: a third below in the selected major key. `key`
    is either a single key name (the ordinary case) or a
    full timeline - a list of (beat, name) pairs, Piece.
    key_changes' own shape - for a piece that genuinely
    modulates: each note harmonises against whichever key
    was actually in force at its own beat, not one key for
    the whole line. `durations` is needed to know where
    each note sits; left as None (every caller before this
    format existed, and most after), every note is assumed
    one beat long, which the lookup never notices unless the
    key genuinely changes underneath it.
    """

    if durations is None:
        durations = [1.0] * len(pitches)

    key_changes = [(0.0, key)] if isinstance(key, str) else key

    harmony = []

    beat = 0.0

    for pitch, length in zip(pitches, durations):

        # A silence in the melody is a silence in the
        # harmony: both parts breathe together.
        if is_rest(pitch):
            harmony.append(pitch)
            beat += float(length)
            continue

        harmony_note = move_in_scale(
            pitch,
            key_at(key_changes, beat),
            steps
        )

        harmony.append(harmony_note)

        beat += float(length)

    return harmony


def is_chord_tone(midi_number, chord_tones):
    """
    Whether a note belongs to the chord underneath it.
    """

    return midi_number % 12 in chord_tones


def nearest_chord_tone_below(midi_number, chord_tones):
    """
    The closest chord tone strictly below a note.

    Where a harmony voice sings when it draws from the
    chord rather than from parallel motion.
    """

    candidate = midi_number - 1

    while candidate > midi_number - 13:

        if candidate % 12 in chord_tones:
            return candidate

        candidate -= 1

    return midi_number - 12


def chord_tones_at(chords, beat):
    """
    The pitch classes of the chord sounding at a moment,
    or None when nothing is.
    """

    for start, length, tones in chords:

        if start <= beat < start + length:
            return tones

    return None


def make_chord_harmony(
    pitches,
    durations,
    chords,
    key="C",
    steps=-2,
    style="Thirds, chord-corrected"
):
    """
    A harmony line that knows the chords.

    Two ways of choosing each note, neither more correct
    than the other - they are different sounds:

    Thirds, chord-corrected: parallel thirds as usual,
    except where the third lands outside the chord, when
    the nearest chord tone below the melody is taken
    instead. First principles: in diatonic music the third
    below a melody note usually is a chord tone, because
    triads are stacked thirds. The departures are exactly
    the moments a duet singer would bend their line to
    avoid a clash, so this is the duet sound with the sour
    moments repaired.

    Chord tones: every note drawn from the chord, nearest
    below the melody. The line follows the harmony rather
    than shadowing the tune, which is the sound of an
    arranged inner voice.

    A third way, holding a note while it still fits the
    chord, was tried and taken out again: on a short
    phrase over changing chords it is forced to move
    almost at once, and what it produces is barely
    distinguishable from chord tones. Holding common tones
    is only the first rule of voice leading, and a line
    with no shape of its own is not really an independent
    voice. Worth returning to with the rest of the rules,
    and with music long enough for it to matter.

    Notes with no chord under them fall back to the
    parallel third, and a melody note that is itself
    outside the chord keeps its parallel third too, since
    correcting an intentional dissonance would flatten
    what the composer wrote.

    `key` is either a single key name or a full timeline -
    a list of (beat, name) pairs, Piece.key_changes' own
    shape - for a piece that genuinely modulates: the
    parallel-third fallback (used whether or not a chord is
    present) is worked out against whichever key was
    actually in force at each note's own beat.
    """

    key_changes = [(0.0, key)] if isinstance(key, str) else key

    harmony = []

    beat = 0.0

    previous = None

    for position in range(len(pitches)):

        pitch = pitches[position]

        length = durations[position]

        if is_rest(pitch):
            harmony.append(pitch)
            beat += length
            continue

        melody_midi = note_to_midi(pitch)

        tones = chord_tones_at(chords, beat)

        parallel = note_to_midi(
            move_in_scale(pitch, key_at(key_changes, beat), steps)
        )

        if tones is None:
            chosen = parallel

        elif style == "Chord tones":
            chosen = nearest_chord_tone_below(
                melody_midi, tones
            )

        else:

            # Thirds, corrected at the clashes. A melody
            # note outside its own chord is left with its
            # parallel third: the dissonance is the
            # composer's, not ours to repair.
            melody_in_chord = is_chord_tone(
                melody_midi, tones
            )

            if melody_in_chord and not is_chord_tone(
                parallel, tones
            ):
                chosen = nearest_chord_tone_below(
                    melody_midi, tones
                )

            else:
                chosen = parallel

        harmony.append(midi_to_note(chosen))

        previous = chosen

        beat += length

    return harmony


# Where a bass line sings: G2 to A3.
#
# Low enough to be heard as the bottom of the harmony
# rather than as a second tune, but a working range rather
# than the extremes. A bass can reach E2, and singing
# there is another matter; a line that drops to F2 because
# the arithmetic allowed it asks for a note most people
# cannot support, and one the detector can barely hear.
BASS_LOWEST_MIDI = 43
BASS_HIGHEST_MIDI = 57

# Where the line starts before it has anywhere to move
# from. Middle of the range, so it has room either way.
BASS_HOME_MIDI = 48


def bass_octave_for(root, previous=None):
    """
    Which octave of a root note the bass should sing.

    Whichever is nearest the note before it. A bass line
    moves by the smallest interval it can: from C, an F a
    fourth above is a shorter journey than an F a fifth
    below, and it keeps the line off the floor of the
    range. Anchoring each root independently from the
    bottom of the range instead produces leaps nobody
    would write and notes lower than most voices reach.
    """

    target = BASS_HOME_MIDI if previous is None else previous

    candidates = []

    midi_number = BASS_LOWEST_MIDI + (
        (root - BASS_LOWEST_MIDI) % 12
    )

    while midi_number <= BASS_HIGHEST_MIDI:
        candidates.append(midi_number)
        midi_number += 12

    if not candidates:
        return BASS_LOWEST_MIDI + (
            (root - BASS_LOWEST_MIDI) % 12
        )

    return min(
        candidates,
        key=lambda value: abs(value - target)
    )


def make_bass(pitches, durations, chords):
    """
    A bass line: the root of each chord, held.

    A bass part does not follow the melody at all. Where a
    harmony voice sings a note for every note of the tune,
    a bass sings one note per chord and holds it while the
    melody moves above. That is what a bass line is for:
    it says where the harmony is, which is what lets
    everyone else hear whether they are in the right place.

    Returned as one entry per melody note, since that is
    what the rest of the app reads, but consecutive notes
    over one chord are the same note repeated rather than
    a line of their own.

    Each root is sung in whichever octave sits closest to
    the note before it, so the line walks rather than
    leaping about the range.
    """

    line = []

    beat = 0.0

    previous = None

    for position in range(len(pitches)):

        pitch = pitches[position]

        length = durations[position]

        if is_rest(pitch):
            line.append(pitch)
            beat += length
            continue

        tones = chord_tones_at(chords, beat)

        if tones is None:

            # Nothing to sing the root of, so the bass
            # rests rather than inventing a harmony.
            line.append("R")

        else:

            midi_number = bass_octave_for(
                tones[0],
                previous
            )

            line.append(midi_to_note(midi_number))

            previous = midi_number

        beat += length

    return line