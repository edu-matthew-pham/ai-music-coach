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


# What is written under a note that continues the word
# before it. A word sung across several notes appears once
# in the score, and the notes carrying it on are marked as
# held rather than left blank.
HELD_SYLLABLE = "_"


# A gap shorter than this is the ordinary space between
# notes rather than a rest anyone would write down.
SHORTEST_REST = 0.2


# Where a piece is divided into phrases to practise.
#
# A singer's phrase ends where they breathe, so a rest is
# the honest place to break. Music with no rests still has
# to be divided somehow, so no phrase may run past the cap.
# A break near the cap waits for a bar line when one is
# close, since breaking mid bar is awkward to count in, but
# the cap is never exceeded either way. Very short phrases
# are folded into the next, since three notes are not worth
# practising alone.
PHRASE_REST = 0.7
SHORTEST_PHRASE_NOTES = 4


# How long a phrase may run, in seconds.
#
# Seconds rather than notes, because a phrase is bounded
# by breath: fourteen sixteenth notes and fourteen half
# notes are the same count and nothing like the same
# phrase. And seconds rather than beats, because a beat is
# not a fixed length either. Twelve beats is ten seconds
# at seventy and four at a hundred and eighty, and a
# singer's lungs do not know the tempo.
#
# Past the comfortable length a phrase is divided at its
# own widest gap, which is where the singer was breathing
# even when the gap was too short to be written as a rest.
# The hard cap is for music that never gives them a gap
# at all, and is never exceeded.
COMFORTABLE_PHRASE_SECONDS = 8
LONGEST_PHRASE_SECONDS = 20


def beats_from_seconds(seconds, bpm):
    """
    How many beats fit in a length of time.
    """

    return seconds * bpm / 60


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


def read_all_notes(path):
    """
    Every note in a file, before anything is thrown away.

    Reducing to a single line is what singing needs, not
    what listening needs: the accompaniment and the other
    voices are what tell you the key. So detection reads
    this, and only then is the melody lifted out for the
    music boxes.

    Returns (pitches, durations) with one entry per note,
    overlaps and all.
    """

    try:
        midi_file = mido.MidiFile(path)

    except Exception:
        raise MidiImportError(
            "That file could not be read as MIDI."
        )

    notes, bpm = read_notes(midi_file)

    pitches = [
        midi_to_note(number)
        for start, length, number in notes
    ]

    durations = [
        length
        for start, length, number in notes
    ]

    return pitches, durations


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


def phrase_beats(phrase):
    """
    How long a phrase runs, in beats.
    """

    first = phrase[0][0]
    last = phrase[-1][0] + phrase[-1][1]

    return last - first


def split_at_widest_gap(phrase, longest_beats):
    """
    Divide an overlong phrase where it breathes most.

    The widest gap inside a phrase is where a singer took
    their breath, even when that gap was too short to be
    written as a rest. Splitting there keeps the division
    musical, where cutting at a note count would not.
    """

    if phrase_beats(phrase) <= longest_beats:
        return [phrase]

    widest = None
    widest_at = None

    previous_end = phrase[0][0] + phrase[0][1]

    for position in range(1, len(phrase)):

        start, length, midi_number = phrase[position]

        gap = start - previous_end

        # Keep both halves worth singing.
        room = (
            position >= SHORTEST_PHRASE_NOTES
            and len(phrase) - position >= SHORTEST_PHRASE_NOTES
        )

        if room and (widest is None or gap > widest):
            widest = gap
            widest_at = position

        previous_end = start + length

    if widest_at is None:
        return [phrase]

    return (
        split_at_widest_gap(
            phrase[:widest_at], longest_beats
        )
        + split_at_widest_gap(
            phrase[widest_at:], longest_beats
        )
    )


def split_into_phrases(
    melody,
    beats_per_bar=4,
    bpm=120
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

    comfortable_beats = beats_from_seconds(
        COMFORTABLE_PHRASE_SECONDS,
        bpm
    )

    longest_beats = beats_from_seconds(
        LONGEST_PHRASE_SECONDS,
        bpm
    )

    phrases = []
    current = [melody[0]]

    phrase_start = melody[0][0]
    previous_end = melody[0][0] + melody[0][1]

    for start, length, midi_number in melody[1:]:

        gap = start - previous_end
        so_far = start - phrase_start

        breaks_here = gap >= PHRASE_REST

        if not breaks_here:

            on_a_bar_line = (
                abs(start % beats_per_bar) < 0.01
            )

            # Within a bar of the cap, take a bar line if
            # one comes along.
            nearly_full = so_far >= (
                longest_beats - beats_per_bar
            )

            if nearly_full and on_a_bar_line:
                breaks_here = True

            # At the cap, break wherever we are.
            elif so_far >= longest_beats:
                breaks_here = True

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

    # Divide anything still too long at its widest breath.
    divided = []

    for phrase in joined:
        divided.extend(
            split_at_widest_gap(phrase, comfortable_beats)
        )

    return divided


def bar_span(phrase, beats_per_bar=4):
    """
    The bar lines either side of a phrase.

    Phrases are split where the music breathes, and a
    breath rarely falls on a bar line: a line may begin on
    a pickup and end part way through a beat. That is
    correct as music and awkward as data, since a chord
    chart is written in bars and the metronome marks a
    downbeat, and neither can line up with a phrase that
    starts and stops mid-bar.

    Returns (start, end) in beats.
    """

    first_start = phrase[0][0]

    last_start, last_length, last_pitch = phrase[-1]

    phrase_end = last_start + last_length

    start = int(first_start // beats_per_bar) * beats_per_bar

    bars = -(-(phrase_end - start) // beats_per_bar)

    return start, start + bars * beats_per_bar


def notes_to_text(melody, span=None):
    """
    Turn a list of notes into pitch and duration text.

    Silence between notes becomes a rest, so the timing
    survives. Silence before the first note is dropped:
    music begins where it begins.

    Given a span of whole bars to fill, the silence at
    either end is written as a rest instead. Those rests
    are real music rather than filler: the one before a
    pickup is time the singer counts, and the one after
    the last note is where they breathe.
    """

    pitches = []
    durations = []

    previous_end = melody[0][0]

    if span is not None:

        span_start, span_end = span

        if melody[0][0] > span_start:
            pitches.append(REST)
            durations.append(
                snap_to_beat(melody[0][0] - span_start)
            )

    for start, length, midi_number in melody:

        gap = start - previous_end

        if gap >= SHORTEST_REST:
            pitches.append(REST)
            durations.append(snap_to_beat(gap))

        pitches.append(midi_to_note(midi_number))
        durations.append(snap_to_beat(length))

        previous_end = start + length

    if span is not None:

        span_start, span_end = span

        # Every length is snapped to the nearest sensible
        # fraction of a beat, and those roundings add up,
        # so the notes rarely total exactly what the bars
        # say. The closing rest takes up the difference:
        # it is the one length nobody is counting.
        wanted = span_end - span_start

        so_far = sum(durations)

        remaining = wanted - so_far

        if remaining >= SHORTEST_REST:
            pitches.append(REST)
            durations.append(remaining)

        elif remaining and durations:
            durations[-1] += remaining

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
            read_time_signature(midi_file),
            bpm
        )

        if phrase_number < 0 or phrase_number >= len(phrases):
            raise MidiImportError(
                "That phrase is not in this music."
            )

        melody = phrases[phrase_number]

        # A phrase is padded out to the bars around it, so
        # that its chords, bar lines and downbeats all have
        # somewhere to sit.
        span = bar_span(melody, read_time_signature(midi_file))

    else:
        span = None

    if maximum_notes is not None:
        melody = melody[:maximum_notes]
        span = None

    pitch_text, duration_text = notes_to_text(melody, span)

    lyric_text = read_lyric_text(
        midi_file,
        melody,
        track_number
    )

    # Chords come from every voice sounding together, not
    # from the one being sung.
    all_notes, all_bpm = read_notes(midi_file)

    chart_text = read_chart_text(
        midi_file,
        all_notes,
        span,
        read_time_signature(midi_file)
    )

    return pitch_text, duration_text, lyric_text, bpm, chart_text


def read_chart_text(midi_file, notes, span, beats_per_bar=4):
    """
    Read the chords out of the whole texture.

    The chords come from every voice sounding together,
    not from the part being sung: a soprano line alone
    holds no chords, while the four parts of a hymn spell
    one out on every beat.

    Only for a phrase, since that is what has been padded
    to whole bars, and a chart has to fit the music it is
    written above.
    """

    if span is None:
        return ""

    from chord_detector import chart_from_notes

    span_start, span_end = span

    within = []

    for start, length, midi_number in notes:

        if start + length <= span_start or start >= span_end:
            continue

        within.append(
            (
                max(0.0, start - span_start),
                length,
                midi_number
            )
        )

    if not within:
        return ""

    return chart_from_notes(
        within,
        span_end - span_start,
        beats_per_bar
    )


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

    phrases = split_into_phrases(melody, beats_per_bar, bpm)

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


def read_lyric_events(midi_file, track_number=None):
    """
    Collect a track's lyrics with the time each falls at.

    Lyrics belong to a voice, not to a file: notation
    software writes them into the staff they are sung on,
    so a choral export carries a separate set under every
    part. Reading them all together would give four times
    the syllables and match nothing.

    Returns a list of (beats, text).
    """

    ticks_per_beat = midi_file.ticks_per_beat

    events = []

    for position, track in enumerate(midi_file.tracks):

        if track_number is not None and position != track_number:
            continue

        time_ticks = 0

        for message in track:

            time_ticks += message.time

            if message.type != "lyrics":
                continue

            text = message.text.strip()

            if text:
                events.append(
                    (time_ticks / ticks_per_beat, text)
                )

    return events


def lyrics_for(melody, events, tolerance=0.05):
    """
    Line a track's syllables up with the notes it sings.

    Each syllable belongs to the note starting at the same
    moment, which is what lets a single phrase be lifted
    out of a whole piece with its own words attached.

    Not every note carries a syllable. A word sung across
    several notes is written once and held, so the notes
    that continue it have nothing of their own. Those are
    marked as held, which is what they are, rather than
    throwing away the words that did match.

    Returns an empty list only when nothing matched at
    all, since words that line up with nothing are worse
    than no words.
    """

    if len(events) == 0:
        return []

    syllables = []
    matched = 0

    for start, length, midi_number in melody:

        found = None

        for moment, text in events:
            if abs(moment - start) <= tolerance:
                found = text
                break

        if found is None:
            syllables.append(HELD_SYLLABLE)

        else:
            syllables.append(found)
            matched += 1

    if matched == 0:
        return []

    return syllables


def read_lyric_text(midi_file, melody, track_number=None):
    """
    The words sung by these notes, as lyric box text.
    """

    events = read_lyric_events(midi_file, track_number)

    syllables = lyrics_for(melody, events)

    return " ".join(syllables)