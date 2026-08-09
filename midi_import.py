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


# The channel every General MIDI file reserves for
# percussion. The numbers on it name drums rather than
# pitches, so a bass drum and a cymbal read as two notes
# a fifth apart. It is described as what it is and left
# available: a drum part is worth practising, and this app
# will not always be only for singers.
DRUM_CHANNEL = 9


# What the General MIDI numbers mean. A file rarely names
# its parts, but it almost always says which instrument
# plays each one, and "Alto Sax" tells a player more about
# what they are choosing than "channel 4" ever could.
GM_INSTRUMENTS = [
    "Grand Piano", "Bright Piano", "Electric Grand",
    "Honky-tonk Piano", "Electric Piano", "Electric Piano 2",
    "Harpsichord", "Clavinet",
    "Celesta", "Glockenspiel", "Music Box", "Vibraphone",
    "Marimba", "Xylophone", "Tubular Bells", "Dulcimer",
    "Drawbar Organ", "Percussive Organ", "Rock Organ",
    "Church Organ", "Reed Organ", "Accordion", "Harmonica",
    "Tango Accordion",
    "Nylon Guitar", "Steel Guitar", "Jazz Guitar",
    "Clean Guitar", "Muted Guitar", "Overdriven Guitar",
    "Distortion Guitar", "Guitar Harmonics",
    "Acoustic Bass", "Finger Bass", "Pick Bass",
    "Fretless Bass", "Slap Bass", "Slap Bass 2",
    "Synth Bass", "Synth Bass 2",
    "Violin", "Viola", "Cello", "Double Bass",
    "Tremolo Strings", "Pizzicato Strings", "Harp", "Timpani",
    "String Ensemble", "String Ensemble 2", "Synth Strings",
    "Synth Strings 2", "Choir Aahs", "Voice Oohs",
    "Synth Voice", "Orchestra Hit",
    "Trumpet", "Trombone", "Tuba", "Muted Trumpet",
    "French Horn", "Brass Section", "Synth Brass",
    "Synth Brass 2",
    "Soprano Sax", "Alto Sax", "Tenor Sax", "Baritone Sax",
    "Oboe", "English Horn", "Bassoon", "Clarinet",
    "Piccolo", "Flute", "Recorder", "Pan Flute",
    "Blown Bottle", "Shakuhachi", "Whistle", "Ocarina",
    "Square Lead", "Sawtooth Lead", "Calliope Lead",
    "Chiff Lead", "Charang Lead", "Voice Lead",
    "Fifths Lead", "Bass and Lead",
    "New Age Pad", "Warm Pad", "Polysynth Pad", "Choir Pad",
    "Bowed Pad", "Metallic Pad", "Halo Pad", "Sweep Pad",
    "Rain", "Soundtrack", "Crystal", "Atmosphere",
    "Brightness", "Goblins", "Echoes", "Sci-fi",
    "Sitar", "Banjo", "Shamisen", "Koto", "Kalimba",
    "Bagpipe", "Fiddle", "Shanai",
    "Tinkle Bell", "Agogo", "Steel Drums", "Woodblock",
    "Taiko Drum", "Melodic Tom", "Synth Drum", "Reverse Cymbal",
    "Guitar Fret Noise", "Breath Noise", "Seashore",
    "Bird Tweet", "Telephone Ring", "Helicopter",
    "Applause", "Gunshot"
]


def instrument_name(program, channel=None):
    """
    What to call a part, from its instrument number.
    """

    if channel == DRUM_CHANNEL:
        return "Drums"

    if program is None:
        return "Unnamed"

    if 0 <= program < len(GM_INSTRUMENTS):
        return GM_INSTRUMENTS[program]

    return f"Instrument {program}"


def read_notes(midi_file, track_number=None, channel=None):
    """
    Collect every note in the file with its absolute start
    time and length, in beats.

    track_number picks a single track and channel picks a
    single instrument within it. Either left as None means
    take everything.

    Both are needed because files divide their parts two
    different ways. A file written by a notation program
    usually gives each voice its own track. A file written
    by a sequencer often puts everything on one track and
    separates the instruments by channel, which is how a
    band arrangement usually arrives. Reading only tracks
    finds one part in such a file: all of them at once.

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

        # Which channel each message belongs to, when only
        # one is wanted.
        def on_wanted_channel(message):

            if channel is None:
                return True

            return getattr(message, "channel", None) == channel

        for message in track:

            time_ticks += message.time

            if message.type == "set_tempo" and bpm is None:
                bpm = round(mido.tempo2bpm(message.tempo))

            elif not wanted or not on_wanted_channel(message):
                continue

            elif message.type == "note_on" and message.velocity > 0:

                # Several notes of the same pitch can sound
                # at once: a piano part repeating a note
                # under a held pedal, or two voices meeting
                # on the same pitch. Keeping only the latest
                # start would lose every one but the last,
                # so they are stacked and matched in turn.
                sounding.setdefault(message.note, []).append(
                    time_ticks
                )

            elif message.type in ("note_off", "note_on"):

                # A note_on with zero velocity is the other
                # accepted way of ending a note.
                starts = sounding.get(message.note)

                if not starts:
                    continue

                started = starts.pop(0)

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


def describe_parts(path):
    """
    Summarise every part a file holds, likeliest tune first.

    Returns a list of (identifier, description), where the
    identifier says which track and channel the part lives
    on. The description is what a player reads when
    choosing, so it names the instrument and its range
    rather than a number.
    """

    try:
        midi_file = mido.MidiFile(path)

    except Exception:
        raise MidiImportError(
            "That file could not be read as MIDI."
        )

    parts = rank_parts(midi_file, find_parts(midi_file))

    described = []

    for part in parts:

        identifier = f"{part['track']}:{part['channel']}"

        text = describe_part(part)

        if part["likely_melody"] and not described:
            text += " - probably the tune"

        elif not part["single_line"]:
            text += " - chords"

        elif part.get("density", 0) > MOST_NOTES_PER_BEAT:
            text += " - too busy to sing"

        described.append((identifier, text))

    return described


def read_part_choice(identifier):
    """
    Turn a part identifier back into track and channel.
    """

    if identifier is None:
        return None, None

    text = str(identifier)

    if ":" not in text:
        return None, None

    track, _, channel = text.partition(":")

    try:
        return int(track), int(channel)

    except ValueError:
        return None, None


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


def lyrics_with_line_breaks(melody, phrases, syllables):
    """
    Write the lyrics out with a line break per phrase.

    The splitter's guess at the phrasing, written where it
    can be corrected. Nothing downstream reads the guess
    again: from here the line breaks are the phrasing, and
    changing one changes the music it divides.
    """

    if not syllables:
        return ""

    starts = set()

    counted = 0

    for phrase in phrases:

        if counted:
            starts.add(counted)

        counted += len([
            note for note in phrase
            if True
        ])

    lines = []

    current = []

    for position in range(len(syllables)):

        if position in starts and current:
            lines.append(" ".join(current))
            current = []

        syllable = syllables[position]

        current.append(syllable if syllable else HELD_SYLLABLE)

    if current:
        lines.append(" ".join(current))

    return "\n".join(lines)


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
                phrase_number=None, channel=None):
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

    notes, bpm = read_notes(midi_file, track_number, channel)

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

    chart_text, chart_notes = read_chart_text(
        midi_file,
        all_notes,
        span,
        read_time_signature(midi_file)
    )

    return (
        pitch_text,
        duration_text,
        lyric_text,
        bpm,
        chart_text,
        chart_notes
    )


def spelling_key(notes):
    """
    Which key to spell the chords in.

    Read from the music itself, since a file rarely says.
    Only the spelling depends on it: B flat and A sharp are
    the same chord, and this decides which way a singer
    reads it.
    """

    from key_detector import detect_key
    from notes import midi_to_note

    if not notes:
        return None

    names = [midi_to_note(number) for start, length, number in notes]

    lengths = [length for start, length, number in notes]

    best, score = detect_key(names, lengths)[0]

    tonic, space, kind = best.partition(" ")

    if kind == "minor":

        from harmony import RELATIVE_MINORS

        for major, minor in RELATIVE_MINORS.items():
            if minor == tonic:
                return major

        return None

    return tonic


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
        return "", []

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
        return "", []

    return chart_from_notes(
        within,
        span_end - span_start,
        beats_per_bar,
        key=spelling_key(notes)
    ), within


def describe_phrases(path, track_number=None, channel=None):
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

    notes, bpm = read_notes(midi_file, track_number, channel)

    if len(notes) == 0:
        raise MidiImportError(
            "No notes were found in that track."
        )

    melody = keep_melody(notes)

    beats_per_bar = read_time_signature(midi_file)

    events = read_lyric_events(midi_file, track_number)

    phrases = split_into_phrases(melody, beats_per_bar, bpm)

    described = []

    for position, phrase in enumerate(phrases):

        first_bar = int(phrase[0][0] / beats_per_bar) + 1

        last = phrase[-1]
        last_bar = int(
            (last[0] + last[1] - 0.01) / beats_per_bar
        ) + 1

        described.append((
            position,
            f"Phrase {position + 1} "
            f"(bars {first_bar} to {last_bar}, "
            f"{len(phrase)} notes): "
            + phrase_opening(phrase, events)
        ))

    return described


# How much of a phrase to show in the list. Enough to know
# which phrase it is, short enough to read at a glance.
OPENING_WORDS = 6


def phrase_opening(phrase, events=None):
    """
    The few words or notes that identify a phrase.

    Words where the music has them. "There once was a
    ship" tells a singer which phrase this is; the same
    phrase written as A#3 C4 C4 C4 C4 tells them almost
    nothing, and they would have to load each one to find
    out.
    """

    if events:

        syllables = lyrics_for(phrase, events)

        words = join_syllables(syllables)

        if words:
            return words

    return " ".join(
        midi_to_note(number)
        for start, length, number in phrase[:5]
    )


def join_syllables(syllables):
    """
    Put sung syllables back together into words.

    Syllables arrive one to a note, hyphenated where a word
    runs across several, and marked where a word is held.
    Reading them as they come gives "Twin- kle twin- kle",
    which is not how anyone would say it.
    """

    words = []

    building = ""

    for syllable in syllables:

        if syllable in (None, "", HELD_SYLLABLE):
            continue

        if syllable.endswith("-"):
            building += syllable[:-1]

        else:
            words.append(building + syllable)
            building = ""

        if len(words) >= OPENING_WORDS:
            break

    if building and len(words) < OPENING_WORDS:
        words.append(building)

    return " ".join(words)


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


def find_parts(midi_file):
    """
    Every separate part in a file, however it divides them.

    Files divide their parts two different ways. A notation
    program gives each voice its own track. A sequencer
    often puts everything on one track and separates the
    instruments by channel, which is how band and pop
    arrangements usually arrive. Looking only at tracks
    finds one part in such a file, containing all of them
    at once, which is why a whole arrangement can import as
    an unsingable tangle.

    Returns a list of dictionaries, one per part, with the
    track and channel that identify it and enough about its
    contents to choose by.
    """

    programs = {}

    found = {}

    for position in range(len(midi_file.tracks)):

        track = midi_file.tracks[position]

        for message in track:

            if message.type == "program_change":
                programs[(position, message.channel)] = (
                    message.program
                )

            if message.type != "note_on" or message.velocity == 0:
                continue

            channel = getattr(message, "channel", 0)

            key = (position, channel)

            if key not in found:
                found[key] = []

            found[key].append(message.note)

    parts = []

    for (position, channel) in sorted(found):

        numbers = found[(position, channel)]

        parts.append({
            "track": position,
            "channel": channel,
            "notes": len(numbers),
            "lowest": min(numbers),
            "highest": max(numbers),
            "average": sum(numbers) / len(numbers),
            "program": programs.get((position, channel)),
            "name": instrument_name(
                programs.get((position, channel)),
                channel
            ),
            "percussion": channel == DRUM_CHANNEL
        })

    return parts


def describe_part(part, most_notes=1):
    """
    One line describing a part, for choosing between them.
    """

    pieces = [part["name"]]

    if part["percussion"]:
        pieces.append("percussion, not pitched")

    else:
        pieces.append(
            midi_to_note(part["lowest"])
            + " to "
            + midi_to_note(part["highest"])
        )

    pieces.append(f"{part['notes']} notes")

    return ", ".join(pieces)


def measure_part(midi_file, part):
    """
    How singable a part is, and how like a melody.

    Two measurements, because one is not enough. How often
    the part sounds two notes at once tells a chord part
    from a single line. How many notes it plays to the beat
    tells a tune from an arpeggiated accompaniment, which
    is also one note at a time and otherwise looks exactly
    like a melody.

    Returns (overlap, notes per beat).
    """

    notes, bpm = read_notes(
        midi_file,
        track_number=part["track"],
        channel=part["channel"]
    )

    if not notes:
        return 0.0, 0.0

    span = (
        max(start + length for start, length, n in notes)
        - min(start for start, length, n in notes)
    )

    density = len(notes) / span if span else 0.0

    overlapping = 0

    for position in range(len(notes)):

        start, length, number = notes[position]

        for other in notes[position + 1:]:

            if other[0] >= start + length:
                break

            if other[0] < start + length:
                overlapping += 1
                break

    return overlapping / len(notes), density


# How much of a part may overlap itself before it stops
# being a single line. A little is ordinary: notes ring
# into each other, and a player holds one while starting
# the next.
SINGLE_LINE_LIMIT = 0.2


# How many notes to the beat a part may have and still be
# a tune someone sings.
#
# This is the signal that tells a melody from an
# arpeggiated accompaniment, which the single line test
# cannot: an arpeggio is one note at a time too, and looks
# exactly like a melody until you count them. A sung line
# rarely passes two notes to the beat for long, while a
# broken chord figure runs at three or four without
# pausing. Measured over a real hymn, the voices sit under
# one note per beat and the piano reduction at nearly
# three.
MOST_NOTES_PER_BEAT = 2.0


def rank_parts(midi_file, parts):
    """
    Order parts by how likely each is to be the tune.

    Nothing is hidden. A guess about which part is the
    melody is only a guess, and a file may well be imported
    to practise the bass line or the inner voice. So the
    likeliest is offered first and the rest stay where they
    can be chosen.
    """

    measured = []

    for part in parts:

        overlap, density = measure_part(midi_file, part)

        single_line = overlap <= SINGLE_LINE_LIMIT

        singable = density <= MOST_NOTES_PER_BEAT

        # A tune is a single line, in a comfortable
        # register, with enough notes to be worth singing.
        score = 0.0

        if part["percussion"]:
            score -= 10

        if single_line:
            score += 3

        if singable:
            score += 3

        if 55 <= part["average"] <= 75:
            score += 2

        if part["notes"] >= 12:
            score += 1

        measured.append(
            (score, part, single_line, overlap, density)
        )

    measured.sort(key=lambda entry: -entry[0])

    ordered = []

    for score, part, single_line, overlap, density in measured:

        described = dict(part)
        described["single_line"] = single_line
        described["overlap"] = overlap
        described["density"] = density
        described["likely_melody"] = score >= 8

        ordered.append(described)

    return ordered


# Splitting a line of music into phrases.
#
# No single sign of a phrase ending is reliable. A rest is
# the clearest, and legato arrangements have none at all. A
# bar line is always there and knows nothing about where a
# line of the song began. Lyrics are the strongest evidence
# there is, and most files carry none.
#
# So the signs vote. A boundary has to be agreed on by more
# than one before the music is cut there, and where they
# disagree the phrase runs on. That is the right way to be
# wrong: a phrase too long is still practisable - sing it,
# breathe where you need to - while a phrase cut mid-line
# is unusable and teaches a shape the song does not have.

# What each sign is worth. A rest counts most because a
# breath is what a phrase ending actually is; the rest are
# corroboration.
REST_EVIDENCE = 3.0
LONG_NOTE_EVIDENCE = 2.0
LYRIC_GAP_EVIDENCE = 2.5
FOUR_BAR_EVIDENCE = 1.5
TWO_BAR_EVIDENCE = 0.75

# The least a boundary must show before it can be used at
# all. One weak sign is not evidence of anything.
SOME_EVIDENCE = 2.0

# How close two boundaries have to be before they are
# treated as the same one, as a fraction of a phrase.
CLOSE_ENOUGH = 0.45

# How far up its own file's boundaries a break has to sit.
STANDS_OUT_SHARE = 0.5

# How long a phrase should be, in seconds of singing.
#
# The threshold for cutting cannot be a fixed score,
# because how much evidence a file offers is a property of
# the file. A quantised hymn has rests and bar lines
# agreeing at every line ending and scores six; a recorded
# line has no rests and no bar lines and scores five at its
# clearest break and nothing anywhere else. A number that
# suits one silences the other.
#
# So the boundaries are ranked and the strongest taken:
# as many as it takes to leave phrases of a length someone
# can practise. The music decides where the cuts fall and
# this decides how many.
TARGET_PHRASE_SECONDS = 11

# A note counts as long, and a gap as a rest, relative to
# what is ordinary in this piece rather than by a fixed
# number of beats. A crotchet is a long note in a piece of
# semiquavers and a short one in a piece of minims.
# What counts as long or as a gap is decided by where it
# stands among the rest of the piece, not by a multiple of
# the middle value.
#
# A multiple works where the music is varied and fails at
# both extremes. In a hymn of even crotchets nothing is
# ever long enough; in a slow ballad of held notes every
# single note passes, and a measure that fires everywhere
# says as little as one that never fires. Asking instead
# which lengths are unusual for this piece gives the same
# answer in both.
UNUSUAL_SHARE = 0.9

# Rests are measured from one note beginning to the next,
# not from where a note stops sounding.
#
# Sequenced files shorten every note a little so that
# repeated notes can be heard apart, which leaves a gap
# after all of them. Measuring silence finds a rest
# everywhere and phrases nowhere. What actually marks a
# break is the next note arriving late: the pulse carrying
# on with nothing on it.

# How near a bar line a note must fall to count as being
# on it, as a fraction of a bar. Played music drifts, and
# a downbeat sung a little late is still a downbeat.
BAR_TOLERANCE = 0.08


# Past this a phrase is too long to practise whatever the
# evidence says, and the best boundary available is taken.
UNWIELDY_SECONDS = 30

# And below this it is not worth offering on its own.
LEAST_PHRASE_NOTES = 3


def typical_length(melody):
    """
    The ordinary note length in a piece of music.

    Used to judge what counts as a long note or a real
    rest, since both are relative: a crotchet is long in a
    piece of semiquavers and short in a piece of minims.
    """

    lengths = sorted(length for start, length, n in melody)

    if not lengths:
        return 1.0

    return lengths[len(lengths) // 2]


def unusually_large(values, share=UNUSUAL_SHARE):
    """
    The size a value must reach to be unusual here.

    Everything is judged against the piece it belongs to.
    """

    ordered = sorted(values)

    if not ordered:
        return 0.0

    place = min(
        len(ordered) - 1,
        int(len(ordered) * share)
    )

    return ordered[place]


def typical_spacing(melody):
    """
    The ordinary distance from one note to the next.

    The pulse of the music as written, which is what tells
    a rest from a note merely played short.
    """

    if len(melody) < 2:
        return 1.0

    spacings = sorted(
        melody[position][0] - melody[position - 1][0]
        for position in range(1, len(melody))
    )

    return spacings[len(spacings) // 2] or 1.0


def gather_evidence(melody, beats_per_bar, lyric_times=None):
    """
    How strongly each note is preceded by a phrase ending.

    Returns a list of scores, one per note, saying how much
    the signs agree that a new phrase begins there.
    """

    if len(melody) < 2:
        return [0.0] * len(melody)

    lengths = [length for start, length, n in melody]

    spacings = [
        melody[position][0] - melody[position - 1][0]
        for position in range(1, len(melody))
    ]

    long_note = unusually_large(lengths)
    real_rest = unusually_large(spacings)

    # Where everything is the same size nothing is unusual,
    # and the measure should stay quiet rather than fire at
    # every note. A piece of even crotchets has no long
    # notes in it, however the numbers are sliced.
    if long_note <= typical_length(melody) * 1.05:
        long_note = None

    if real_rest <= typical_spacing(melody) * 1.05:
        real_rest = None

    # A short line has too few gaps for a share of them to
    # mean anything, and one plain rest in ten notes is
    # still a phrase ending. Below that, the largest gap
    # speaks for itself if it is clearly larger.
    if real_rest is None and len(spacings) >= 2:

        largest = max(spacings)

        if largest >= typical_spacing(melody) * 1.6:
            real_rest = largest

    first_bar_start = (
        int(melody[0][0] // beats_per_bar) * beats_per_bar
    )

    scores = [0.0] * len(melody)

    for position in range(1, len(melody)):

        start = melody[position][0]

        previous_start, previous_length, n = melody[position - 1]

        previous_end = previous_start + previous_length

        score = 0.0

        # A breath: the next note arriving later than the
        # pulse would have it.
        if real_rest and start - previous_start >= real_rest:
            score += REST_EVIDENCE

        # A note held at the end of a line.
        if long_note and previous_length >= long_note:
            score += LONG_NOTE_EVIDENCE

        # A gap in the words, where there are words.
        if lyric_times:

            before = [
                time for time in lyric_times if time <= previous_end
            ]

            after = [time for time in lyric_times if time >= start]

            if (
                real_rest
                and before
                and after
                and after[0] - before[-1] >= real_rest
            ):
                score += LYRIC_GAP_EVIDENCE

        # Falling on a bar line, and how regular a one.
        from_start = start - first_bar_start

        # Played files are not quantised: a downbeat sung
        # a fraction late is still a downbeat, and asking
        # for exactness finds bar lines only in music
        # typed by a machine.
        on_bar = abs(
            from_start / beats_per_bar
            - round(from_start / beats_per_bar)
        ) < BAR_TOLERANCE

        if on_bar:

            bars_in = round(from_start / beats_per_bar)

            if bars_in % 4 == 0:
                score += FOUR_BAR_EVIDENCE

            elif bars_in % 2 == 0:
                score += TWO_BAR_EVIDENCE

        scores[position] = score

    return scores


def split_by_agreement(
    melody,
    beats_per_bar=4,
    bpm=120,
    lyric_times=None
):
    """
    Divide a line into phrases where the signs agree.

    NOT IN USE. Kept because the measurements in it are
    sound and the failure is worth recording.

    Inclusive by default: the music is only cut where more
    than one sign of an ending falls together. The idea is
    right and the thresholds are not. Every setting that
    suits one file spoils another - a quantised hymn agrees
    at six where a recorded line agrees at five and is
    silent everywhere else, a slow ballad of held notes
    makes every note look like an ending, and judging by
    what is unusual for the piece only moves the problem to
    how many boundaries the piece happens to have.

    What the attempt did establish, and what any second
    attempt should keep:

    - rests must be measured from one note beginning to
      the next, not from where a note stops sounding, or
      sequenced files show a rest after every note
    - played files are not quantised, so bar lines have to
      be matched loosely or they never match at all
    - some files have no rests and no bar alignment
      whatever, and their phrases can only come from the
      words or from nothing
    - the signs genuinely do agree at real line endings;
      it is choosing among them that is unsolved
    """

    if len(melody) == 0:
        return []

    scores = gather_evidence(melody, beats_per_bar, lyric_times)

    total_beats = (
        melody[-1][0] + melody[-1][1] - melody[0][0]
    )

    target = beats_from_seconds(TARGET_PHRASE_SECONDS, bpm)

    # Two boundaries close together are the same ending
    # seen twice: the rest before the last note of a line
    # and the bar line after it both point at one break.
    # Taking the stronger and setting aside its neighbours
    # keeps phrases evenly sized, which taking the highest
    # scores alone does not - they arrive in clusters and
    # leave long stretches uncut between them.
    apart = target * CLOSE_ENOUGH

    # A boundary has to stand out among this file's own
    # boundaries, not reach a fixed score. One file agrees
    # at six and another at five, and neither number means
    # anything outside the piece it came from.
    speaking = [
        scores[position]
        for position in range(1, len(melody))
        if scores[position] >= SOME_EVIDENCE
    ]

    if not speaking:
        return [melody]

    stands_out = unusually_large(speaking, STANDS_OUT_SHARE)

    offered = [
        (scores[position], position)
        for position in range(1, len(melody))
        if scores[position] >= max(SOME_EVIDENCE, stands_out)
    ]

    offered.sort(reverse=True)

    chosen = []

    for score, position in offered:

        where = melody[position][0]

        if any(
            abs(where - melody[taken][0]) < apart
            for taken in chosen
        ):
            continue

        chosen.append(position)

    chosen = sorted(chosen)

    phrases = []

    current = [melody[0]]

    for position in range(1, len(melody)):

        if (
            position in chosen
            and len(current) >= LEAST_PHRASE_NOTES
        ):
            phrases.append(current)
            current = []

        current.append(melody[position])

    if current:

        if phrases and len(current) < LEAST_PHRASE_NOTES:
            phrases[-1] += current

        else:
            phrases.append(current)

    return phrases