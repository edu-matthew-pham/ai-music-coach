# midi_import.py

"""
Read a MIDI file into the app's three textboxes.

A MIDI file is already the app's data model: pitches with
start times and lengths, plus a tempo. This module reads a
melody line out of one and turns it into the pitch,
duration and lyric text the rest of the app runs on.

What it deliberately does not attempt: polyphony. When two
notes sound at once, the highest is kept, on the grounds
that the melody usually sits on top. Files exported from
notation software, one voice per track, import cleanly.
Dense piano arrangements will come out as their top line.
"""

from fractions import Fraction

import mido

from notes import midi_to_note, REST


class MidiImportError(ValueError):
    """
    Something about the file stops it importing.

    The message is written to be shown to the person who
    chose the file.
    """


# A gap shorter than this is the ordinary space between
# notes rather than a rest anyone would write down.
SHORTEST_REST = 0.2


# Where a piece is divided into phrases to practise.
#
# A singer's phrase ends where they breathe, so a rest is
# the honest place to break. Music with no rests still has
# to be divided somehow, hence the cap: a stretch longer
# than this breaks at a bar line instead. Very short
# phrases are folded into the next, since two notes are
# not worth practising alone.
PHRASE_REST = 0.7
LONGEST_PHRASE_BEATS = 32
SHORTEST_PHRASE_NOTES = 4


# The note lengths the app works in, as fractions of a
# beat, taking a beat as a quarter note. Real files land
# between the cracks, so an imported length snaps to the
# nearest of these.
#
# The list covers plain notes, dotted notes at every level
# including double dots, and triplets. Music written in
# compound time leans on dotted values, and leaving them
# out does not merely round one note: the error repeats
# and the phrase drifts out of time.
BEAT_FRACTIONS = [
    # Triplets.
    1 / 3, 2 / 3, 4 / 3, 8 / 3,

    # Sixteenths and their dots.
    0.25, 0.375, 0.4375,

    # Eighths.
    0.5, 0.75, 0.875,

    # Quarters.
    1.0, 1.5, 1.75,

    # Halves.
    2.0, 2.75, 3.0, 3.5,

    # Whole notes and longer.
    4.0, 6.0, 7.0, 8.0
]


def snap_to_beat(beats):
    """
    Round a duration to the nearest musical note length.
    """

    best = BEAT_FRACTIONS[0]

    for fraction in BEAT_FRACTIONS:
        if abs(beats - fraction) < abs(beats - best):
            best = fraction

    return best


def read_notes(midi_file, track_number=None):
    """
    Collect every note in the file with its absolute start
    time and length, in beats.

    track_number picks a single track. Left as None, every
    track is read together, which suits a file holding one
    line of music and not much else.

    Returns a list of (start_beats, length_beats, midi_number)
    and the first tempo found, as beats per minute.
    """

    ticks_per_beat = midi_file.ticks_per_beat

    bpm = None

    notes = []

    for position, track in enumerate(midi_file.tracks):

        # The tempo usually lives on the first track, so it
        # is read from every track even when only one is
        # being imported.
        wanted = (
            track_number is None
            or position == track_number
        )

        time_ticks = 0
        sounding = {}

        for message in track:

            time_ticks += message.time

            if message.type == "set_tempo" and bpm is None:
                bpm = round(mido.tempo2bpm(message.tempo))

            elif not wanted:
                continue

            elif message.type == "note_on" and message.velocity > 0:
                sounding[message.note] = time_ticks

            elif message.type in ("note_off", "note_on"):

                # A note_on with zero velocity is the other
                # accepted way of ending a note.
                started = sounding.pop(message.note, None)

                if started is None:
                    continue

                start_beats = started / ticks_per_beat
                length_beats = (
                    time_ticks - started
                ) / ticks_per_beat

                if length_beats > 0:
                    notes.append(
                        (start_beats, length_beats, message.note)
                    )

    if bpm is None:
        bpm = 120

    return notes, bpm


def keep_melody(notes):
    """
    Reduce overlapping notes to a single line.

    Notes are grouped by start time, and where several
    start together, the highest wins. A note swallowed
    entirely by a longer, higher one is dropped.
    """

    notes = sorted(notes)

    melody = []

    for start, length, midi_number in notes:

        if melody:

            last_start, last_length, last_midi = melody[-1]

            same_start = abs(start - last_start) < 0.05

            if same_start:

                if midi_number > last_midi:
                    melody[-1] = (start, length, midi_number)

                continue

            # Trim the previous note if this one interrupts.
            if start < last_start + last_length:
                melody[-1] = (
                    last_start,
                    start - last_start,
                    last_midi
                )

        melody.append((start, length, midi_number))

    return melody


def describe_tracks(path):
    """
    Summarise what each track in a file contains.

    A choral or band file holds one track per part, and
    which is the melody cannot be guessed reliably: the
    highest average pitch is often a descant or a piano
    reduction rather than the tune. So the tracks are
    described and the choice is left to the player.

    Returns a list of (track_number, description).
    """

    try:
        midi_file = mido.MidiFile(path)

    except Exception:
        raise MidiImportError(
            "That file could not be read as MIDI."
        )

    described = []

    for position, track in enumerate(midi_file.tracks):

        numbers = [
            message.note
            for message in track
            if message.type == "note_on"
            and message.velocity > 0
        ]

        if len(numbers) == 0:
            continue

        one = mido.MidiFile(
            ticks_per_beat=midi_file.ticks_per_beat
        )
        one.tracks.append(track)

        notes, bpm = read_notes(one)
        melody = keep_melody(notes)

        opening = " ".join(
            midi_to_note(number)
            for _, _, number in melody[:6]
        )

        name = track.name.strip() if track.name else ""

        label = f"Track {position}"

        if name:
            label += f" - {name}"

        label += (
            f" ({len(numbers)} notes, "
            f"{midi_to_note(min(numbers))} to "
            f"{midi_to_note(max(numbers))}): {opening}"
        )

        described.append((position, label))

    if len(described) == 0:
        raise MidiImportError(
            "No notes were found in that file."
        )

    return described


def split_into_phrases(
    melody,
    beats_per_bar=4
):
    """
    Divide a line of music into phrases worth practising.

    Breaks fall where the music rests. A stretch that runs
    on without resting is broken at a bar line so that no
    phrase is unusably long, and a phrase too short to be
    worth singing is joined to the one after it.

    Returns a list of lists of notes.
    """

    if len(melody) == 0:
        return []

    phrases = []
    current = [melody[0]]

    phrase_start = melody[0][0]
    previous_end = melody[0][0] + melody[0][1]

    for start, length, midi_number in melody[1:]:

        gap = start - previous_end
        so_far = start - phrase_start

        breaks_here = gap >= PHRASE_REST

        # Nothing has rested for a long time, so break at
        # the next bar line rather than run on forever.
        if not breaks_here and so_far >= LONGEST_PHRASE_BEATS:
            breaks_here = (
                abs(start % beats_per_bar) < 0.01
            )

        if breaks_here:
            phrases.append(current)
            current = []
            phrase_start = start

        current.append((start, length, midi_number))
        previous_end = start + length

    if current:
        phrases.append(current)

    # Fold anything too short into the phrase after it.
    joined = []

    for phrase in phrases:

        if joined and len(joined[-1]) < SHORTEST_PHRASE_NOTES:
            joined[-1] = joined[-1] + phrase

        else:
            joined.append(phrase)

    return joined


def notes_to_text(melody):
    """
    Turn a list of notes into pitch and duration text.

    Silence between notes becomes a rest, so the timing
    survives. Silence before the first note is dropped:
    music begins where it begins.
    """

    pitches = []
    durations = []

    previous_end = melody[0][0]

    for start, length, midi_number in melody:

        gap = start - previous_end

        if gap >= SHORTEST_REST:
            pitches.append(REST)
            durations.append(snap_to_beat(gap))

        pitches.append(midi_to_note(midi_number))
        durations.append(snap_to_beat(length))

        previous_end = start + length

    def show(value):
        """
        Write a length as a fraction of a beat.

        Fractions are how note lengths actually work, and
        writing them that way makes the structure plain:
        every dotted note is three over something, because
        a dot adds half again, and every double dotted note
        is seven over something. Triplets, which have no
        exact decimal at all, then need no special case.

            1/4  sixteenth        3/8  dotted sixteenth
            1/2  eighth           3/4  dotted eighth
            1    quarter          3/2  dotted quarter
            2    half             3    dotted half
            1/3  triplet
        """

        fraction = Fraction(value).limit_denominator(16)

        if fraction.denominator == 1:
            return str(fraction.numerator)

        return f"{fraction.numerator}/{fraction.denominator}"

    return (
        " ".join(pitches),
        " ".join(show(value) for value in durations)
    )


def read_time_signature(midi_file):
    """
    How many beats are in a bar, taking a beat as a quarter
    note. Files without a time signature are treated as
    four four, which is the common case.
    """

    for track in midi_file.tracks:
        for message in track:
            if message.type == "time_signature":
                return (
                    message.numerator * 4 / message.denominator
                )

    return 4


def import_midi(path, maximum_notes=None, track_number=None,
                phrase_number=None):
    """
    Turn a MIDI file into pitch, duration and lyric text.

    Returns (pitch_text, duration_text, lyric_text, bpm).
    Lyrics come back when the file carries them aligned to
    notes, as karaoke files do, and empty otherwise.
    """

    try:
        midi_file = mido.MidiFile(path)

    except Exception:
        raise MidiImportError(
            "That file could not be read as MIDI."
        )

    notes, bpm = read_notes(midi_file, track_number)

    if len(notes) == 0:
        raise MidiImportError(
            "No notes were found in that file."
        )

    melody = keep_melody(notes)

    if phrase_number is not None:

        phrases = split_into_phrases(
            melody,
            read_time_signature(midi_file)
        )

        if phrase_number < 0 or phrase_number >= len(phrases):
            raise MidiImportError(
                "That phrase is not in this music."
            )

        melody = phrases[phrase_number]

    if maximum_notes is not None:
        melody = melody[:maximum_notes]

    pitch_text, duration_text = notes_to_text(melody)

    lyric_text = read_lyric_text(midi_file, len(melody))

    return pitch_text, duration_text, lyric_text, bpm


def describe_phrases(path, track_number=None):
    """
    Summarise the phrases a track divides into.

    Returns a list of (phrase_number, description).
    """

    try:
        midi_file = mido.MidiFile(path)

    except Exception:
        raise MidiImportError(
            "That file could not be read as MIDI."
        )

    notes, bpm = read_notes(midi_file, track_number)

    if len(notes) == 0:
        raise MidiImportError(
            "No notes were found in that track."
        )

    melody = keep_melody(notes)

    beats_per_bar = read_time_signature(midi_file)

    phrases = split_into_phrases(melody, beats_per_bar)

    described = []

    for position, phrase in enumerate(phrases):

        first_bar = int(phrase[0][0] / beats_per_bar) + 1

        last = phrase[-1]
        last_bar = int(
            (last[0] + last[1] - 0.01) / beats_per_bar
        ) + 1

        opening = " ".join(
            midi_to_note(number)
            for _, _, number in phrase[:5]
        )

        described.append((
            position,
            f"Phrase {position + 1} "
            f"(bars {first_bar} to {last_bar}, "
            f"{len(phrase)} notes): {opening}"
        ))

    return described


def read_lyric_text(midi_file, note_count):
    """
    Collect karaoke-style lyrics when the file has them.

    MIDI lyrics arrive one syllable per event. Only a file
    whose syllable count matches its melody imports them;
    anything else returns empty rather than guessing at
    the alignment.
    """

    syllables = []

    for track in midi_file.tracks:
        for message in track:
            if message.type == "lyrics":
                text = message.text.strip()
                if text:
                    syllables.append(text)

    if len(syllables) != note_count:
        return ""

    return " ".join(syllables)