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

from chord_detector import chart_from_notes, fill_gaps, write_chart
from harmony import format_key
from midi_import import spelling_key
from notes import NOTE_SEMITONES, REST, midi_to_note


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


# MusicXML's own vocabulary for a chord symbol's kind,
# mapped to the app's own quality tokens (chords.py's
# CHORD_QUALITIES). Covers every quality the app can
# represent; a kind not listed here has no exact match and
# falls back to its triad shape instead (see _printed_chart).
KIND_TO_QUALITY = {
    "major": "",
    "minor": "m",
    "dominant": "7",
    "dominant-seventh": "7",
    "minor-seventh": "m7",
    "major-seventh": "maj7",
    "diminished": "dim",
    "augmented": "aug",
    "suspended-second": "sus2",
    "suspended-fourth": "sus4",
    "major-sixth": "6",
    "minor-sixth": "m6",
}

# When a printed chord's own kind has no exact match above
# - a ninth, an altered chord, a half-diminished seventh -
# music21 still classifies its underlying triad. Falling
# back to that triad is the same move invariant 12 makes
# for a detected chart: the chart holds one name because it
# must parse and play, and a plainer name that plays is
# worth more here than an exact one that doesn't fit the
# app's vocabulary. "other" (a chord with no clear triad,
# such as a bare suspension) has nothing to fall back to
# and is dropped rather than guessed.
QUALITY_FALLBACK = {
    "major": "",
    "minor": "m",
    "diminished": "dim",
    "augmented": "aug",
}


def _sung(notes):
    """
    A stream's notes, without the chord symbols hiding
    among them.

    music21 models a printed chord symbol as a kind of
    chord, so it passes every "just the notes" filter a
    real, played chord passes too. Left in, a symbol
    printed above the staff becomes a phantom note in the
    melody, or phantom polyphony in the chart - wrong in a
    way nothing here would notice, because it looks exactly
    like a very quiet chord.
    """

    from music21 import harmony

    return [
        item for item in notes
        if not isinstance(item, harmony.ChordSymbol)
    ]


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

        notes = _sung(part.flatten().notes)

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


def _printed_chart(parts, total_beats, beats_per_bar):
    """
    The chart as the score itself states it, read from
    every chord symbol in the file - not detected from
    polyphony, because a score that already prints its
    harmony has said what it is. Invariant 5: this is
    reading, not suggesting, and a human's own printed
    symbol is stronger evidence than anything derived from
    the notes.

    Read across every part rather than the chosen singing
    part: a chord symbol is written once for the system,
    not per voice, so the part carrying the tune is not
    necessarily the part carrying the symbols. Where a file
    duplicates the same symbols onto every staff (a
    grand-staff piano part often does), duplicates at the
    same beat are read once.

    Takes flattened parts, not score.recurse(): a symbol's
    own .offset resets to zero at every measure, and only
    flattening turns that into one running count from the
    start of the piece - the same reason the polyphony
    reading below flattens each part before reading offsets
    from it. Reading offsets straight from recurse() looked
    plausible on the first bar and wrong on every bar after
    it, since every measure's symbols collided into the
    first few beats.

    Returns "" if the file has no chord symbols, or if
    every one it has falls outside what a chart here can
    represent - the caller falls back to detection exactly
    as it would for a file with no symbols at all.
    """

    from music21 import harmony

    symbols = sorted(
        (
            symbol
            for part in parts
            for symbol in part.flatten().getElementsByClass(
                harmony.ChordSymbol
            )
        ),
        key=lambda symbol: symbol.offset
    )

    by_beat = {}

    for symbol in symbols:

        root = symbol.root()

        # music21 parses a printed "N.C." (no chord) mark as
        # a ChordSymbol with kind "none" and no root pitch at
        # all - real notation, not a malformed file. Skipped
        # like any other symbol this chart can't represent
        # (see the quality checks below): the beat is left as
        # a gap for fill_gaps to carry the surrounding chord
        # through, the same as a beat with no symbol printed.
        if root is None:
            continue

        root_name = root.name.replace("-", "b")

        if root_name not in NOTE_SEMITONES:
            continue

        quality = KIND_TO_QUALITY.get(symbol.chordKind)

        if quality is None:
            quality = QUALITY_FALLBACK.get(symbol.quality)

        if quality is None:
            continue

        # A chart here can keep a symbol's timing down to
        # the half beat - an eighth-note pickup arriving on
        # the "and" of a beat, the syncopated-strum case a
        # real lead sheet marks - but no finer. A symbol
        # landing exactly on a half keeps that precision;
        # anything else still gives up its timing and floors
        # to the beat it starts within. Not rounded to the
        # nearest one: rounding can push a symbol a whole
        # beat late (Python rounds a half beat to even, so
        # 3.5 becomes 4, not 3) - that same 3.5 is exactly
        # the position now worth keeping as 3.5, which is
        # why this checks for a genuine half explicitly
        # rather than calling round().
        floor_beat = int(symbol.offset)
        fraction = symbol.offset - floor_beat

        if abs(fraction - 0.5) < 1e-6:
            beat = floor_beat + 0.5

        else:
            beat = float(floor_beat)

        by_beat[beat] = root_name + quality

    if not by_beat:
        return ""

    positions = sorted(by_beat)

    # A score sometimes reprints the chord already sounding
    # - a courtesy symbol at a new line or section, not a
    # real change. Left as two separate entries, each got
    # its own onset in playback: the chord struck once on
    # its true arrival, then struck again moments later for
    # no musical reason (BUILDNOTES.md, the syncopation
    # session - real evidence against a real recording, not
    # a guess). A reprint carries no new information the
    # first symbol did not already state, so it is dropped
    # here rather than kept as a second, silent-seeming
    # "change" that still ends up sounding.
    kept = [positions[0]]

    for beat in positions[1:]:
        if by_beat[beat] != by_beat[kept[-1]]:
            kept.append(beat)

    chords = [(beat, 0.0, by_beat[beat]) for beat in kept]

    return write_chart(
        fill_gaps(chords, total_beats), total_beats, beats_per_bar
    )


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
        if _sung(part.flatten().notes)
    ]

    if not parts:
        return []

    part = parts[min(part_number_from(part_label), len(parts) - 1)]

    numbers = set()

    for item in _sung(part.flatten().notes):
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


def _stated_key(score):
    """
    The key, read from the score's own signature.

    A signature only says how many flats or sharps - the
    same count belongs to a major key and its relative
    minor, so this cannot say which the piece actually
    resolves to. It does not need to: the key box holds a
    signature, not a tonic-with-mode, and asKey("major")
    hands back the one spelling that count has always meant.

    None when the score carries no signature to read - a
    rare score, or a bare part MusicXML did not attach one
    to - so the caller falls back to guessing from the notes.
    """

    signatures = list(
        score.recurse().getElementsByClass("KeySignature")
    )

    if not signatures:
        return None

    tonic = signatures[0].asKey("major").tonic.name

    # music21 spells a flat with a dash; the rest of this
    # app spells it with a b.
    return tonic.replace("-", "b")


def _key_signatures(all_parts, part):
    """
    Every key the score states, in beat order.

    Read across every part that shares the selected part's
    own transposition, not just the selected part alone: a
    modulation is sometimes restated on an accompaniment
    part's engraving without being reprinted on the vocal
    line's own staff, which would otherwise carry on with no
    signature to read at all. A part whose transposition
    differs from the selected part's (a Bb trumpet against a
    concert-pitch voice, say) is excluded outright - its
    signature is written in its own transposed pitch space,
    and borrowing it to spell a different part's notes would
    spell them wrong on purpose, not by accident. Where two
    compatible parts disagree at the same beat, the selected
    part's own value wins: these are its own notes being
    spelled, and another part is only consulted for a beat
    the selected part is silent about.

    Read from each part's own flattened stream rather than
    score.recurse(): a signature's own .offset resets to zero
    at every measure, the same trap _printed_chart's own
    docstring warns about for chord symbols, and only
    flattening turns that into one running count from the
    start of the piece.

    Returns a list of (beat, key_name) pairs, sorted, empty
    if no compatible part carries a signature at all. The
    first pair's beat is not necessarily 0.0 - a pickup bar
    before the first full bar is real - so a caller wanting
    "the key in force at beat B" should take the last entry
    whose beat is at or before B, not assume the list opens
    at zero.
    """

    def transposition_of(a_part):

        instrument = a_part.getInstrument()

        return instrument.transposition if instrument else None

    own_transposition = transposition_of(part)

    by_beat = {}

    # Other compatible parts first, so the selected part's
    # own values - read second, below - can overwrite them
    # where both state something at the same beat.
    for other in all_parts:

        if other is part:
            continue

        if transposition_of(other) != own_transposition:
            continue

        for signature in other.flatten().getElementsByClass(
            "KeySignature"
        ):
            by_beat[float(signature.offset)] = (
                signature.asKey("major").tonic.name
                .replace("-", "b")
            )

    for signature in part.flatten().getElementsByClass(
        "KeySignature"
    ):
        by_beat[float(signature.offset)] = (
            signature.asKey("major").tonic.name.replace("-", "b")
        )

    return sorted(by_beat.items())


def _key_at(beat, signatures, opening_key):
    """
    Which key is in force at a given beat.

    Walks the score's own list of changes rather than
    assuming one key throughout - a modulating piece spells
    its second half in the second key's dialect, not the
    first's. Falls back to the opening key (however it was
    found - stated or guessed) when the part carries no
    signature that has arrived yet, which is every beat of a
    single-key piece: this changes nothing for the common
    case, only for one that genuinely modulates.
    """

    key = opening_key

    for signature_beat, signature_key in signatures:

        if signature_beat > beat:
            break

        key = signature_key

    return key


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
        if _sung(part.flatten().notes)
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

    # The tempo, if the score carries one. A mark can be
    # words alone - "Moderately", with no number - and a
    # wordy mark says nothing a BPM box can hold.
    marks = [
        mark for mark in score.recurse().getElementsByClass(
            "MetronomeMark"
        )
        if mark.number is not None
    ]

    bpm = int(round(marks[0].number)) if marks else 100

    items = _sung(part.flatten().notesAndRests)

    merged = _merge_ties(items)

    # The file's own marking first. Only a score that marks
    # every syllable "single" needs the trailing-space
    # reading, which is a printing convention rather than
    # the format's way of saying it.
    marked = any(
        lyric.syllabic in ("begin", "middle", "end")
        for note in _sung(part.flatten().notes)
        for lyric in note.lyrics
    )

    ends_word = None if marked else _word_ends(path, index)

    verses = len({
        lyric.number
        for note in _sung(part.flatten().notes)
        for lyric in note.lyrics
        if lyric.number
    })

    pitches = []
    durations = []
    pitch_beats = []
    syllables = []

    sung = 0
    position = 0.0

    for is_rest, length, item in merged:

        if length <= 0:
            continue

        if is_rest:

            for piece in _rests_as_bars(length, beats_per_bar):
                pitches.append(REST)
                durations.append(piece)
                pitch_beats.append(position)
                position += float(piece)

            continue

        # A chord in a sung part is written as its top
        # note: one line is what a voice can sing, and the
        # rest of the chord is in the other parts.
        number = max(pitch.midi for pitch in item.pitches)

        pitches.append(number)
        durations.append(length)
        pitch_beats.append(position)
        position += float(length)

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

        for item in _sung(other.flatten().notes):

            start = float(item.offset)
            length = float(item.quarterLength)

            for pitch in item.pitches:
                polyphony.append((start, length, pitch.midi))

    total = sum(durations)

    # A key signature states a flat/sharp count, not a
    # tonic - four flats is A flat major or its relative,
    # F minor, and the file does not say which. But the key
    # box only ever names a signature, never a tonic with a
    # mode (the same reading the MIDI importer does: a minor
    # piece is set to its relative major) - so the count
    # alone already answers the only question the box asks,
    # with nothing left to guess. This is what the module's
    # own reason for existing says to do: the file already
    # states its key, the same as its lengths and its metre.
    #
    # Found on a real score: the note-based guess, with no
    # signature to check against, picked C minor - three
    # flats - for a piece whose own header states four. The
    # notes it was guessing from were real; the signature it
    # never looked at was the actual answer.
    key = _stated_key(score) or spelling_key([
        (0, float(length), number)
        for number, length in zip(pitches, durations)
        if number != REST
    ]) or "C"

    # Every key the score itself states, opening key first -
    # a piece with only one signature (or none) gets a list
    # of at most one entry, so _key_at falls straight back to
    # `key` for every note, unchanged from before. A piece
    # that genuinely modulates spells its notes in whichever
    # key was actually in force when each one sounds, rather
    # than the opening key's dialect for the whole piece -
    # the key box itself still only ever holds the opening
    # key (invariant 1's boxes stay single-valued until the
    # box itself learns to hold a timeline; see the design
    # note on multi-key support).
    key_signatures = _key_signatures(score.parts, part)

    chart = _printed_chart(parts, float(total), beats_per_bar)

    chart_source = "printed" if chart else None

    if not chart and polyphony:
        chart = chart_from_notes(
            polyphony, float(total), beats_per_bar, key
        )
        chart_source = "detected" if chart else None

    pitch_text = " ".join(
        REST if number == REST
        else midi_to_note(
            number, _key_at(beat, key_signatures, key)
        )
        for number, beat in zip(pitches, pitch_beats)
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

    if len(key_signatures) > 1:

        change_beat, change_key = key_signatures[1]

        change_bar = int(change_beat // beats_per_bar) + 1

        feedback += (
            f" The score changes key partway through, to "
            f"{change_key} major at bar {change_bar}. The "
            f"key box holds the opening key only, but pitches "
            f"after the change are already spelled correctly."
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

    if chart_source == "printed":
        feedback += (
            " The chords are the score's own printed "
            "symbols, and can be edited."
        )

    elif chart_source == "detected":
        feedback += (
            " The score prints no chord symbols, so the "
            "chords were read from every voice sounding "
            "together instead, and can be edited."
        )

    return (
        pitch_text,
        duration_text,
        lyric_text,
        bpm,
        feedback,
        chart,
        polyphony,
        format_key(key_signatures) if len(key_signatures) > 1
        else key
    )