# musicxml_import.py

"""
Read a score, rather than reconstruct one.

MIDI is a record of a performance. What it holds is when
notes started and stopped, which is why importing one
means inferring everything a score would have said: what
the written lengths were, where the bars fall, what key it
is in, where the phrases end. A whole subsystem exists to
undo the drift of a file played at one speed and marked at
another, and it earned its place.

MusicXML holds the score itself. The lengths are written
values, the metre and key are stated, parts have their own
names, and lyrics are attached to the notes they are sung
on. So none of the repair applies here - not because it
was skipped, but because the questions it answers are
already answered in the file.

music21 does the reading. That is a deliberate choice: the
format is large and its corners are genuinely awkward -
repeats and voltas, ties across barlines, several voices
in one staff, transposing instruments, divisions changing
mid-score - and a hand-written parser meets those one file
at a time, in the middle of doing something else. The
library has met them already.

It is kept thin, though. music21's own model of music -
its Streams and Notes and Durations - stops at the edge of
this module, and what leaves here is what leaves the MIDI
importer: text for the boxes. Letting a second model of
music flow through the app would put a translation between
every part of it and every other.
"""

import re
import zipfile
from fractions import Fraction

from chord_detector import chart_from_notes
from midi_import import spelling_key
from notes import REST, midi_to_note


# Lengths are rounded to something notation can express.
# A score should already hold such values, but a file
# written by hand or converted from elsewhere can carry a
# length a hair off, and a box holding 0.9999 beats is not
# a box anyone can read.
ROUNDING = 64

# A rest this long or longer is taken to end a phrase.
PHRASE_REST = 1

# How long a rest may be before it is written as bars of
# rest instead. Invariant 9: a singer counting through an
# instrumental counts bars.
LONGEST_REST = 4


def parts_in(path):
    """
    The parts of a score, named as the score names them.

    No guessing from General MIDI programs: a MusicXML part
    carries the name the composer or engraver gave it, and
    a part with lyrics is a part someone sings.
    """

    score = _read(path)

    described = []

    for index, part in enumerate(score.parts):

        notes = list(part.flatten().notes)

        if not notes:
            continue

        sung = len([note for note in notes if note.lyric])

        name = part.partName or f"Part {index + 1}"

        label = f"{index}  {name}, {len(notes)} notes"

        if sung:
            label += f", {sung} with words"

        described.append(label)

    return described


def part_number_from(label):
    """
    Which part a chosen label refers to.
    """

    if label is None:
        return 0

    match = re.match(r"\s*(\d+)", str(label))

    return int(match.group(1)) if match else 0


def _read(path):
    """
    Parse a score, compressed or not.
    """

    from music21 import converter

    return converter.parse(path)


def _round(length):
    """
    A length as a fraction a box can hold.
    """

    return Fraction(length).limit_denominator(ROUNDING)


def _merge_ties(items):
    """
    A note tied to the next is one note, sung once.

    The file writes it as two because a bar line came
    between them, which is a fact about the page and not
    about the singing. Left as two, the second gets no
    syllable and the words slide.
    """

    merged = []

    for item in items:

        tie = getattr(item, "tie", None)

        if (
            tie is not None
            and tie.type in ("stop", "continue")
            and merged
            and not merged[-1][0]
        ):
            # Add the length to the note it continues.
            merged[-1][1] += _round(item.quarterLength)
            continue

        merged.append([
            item.isRest,
            _round(item.quarterLength),
            item
        ])

    return merged


def _word_ends(path, part_index):
    """
    Which syllables end a word, read from the file itself.

    MusicXML can mark this properly - a syllable is begin,
    middle, end or single - but files often mark every
    syllable "single" and rely on a trailing space in the
    text instead, which is how a printed score is typed.
    music21 strips that space, so it is read here from the
    XML directly.

    Returns a list of booleans, or None when the file does
    not say. None means every syllable is treated as its
    own word, which is wrong but visibly wrong: the words
    can be pasted in and corrected.
    """

    try:

        if zipfile.is_zipfile(path):

            with zipfile.ZipFile(path) as archive:

                name = [
                    item for item in archive.namelist()
                    if item.endswith(".xml")
                    and not item.startswith("META-INF")
                ]

                if not name:
                    return None

                xml = archive.read(name[0]).decode("utf-8", "ignore")

        else:
            xml = open(path, encoding="utf-8", errors="ignore").read()

    except (OSError, zipfile.BadZipFile):
        return None

    bodies = re.findall(r"<part id=[^>]*>(.*?)</part>", xml, re.S)

    if part_index >= len(bodies):
        return None

    texts = re.findall(
        r"<lyric[^>]*>.*?<text[^>]*>(.*?)</text>",
        bodies[part_index],
        re.S
    )

    if not texts:
        return None

    # A trailing space says the word ended there. If no
    # syllable has one, the file is not using the
    # convention and nothing can be read from it.
    ends = [text != text.rstrip() for text in texts]

    if not any(ends):
        return None

    return ends


def _rests_as_bars(length, beats_per_bar):
    """
    A long silence as bars of rest.
    """

    pieces = []

    remaining = length

    while remaining > beats_per_bar:
        pieces.append(Fraction(beats_per_bar))
        remaining -= beats_per_bar

    if remaining > 0:
        pieces.append(remaining)

    return pieces


def verses_in(path, part_label=None):
    """
    Which verses a part carries.

    A carol writes several verses under one line of notes,
    numbered. The boxes hold one syllable per note, so they
    hold one verse; this says which are on offer.
    """

    score = _read(path)

    parts = [
        part for part in score.parts
        if list(part.flatten().notes)
    ]

    if not parts:
        return []

    part = parts[min(part_number_from(part_label), len(parts) - 1)]

    numbers = set()

    for item in part.flatten().notes:
        for lyric in item.lyrics:
            if lyric.number:
                numbers.add(lyric.number)

    return sorted(numbers)


def _syllable(item, verse):
    """
    The syllable sung on a note, in the chosen verse.

    Taken from the numbered lyrics rather than from
    music21's convenience property, which joins every
    verse of a note into one string with newlines between
    them. That string went into the boxes as a single
    token and split into several later, so a score with
    two verses arrived with more syllables than notes.

    The hyphen that says a word continues comes from the
    file's own marking where it has one - begin and middle
    mean the word goes on - which is how notation software
    writes it. rawText carries the hyphen already.
    """

    for lyric in item.lyrics:

        if lyric.number and lyric.number != verse:
            continue

        text = (lyric.text or "").strip()

        if not text:
            continue

        if lyric.syllabic in ("begin", "middle"):

            if not text.endswith("-"):
                text += "-"

        return text.replace(" ", "")

    return None


def import_musicxml(path, part_label=None, verse=1):
    """
    A score into the boxes.

    Returns the same eight things the MIDI importer does,
    so the two are interchangeable to everything above:
    pitches, durations, lyrics, tempo, feedback, chart,
    the polyphony behind the chart, and the key.
    """

    score = _read(path)

    index = part_number_from(part_label)

    parts = [
        part for part in score.parts
        if list(part.flatten().notes)
    ]

    if not parts:
        raise ValueError(
            "This score has no notes in any part."
        )

    index = min(index, len(parts) - 1)

    part = parts[index]

    # The metre, as stated rather than inferred - and read
    # from the library rather than worked out from the
    # numerator. Six eight is six eighth notes, which is
    # three beats, not six: taking the numerator drew every
    # bar line at twice its width, and only in compound
    # time, where four four hid it.
    signatures = list(
        part.recurse().getElementsByClass("TimeSignature")
    )

    beats_per_bar = 4
    metre = None

    if signatures:
        metre = signatures[0]
        beats_per_bar = float(metre.barDuration.quarterLength)

    # The tempo, if the score carries one.
    marks = list(score.recurse().getElementsByClass("MetronomeMark"))

    bpm = int(round(marks[0].number)) if marks else 100

    items = list(part.flatten().notesAndRests)

    merged = _merge_ties(items)

    # The file's own marking first. Only a score that marks
    # every syllable "single" needs the trailing-space
    # reading, which is a printing convention rather than
    # the format's way of saying it.
    marked = any(
        lyric.syllabic in ("begin", "middle", "end")
        for note in part.flatten().notes
        for lyric in note.lyrics
    )

    ends_word = None if marked else _word_ends(path, index)

    verses = len({
        lyric.number
        for note in part.flatten().notes
        for lyric in note.lyrics
        if lyric.number
    })

    pitches = []
    durations = []
    syllables = []

    sung = 0

    for is_rest, length, item in merged:

        if length <= 0:
            continue

        if is_rest:

            for piece in _rests_as_bars(length, beats_per_bar):
                pitches.append(REST)
                durations.append(piece)

            continue

        # A chord in a sung part is written as its top
        # note: one line is what a voice can sing, and the
        # rest of the chord is in the other parts.
        number = max(pitch.midi for pitch in item.pitches)

        pitches.append(number)
        durations.append(length)

        word = _syllable(item, verse)

        if word:

            token = word

            # Where the file marks nothing - every syllable
            # "single" - the trailing space in the printed
            # text is the only hint of a word ending, and
            # that is read from the XML itself because
            # music21 strips it.
            if (
                not token.endswith("-")
                and ends_word is not None
                and sung < len(ends_word)
                and not ends_word[sung]
            ):
                token += "-"

            syllables.append(token)

        else:
            # A note inside a word being held. The file
            # gives it no syllable because the one before
            # is still sounding.
            syllables.append("_")

        sung += 1

    if not pitches:
        raise ValueError(
            "That part has no notes to import."
        )

    # Every voice sounding together, for the chart. All on
    # one clock by construction here: the score states the
    # divisions, so nothing has to be rescaled onto
    # anything else.
    polyphony = []

    for other in parts:

        for item in other.flatten().notes:

            start = float(item.offset)
            length = float(item.quarterLength)

            for pitch in item.pitches:
                polyphony.append((start, length, pitch.midi))

    total = sum(durations)

    # The same reading the MIDI importer does: a minor
    # piece is set to its relative major, because the key
    # box names a signature rather than a tonic.
    key = spelling_key([
        (0, float(length), number)
        for number, length in zip(pitches, durations)
        if number != REST
    ]) or "C"

    chart = ""

    if polyphony:
        chart = chart_from_notes(
            polyphony, float(total), beats_per_bar, key
        )

    pitch_text = " ".join(
        REST if number == REST else midi_to_note(number, key)
        for number in pitches
    )

    duration_text = " ".join(
        str(length) if length.denominator == 1
        else f"{length.numerator}/{length.denominator}"
        for length in durations
    )

    # Phrases, written as line breaks in the lyrics where
    # they can be corrected. A score does not say where a
    # singer breathes, so this is a guess like any other
    # and is demoted the same way: Enter and Backspace fix
    # it in a keystroke.
    #
    # One rule, deliberately: a rest of a beat or more ends
    # a phrase. A rule-based splitter with several kinds of
    # evidence was built for the MIDI path, tuned, and
    # reverted - every threshold that fixed one file broke
    # another. So this is not tuned. It will be wrong on
    # some scores, and the wrongness costs a keystroke.
    #
    # Pasting the words is the better answer where they are
    # to hand: a lyric sheet's line breaks are a human's
    # idea of where the phrases fall, and the paste applies
    # them.
    lyric_text = " ".join(syllables)

    breaks = set()

    spoken = 0

    for is_rest, length, item in merged:

        if is_rest:

            if length >= PHRASE_REST and spoken:
                breaks.add(spoken)

            continue

        spoken += 1

    if breaks:

        lines = []
        last = 0

        for position in sorted(breaks):

            if position <= last:
                continue

            lines.append(" ".join(syllables[last:position]))
            last = position

        lines.append(" ".join(syllables[last:]))

        lyric_text = "\n".join(
            line for line in lines if line.strip()
        )

    feedback = (
        f"Read {sung} notes from "
        f"{part.partName or 'part ' + str(index + 1)}, "
        f"written in {metre.ratioString if metre else '4/4'}. "
        f"The lengths are the score's own, so nothing was "
        f"repaired or rounded to a grid. "
        f"This sounds like {key} major."
    )

    if syllables and any(token != "_" for token in syllables):

        if marked:
            feedback += (
                " Lyrics were found, with the words joined "
                "as the score marks them."
            )

        elif ends_word is not None:
            feedback += (
                " Lyrics were found, with the words joined "
                "from where they end in the printed text."
            )

        else:
            feedback += (
                " Lyrics were found, but the file does not "
                "say which syllables join into words, so "
                "each stands alone. Paste the words to "
                "correct them."
            )

        if verses > 1:
            feedback += (
                f" The score has {verses} verses; verse "
                f"{verse} was taken."
            )

    if chart:
        feedback += (
            " The chords were read from every voice "
            "sounding together, and can be edited."
        )

    return (
        pitch_text,
        duration_text,
        lyric_text,
        bpm,
        feedback,
        chart,
        polyphony,
        key
    )