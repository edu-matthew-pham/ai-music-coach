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

One of those corners deserves naming, because it was missed
for a long time: a score is printed once and played in the
order its repeats, endings, D.C. and D.S. dictate. The
import unfolds the score into playing order first (music21's
expander, on the whole score at once) and reads everything -
notes, words, chords, key changes - from that. Where the
markings are something the expander cannot make sense of,
the printed order is kept and the feedback says so, with the
bar past which the numbers stop matching a performance. It
was reading the printed order for months, and every beat
position after the first repeat was wrong by the length of
the repeated passage.

A second corner deserves the same naming: "several voices in
one staff" is not always one line doubled for engraving - in
a real file (Mulan's bridge) it was a second, differently-
worded vocal line, the men's chorus answering "Be a man"
under the main melody. Reading a part as one flattened
stream, the way a part with no voices is read, mixed both
lines' notes together in whatever order the flattening
produced - wrong durations, and notes from the wrong line
landing where the other line was actually holding one, for
everything after the first such measure. Each voice is now
read apart (music21's voicesToParts) and, where more than
one voice genuinely carries a lyric, offered as its own part
to choose - not silently merged, and not silently dropped.

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

# A syllable ending with one of these reads as the close
# of a sentence, the same way a line of print does.
SENTENCE_END = (".", "!", "?")


def _ends_sentence(word):
    """
    Whether a syllable's own text closes a sentence.

    Checked on the syllable itself - a closing word like
    "bye." is where the score actually prints the mark,
    trailing quotes and brackets aside.
    """

    return word.rstrip("'\")]").endswith(SENTENCE_END)


def _lyrics_read_as_prose(syllables):
    """
    Whether these lyrics use capitals and full stops the
    way ordinary prose does, rather than one flat case.

    Some engraved scores print every syllable in capitals
    - a typesetting convention, not a phrase marker.
    Reading "starts with a capital" against a score like
    that would fire on every single syllable and produce
    nonsense, so the words only count as usable evidence
    once the score is confirmed to use lower case at all.
    """

    words = [
        syllable for syllable in syllables
        if syllable not in (None, "", "_")
        and any(letter.isalpha() for letter in syllable)
    ]

    if not words:
        return False

    if not any(
        any(letter.islower() for letter in word)
        for word in words
    ):
        return False

    return (
        any(word[0].isupper() for word in words)
        or any(_ends_sentence(word) for word in words)
    )


def _is_bare_pronoun_i(word):
    """
    Whether this token is the pronoun "I" on its own, or
    one of its contractions.

    English capitalises this one word regardless of where
    it falls in a sentence, so its capital says nothing
    about a phrase beginning here the way every other
    capital does - checked directly against a real fixture
    (Mulan), where every wrong break the words-first rule
    produced traced to this one word.
    """

    core = word.rstrip("'\")]").rstrip("-")

    return core in ("I", "I'll", "I'm", "I've", "I'd")


def _lyric_phrase_breaks(syllables):
    """
    Where a phrase begins, read from the words themselves.

    A line of a song is usually printed the way a sentence
    is - a capital letter opens it, a full stop or a
    question mark closes it - and that is stronger
    evidence of where a phrase ends than a rest, which only
    says a singer paused there, not that the line did.
    Where the words carry that signal it is used as the
    phrasing; where they do not (no lyrics, or a score
    printed in one running case with no punctuation) this
    returns None, and the caller falls back to rests alone.

    Returns break positions in the same units as the
    rest-based rule: a count of spoken (non-rest) notes,
    which is also a direct index into `syllables`.
    """

    if not _lyrics_read_as_prose(syllables):
        return None

    breaks = set()
    last_word = None

    for position, syllable in enumerate(syllables):

        if syllable in (None, "", "_"):
            continue

        if position > 0:

            starts_capital = (
                syllable[0].isupper()
                and not _is_bare_pronoun_i(syllable)
            )

            follows_full_stop = (
                last_word is not None
                and _ends_sentence(last_word)
            )

            if starts_capital or follows_full_stop:
                breaks.add(position)

        last_word = syllable

    return breaks


# How long, in real singing seconds, a bare-capital break
# needs to hold up before it's trusted on its own.
#
# Seconds, not bars or notes: both of those were tried
# first and both failed on this app's own real fixtures,
# for the same underlying reason - a slow hymn's real
# phrases and a fast song's real phrases occupy different
# numbers of bars and notes for the same actual singing
# time, so a threshold in either unit that suits one tempo
# wrongly eats real short phrases at another. Measured
# directly in seconds, O Holy Night's genuine short lines
# ("Christ was born" 3.4s, "Sa- viour's birth" 2.6s, "See
# right through me." 1.3s, "Sur- vive." 1.6s) sit clearly
# above Mulan's and O Holy Night's own real false positives
# ("Huns." 0.8s, "O" 0.9s, "Ho- ly" 0.9s) - a real gap, not
# a razor's edge, checked against both files at once.
#
# Only applied to a bare-capital break. A break the words
# themselves close with a full stop is never second-guessed
# by length - that is the strong signal, and this filter
# exists only to catch the weak one leaning on it too hard.
MINIMUM_LYRIC_PHRASE_SECONDS = 1.0


def _previous_real_word(syllables, before):
    """
    The nearest real syllable before a position, skipping
    the held-note marker - a break can land right after a
    melisma, and the word that matters for punctuation is
    whichever one was actually spoken, not the notes
    silently continuing it.
    """

    for position in range(before - 1, -1, -1):

        if syllables[position] not in (None, "", "_"):
            return syllables[position]

    return None


def _drop_short_lyric_breaks(breaks, syllables, sung_spans, bpm):
    """
    Don't trust a bare-capital break that would open a very
    short phrase, measured in real singing time.

    Errs toward merging on purpose: a phrase folded in that
    should have stood alone costs one Enter to split back
    apart, at the exact point wanted. A phrase cut too
    early costs finding and removing the right line break
    among several short ones - editing is meant to be about
    placing the splits that are wanted, not undoing ones
    that weren't.
    """

    if not breaks or not sung_spans or not bpm:
        return breaks

    ordered = sorted(breaks)
    kept = set()

    for position, start in enumerate(ordered):

        previous_word = _previous_real_word(syllables, start)

        # Strong evidence - a real full stop - is never
        # second-guessed by how long the phrase runs.
        if previous_word is not None and _ends_sentence(previous_word):
            kept.add(start)
            continue

        end = (
            ordered[position + 1] if position + 1 < len(ordered)
            else len(sung_spans)
        )

        phrase_start = sung_spans[start][0]
        last_beat, last_length = sung_spans[end - 1]
        phrase_beats = last_beat + last_length - phrase_start

        seconds = phrase_beats / bpm * 60

        if seconds >= MINIMUM_LYRIC_PHRASE_SECONDS:
            kept.add(start)

    return kept

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


def _voice_parts(part):
    """
    A part's own voices, each as its own single line.

    A measure that splits into voices is real polyphony
    sharing one staff - Mulan's bridge is the real case that
    found this: the main melody continues in one voice while
    the men's chorus answers "Be a man" in a second voice
    underneath, both real, both sung. Reading the part as one
    flattened stream, the way a part with no voices is read,
    mixes both lines' notes and rests together in whatever
    order the flattening produces - wrong durations, and
    pitches from the wrong line landing where the other line
    was actually holding a note. Every note after the first
    such measure drifts, because the reading is a running
    position built by summing consecutive lengths, and that
    sum is wrong from the first mixed note on.

    `voicesToParts()` is music21's own tool for this: each
    voice becomes a genuine, independent part, correctly
    padded with rests for every bar it stays silent, using
    the score's own voice numbering - not anything read from
    lyrics or guessed. Lyrics decide only which voices are
    worth surfacing as something a person could choose to
    sing, once each voice is already read correctly: a part
    with no voice split anywhere is untouched, and a voice
    split where only one voice ever carries a lyric - a
    piano's two hands, say - collapses back to that one
    voice, exactly as if there had been no split to choose
    from at all.

    Returns a list of (part, extra) pairs, `extra` being None
    for a part needing no further description and a short
    phrase ("second voice") where more than one voice is
    genuinely offered.
    """

    if not any(
        measure.getElementsByClass("Voice")
        for measure in part.getElementsByClass("Measure")
    ):
        return [(part, None)]

    voices = list(part.voicesToParts().parts)

    lyric_voices = [
        voice for voice in voices
        if any(note.lyrics for note in _sung(voice.flatten().notes))
    ]

    if len(lyric_voices) <= 1:
        return [(lyric_voices[0] if lyric_voices else voices[0], None)]

    ordinals = ["first", "second", "third", "fourth", "fifth"]

    singles = [
        (
            voice,
            None if index == 0 else
            f"{ordinals[index] if index < len(ordinals) else index + 1} voice"
        )
        for index, voice in enumerate(lyric_voices)
    ]

    # The voices together, as one divided song - the second
    # half of what a two-voice staff needs. Splitting the
    # voices apart (above) only ever gave a choice between
    # them; this entry lands them side by side, the way the
    # hand-typed partner songs are. Its part slot is a list,
    # and every reader of this list branches on that.
    together = (
        lyric_voices,
        "both voices" if len(lyric_voices) == 2
        else f"all {len(lyric_voices)} voices"
    )

    return singles + [together]


def _is_combined(entry_part):
    """
    Whether a logical part's part slot is several parts to
    land together rather than one.
    """

    return isinstance(entry_part, list)


def _members(entry_part):
    """
    The parts behind a logical part - the one part itself,
    or every part of a combined entry.
    """

    return entry_part if _is_combined(entry_part) else [entry_part]


def _carries_words(part):
    """
    Whether any note of a part has a lyric at all - the test
    for "a part someone sings", as opposed to accompaniment.
    """

    return any(note.lyrics for note in _sung(part.flatten().notes))


def _logical_parts(score):
    """
    Every part a person could choose to import, in the order
    parts_in() describes them and import_musicxml selects
    from - the same list read the same way in both places, so
    a label parts_in() hands back always resolves to the same
    music.

    Ordinarily one entry per score part. A part with more
    than one genuinely sung voice contributes one entry per
    voice, then one for the voices together - see
    _voice_parts. And where more than one score part carries
    words, a last entry lands every sung part together, as
    one divided song: a partner song or a choir written on
    separate staves. Accompaniment (a staff with no words)
    stays out of it.

    Combined entries are always appended after the single
    ones, so every existing label and its index stay exactly
    where they were.
    """

    logical = []
    sung_staves = []
    staves_with_words = 0

    for part in score.parts:

        entries = _voice_parts(part)
        logical.extend(entries)

        if _carries_words(part):
            staves_with_words += 1
            sung_staves.extend(
                voice for voice, extra in entries
                if not _is_combined(voice)
            )

    # More than one staff, not more than one voice: a single
    # staff's voices together is already the entry above.
    if staves_with_words > 1:
        logical.append((sung_staves, "all sung parts"))

    return logical


def _tune_names(parts):
    """
    A name for each tune of a combined entry, for the
    "=== name ===" dividers.

    Voices of one staff have no name of their own beyond
    their order, so they are "Voice 1", "Voice 2" - the same
    convention the hand-typed round uses. Separate staves
    keep the score's own part names; a repeated name (two
    staves both called "Piano") is numbered so the dividers
    stay distinct, which Piece.read requires.
    """

    raw = [part.partName for part in parts]

    if len(set(raw)) == 1:
        return [f"Voice {index + 1}" for index in range(len(parts))]

    names = []
    seen = {}

    for name in raw:
        name = name or "Part"
        seen[name] = seen.get(name, 0) + 1
        names.append(
            name if raw.count(name) == 1 else f"{name} {seen[name]}"
        )

    return names


def parts_in(path):
    """
    The parts of a score, named as the score names them.

    No guessing from General MIDI programs: a MusicXML part
    carries the name the composer or engraver gave it, and
    a part with lyrics is a part someone sings.
    """

    return [label for label, _ in _described(_read(path))]


def default_part_in(path):
    """
    The part that lands when nothing has been chosen yet.

    The most inclusive one: every sung staff together when
    the score has several, a staff's voices together when
    one staff carries two, the first part otherwise. The
    built-in partner songs and rounds open with all their
    tunes loaded and let the singer pick theirs in the
    mixer; an imported score should arrive the same way,
    so "which part" is a question about who is singing,
    not about what got read.
    """

    described = _described(_read(path))

    if not described:
        return None

    combined = [label for label, together in described if together]

    return combined[-1] if combined else described[0][0]


def _described(score):
    """
    Every part worth listing, as (label, combined) pairs.

    Shared by parts_in and default_part_in so the two can
    never disagree about what is on offer. Combined entries
    are listed after the parts they combine, and every sung
    staff together comes last, so the last combined entry
    is always the most inclusive.
    """

    described = []

    for index, (part, extra) in enumerate(_logical_parts(score)):

        notes = [
            note
            for member in _members(part)
            for note in _sung(member.flatten().notes)
        ]

        if not notes:
            continue

        sung = len([note for note in notes if note.lyric])

        if _is_combined(part) and extra == "all sung parts":
            name = "All sung parts"

        else:
            name = _members(part)[0].partName or f"Part {index + 1}"

            if extra:
                name += f", {extra}"

        label = f"{index}  {name}, {len(notes)} notes"

        if sung:
            label += f", {sung} with words"

        described.append((label, _is_combined(part)))

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


def _rests_as_bars(length, beats_per_bar):
    """
    A long silence as bars of rest.
    """

    pieces = []

    # Kept as a Fraction throughout: the metre arrives as a
    # float, and subtracting that from a Fraction silently
    # turns the remainder into a float the boxes cannot
    # write. Never bitten before a part first entered
    # partway through a bar after a long silence.
    bar = Fraction(beats_per_bar)

    remaining = length

    while remaining > bar:
        pieces.append(bar)
        remaining -= bar

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
        part for part, extra in _logical_parts(score)
        if any(
            _sung(member.flatten().notes)
            for member in _members(part)
        )
    ]

    if not parts:
        return []

    part = parts[min(part_number_from(part_label), len(parts) - 1)]

    numbers = set()

    for member in _members(part):
        for item in _sung(member.flatten().notes):
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

    # A signature restating the key already in force is not a
    # change - a courtesy signature at a section start, or,
    # once the score is unfolded, the signature at a D.S.
    # target seen a second time - so consecutive repeats of
    # the same key are dropped. _key_at reads the last entry
    # at or before a beat, so this changes nothing it returns;
    # it only keeps "the score changes key" honest.
    signatures = []

    for beat, name in sorted(by_beat.items()):
        if signatures and signatures[-1][1] == name:
            continue
        signatures.append((beat, name))

    return signatures


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


def _structure(score):
    """
    What the score says about its own shape, counted before
    anything is unfolded: repeat barlines, ending brackets,
    and every navigation mark (D.C., D.S., Fine, Coda, Segno
    and their combinations).

    Counted here rather than trusted to the expander, because
    the expander has two ways of not doing what the marks say
    - refusing outright, and quietly unfolding the repeats
    while dropping a D.C. it could not place - and the import
    feedback has to be able to name both. Returns a dict of
    name -> count and the beat length of the longest part.
    """

    from music21 import bar, repeat, spanner

    # Marks are printed on every staff, so one part is
    # counted - the first - not the whole score, or a quartet
    # reports four times the repeats it has. Whether every
    # part really carries the same marks is not checked here;
    # if they differ, the expander (which runs per part) can
    # bring parts back at different lengths, and that shows
    # up in the beat count, not in this tally.
    counted = score.parts[0] if score.parts else score

    flat = counted.flatten()

    counts = {}

    repeats = len(flat.getElementsByClass(bar.Repeat))
    if repeats:
        counts["repeat"] = repeats

    endings = len(
        counted.recurse().getElementsByClass(spanner.RepeatBracket)
    )
    if endings:
        counts["ending"] = endings

    # Navigation words are different: usually printed once,
    # above the top staff or on whichever part the engraver
    # chose, so they are looked for on every part. Only their
    # presence matters downstream, not the tally.
    for mark in score.flatten().getElementsByClass(
        repeat.RepeatExpression
    ):
        name = mark.__class__.__name__
        counts[name] = counts.get(name, 0) + 1

    beats = max(
        (float(part.duration.quarterLength) for part in score.parts),
        default=float(score.duration.quarterLength),
    )

    return counts, beats


# Human names for music21's navigation classes, for the
# feedback sentence. Segno and Coda on their own are signs
# to jump to, not instructions to jump, so they are not
# named - a score with a D.S. always has a segno too, and
# naming both says the same thing twice.
NAVIGATION_NAMES = {
    "DaCapo": "D.C.",
    "DaCapoAlFine": "D.C. al Fine",
    "DaCapoAlCoda": "D.C. al Coda",
    "DalSegno": "D.S.",
    "DalSegnoAlFine": "D.S. al Fine",
    "DalSegnoAlCoda": "D.S. al Coda",
    "AlSegno": "al Segno",
    "Fine": None,
    "Segno": None,
    "Coda": None,
}


def _describe_structure(counts):
    """
    "1 repeat with two endings, D.S. al Fine" - the marks
    that mean something to a player, in a phrase.
    """

    words = []

    repeats = counts.get("repeat", 0)
    endings = counts.get("ending", 0)

    if repeats:
        # A repeat is a pair of barlines; a lone backward
        # repeat (back to the start) counts as one.
        pairs = max(1, (repeats + 1) // 2)
        words.append(
            f"{pairs} repeat{'s' if pairs != 1 else ''}"
            + (
                f" with {endings} ending"
                + ("s" if endings != 1 else "")
                if endings else ""
            )
        )

    for name, shown in NAVIGATION_NAMES.items():
        if shown and counts.get(name):
            words.append(shown)

    return ", ".join(words)


def _has_navigation(counts):
    return any(
        counts.get(name)
        for name, shown in NAVIGATION_NAMES.items()
        if shown
    )


def _first_marked_bar(score):
    """
    The bar number of the first repeat barline or navigation
    mark - the point past which, if nothing was unfolded, the
    bar numbers stop matching a performance.
    """

    from music21 import bar, repeat

    earliest = None

    for element in score.recurse().getElementsByClass(
        (bar.Repeat, repeat.RepeatExpression)
    ):
        measure = element.getContextByClass("Measure")
        if measure is None or measure.number is None:
            continue
        if earliest is None or measure.number < earliest:
            earliest = measure.number

    return earliest


def _unfold(score):
    """
    The score as it is played, not as it is printed.

    music21's expander unfolds repeats, endings, D.C. and D.S.
    on the whole Score at once - the whole score, not each
    part, so parts cannot come back different lengths through
    disagreeing markup. Where the markup is something it
    cannot make sense of (an unclosed ending bracket, two
    D.C.s, an "al Coda" with no coda to go to) it raises, and
    the printed order is kept instead - one time through, and
    the feedback says so.

    Returns (score, unfolded), where unfolded is True when the
    expander ran and changed something, False when there was
    nothing to unfold, and None when it refused.
    """

    from music21.repeat import ExpanderException

    try:
        expanded = score.expandRepeats()
    except ExpanderException:
        return score, None

    if expanded is None:
        return score, False

    return expanded, True


def _stamp_word_ends(score, path):
    """
    Where each syllable ends a word, read from the file's own
    text and written onto the syllable itself before anything
    is unfolded.

    MusicXML can mark this properly - begin, middle, end,
    single - but files often mark every syllable "single" and
    rely on a trailing space in the text, which is how a
    printed score is typed. music21 strips that space, so it
    is read here from the XML directly and stamped on each
    Lyric's editorial, where the expander's copy carries it
    to every place the syllable is sung. Reading it by
    position in the raw XML, as was done before, went wrong
    as soon as a note was sung twice.

    Silent where the file does not use the convention: a
    lyric with no stamp is treated as ending its word, which
    is wrong but visibly wrong.
    """

    try:

        if zipfile.is_zipfile(path):

            with zipfile.ZipFile(path) as archive:

                names = [
                    item for item in archive.namelist()
                    if item.endswith(".xml")
                    and not item.startswith("META-INF")
                ]

                if not names:
                    return False

                xml = archive.read(names[0]).decode("utf-8", "ignore")

        else:
            xml = open(path, encoding="utf-8", errors="ignore").read()

    except (OSError, zipfile.BadZipFile):
        return False

    bodies = re.findall(r"<part id=[^>]*>(.*?)</part>", xml, re.S)

    stamped = False

    for body, part in zip(bodies, score.parts):

        texts = re.findall(
            r"<lyric[^>]*>.*?<text[^>]*>(.*?)</text>",
            body,
            re.S
        )

        ends = [text != text.rstrip() for text in texts]

        if not any(ends):
            continue

        lyrics = [
            lyric
            for item in part.flatten().notes
            for lyric in item.lyrics
        ]

        # The XML and the parsed score list the same
        # syllables in the same order - checked on real
        # files - but a file that defeats the regex is not
        # worth guessing at.
        if len(lyrics) != len(ends):
            continue

        for lyric, end in zip(lyrics, ends):
            lyric.editorial.endsWord = end

        stamped = True

    return stamped


def _chosen_lyric(item, verse):
    """
    The lyric sung on a note in the chosen verse - the one
    _syllable reads its text from.
    """

    for lyric in item.lyrics:

        if lyric.number and lyric.number != verse:
            continue

        if not (lyric.text or "").strip():
            continue

        return lyric

    return None


def _verse_for(part, verse):
    """
    Which verse to read from a part: the one asked for,
    unless most of this part's words are in another.

    A second voice on a staff often carries its words under
    a different verse number from the main line - in a real
    file (Mulan's bridge) the chorus's "Be a man" sits in
    verse 2 while the melody's words sit in verse 1, so
    reading every voice at verse 1 would land the chorus as
    a line of held-note marks and nothing else. The feedback
    names the verse taken wherever it differs from the one
    asked for, so the inference is visible.
    """

    words = {}

    for note in _sung(part.flatten().notes):
        for lyric in note.lyrics:
            if lyric.number and (lyric.text or "").strip():
                words[lyric.number] = words.get(lyric.number, 0) + 1

    if not words:
        return verse

    # The verse most of this part's words are in; the one
    # asked for wins a tie. "Any words at all" was tried
    # first and picked verse 1 for Mulan's chorus on the
    # strength of a single stray syllable.
    best = max(words.values())

    if words.get(verse, 0) == best:
        return verse

    return min(number for number, count in words.items() if count == best)


def _read_voice(part, beats_per_bar, verse, positioned):
    """
    One part's notes, lengths and syllables, as the boxes
    hold them.

    `positioned` says whether a note lands where the score
    places it (rests written for every gap and for the
    silence before its first note) or simply after the note
    before it. A part imported to sing on its own needs only
    the second - and it is how every single-part import has
    always read, so it stays that way. Parts landed together
    need the first, or a voice that first enters at bar 12
    would start singing at bar 1: checked on a real file,
    where music21's voice splitting hands back only the bars
    a voice actually sounds in, with the silences between
    them missing rather than written as rests.

    Returns a dict; the loop that fills it is the same loop
    the single-part import has always run.
    """

    items = _sung(part.flatten().notesAndRests)

    merged = _merge_ties(items)

    if positioned:

        placed = []
        position = 0.0

        for is_rest, length, item in merged:

            start = float(item.offset)

            # A gap is written as its own rest, never folded
            # into a neighbouring one: the part's own rests
            # keep exactly the tokens they have when the part
            # is imported alone, so a tune reads the same
            # whether it lands by itself or beside others.
            if start > position + 1e-6:
                placed.append([True, _round(start - position), None])

            placed.append([is_rest, length, item])

            position = start + float(length)

        merged = placed

    # The file's own marking first. Only a score that marks
    # every syllable "single" needs the trailing-space
    # reading, which is a printing convention rather than
    # the format's way of saying it.
    marked = any(
        lyric.syllabic in ("begin", "middle", "end")
        for note in _sung(part.flatten().notes)
        for lyric in note.lyrics
    )

    # Whether the file used trailing spaces at all: if no
    # syllable in this part carries a stamp, nothing can be
    # read from it and each syllable stands alone.
    stamped = not marked and any(
        getattr(lyric.editorial, "endsWord", None) is not None
        for note in _sung(part.flatten().notes)
        for lyric in note.lyrics
    )

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
    sung_spans = []

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
        sung_spans.append((position, float(length)))
        position += float(length)

        word = _syllable(item, verse)

        if word:

            token = word

            # Where the file marks nothing - every syllable
            # "single" - the trailing space in the printed
            # text is the only hint of a word ending. It was
            # stamped on the syllable itself before the score
            # was unfolded, so a note sung twice reads the
            # same both times.
            if not token.endswith("-") and stamped:

                lyric = _chosen_lyric(item, verse)

                if (
                    lyric is not None
                    and getattr(lyric.editorial, "endsWord", None)
                    is False
                ):
                    token += "-"

            syllables.append(token)

        else:
            # A note inside a word being held. The file
            # gives it no syllable because the one before
            # is still sounding.
            syllables.append("_")

        sung += 1

    return {
        "pitches": pitches,
        "durations": durations,
        "pitch_beats": pitch_beats,
        "syllables": syllables,
        "sung_spans": sung_spans,
        "sung": sung,
        "merged": merged,
        "marked": marked,
        "stamped": stamped,
        "verses": verses,
    }


def _pad_to(read, total, beats_per_bar):
    """
    Trailing bars of rest on a tune, so it ends where the
    longest tune does.
    """

    short = total - sum(read["durations"])

    if short <= 0:
        return

    position = sum(float(length) for length in read["durations"])

    for piece in _rests_as_bars(Fraction(short), beats_per_bar):
        read["pitches"].append(REST)
        read["durations"].append(piece)
        read["pitch_beats"].append(position)
        position += float(piece)


def _lyric_lines(read, bpm):
    """
    One voice's syllables as lyric text, with phrase breaks
    written as line breaks where they can be corrected.

    A score does not say where a singer breathes, so this is
    a guess like any other and is demoted the same way:
    Enter and Backspace fix it in a keystroke.

    The words themselves are the primary evidence, when
    they carry it: a line of print usually opens with a
    capital and closes with a full stop, and that says
    where a phrase falls more reliably than a rest does -
    a rest only says a singer paused, not that the line
    ended, which is why a run of short breaths inside one
    sentence (a real score in this app's own fixtures)
    used to be cut into three lines instead of one, and a
    long unbroken sentence with rests only at its very end
    (another real fixture) used to arrive as one crowded
    line holding several sentences at once.

    A rule-based splitter combining several kinds of
    evidence by score was tried once, for the MIDI path,
    tuned, and reverted - every threshold that fixed one
    file broke another. This does not repeat that: the
    words are used alone, only where they are confirmed
    usable, and the rest-rule below is the fallback for
    everything else, not a second vote combined with it.
    """

    syllables = read["syllables"]

    lyric_text = " ".join(syllables)

    breaks = _lyric_phrase_breaks(syllables)

    if breaks is None:

        # One rule, deliberately, same as before: a rest of
        # a beat or more ends a phrase. Used only when the
        # words themselves gave no usable signal - no
        # lyrics, or a score printed in one running case
        # with no punctuation.
        breaks = set()

        spoken = 0

        for is_rest, length, item in read["merged"]:

            if is_rest:

                if length >= PHRASE_REST and spoken:
                    breaks.add(spoken)

                continue

            spoken += 1

    else:

        # Only the words' own weaker signal (a bare capital,
        # with no full stop backing it) gets second-guessed
        # here - see _drop_short_lyric_breaks for why seconds
        # rather than bars or notes.
        breaks = _drop_short_lyric_breaks(
            breaks, syllables, read["sung_spans"], bpm
        )

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

    return lyric_text


def import_musicxml(path, part_label=None, verse=1):
    """
    A score into the boxes.

    Returns the same eight things the MIDI importer does,
    so the two are interchangeable to everything above:
    pitches, durations, lyrics, tempo, feedback, chart,
    the polyphony behind the chart, and the key.

    A combined entry from parts_in() (a staff's voices
    together, or every sung staff together) lands as one
    divided song: each box holds every tune in turn, under
    "=== name ===" divider lines, exactly the shape the
    hand-typed partner songs and rounds are written in, so
    Piece.read takes it without knowing where it came from.
    """

    score = _read(path)

    # What the printed score says about its shape, and the
    # word ends the file writes as trailing spaces - both
    # read from the raw score, before it is unfolded, because
    # both are printed once and played many times.
    printed_marks, printed_beats = _structure(score)

    _stamp_word_ends(score, path)

    score, unfolded = _unfold(score)

    left, played_beats = _structure(score)

    # A D.C. or D.S. the expander honoured is consumed by the
    # unfolding; one it could not place is left in the score
    # untouched, with no error - checked on real files both
    # ways. So whatever navigation is still there afterwards
    # was dropped, and the feedback names it.
    dropped = _has_navigation(left)

    first_bar = (
        _first_marked_bar(score)
        if unfolded is None or dropped else None
    )

    index = part_number_from(part_label)

    # Two different lists, on purpose. Choosing which part to
    # sing needs voices split apart - Mulan's bridge is real
    # polyphony sharing one staff, and reading it as one part
    # garbles it (see _voice_parts). Reading the chart and the
    # polyphony behind it needs the opposite: every voice
    # sounding together is exactly what a chord chart and a
    # second opinion are made from, and both already read each
    # note's own true offset rather than assuming one voice at
    # a time, so splitting would only risk losing a chord
    # symbol some file happens to print inside a Voice.
    singing_parts = [
        part for part, extra in _logical_parts(score)
        if any(
            _sung(member.flatten().notes)
            for member in _members(part)
        )
    ]

    parts = [
        part for part in score.parts
        if _sung(part.flatten().notes)
    ]

    if not singing_parts:
        raise ValueError(
            "This score has no notes in any part."
        )

    index = min(index, len(singing_parts) - 1)

    part = singing_parts[index]

    combined = _is_combined(part)

    members = _members(part)

    # The part everything score-wide is read against: the
    # metre, the key signatures. For a combined entry that is
    # its first tune - every tune shares one metre and one
    # key timeline by design, the same as the hand-typed
    # examples, and checked to agree on the real files.
    lead = members[0]

    # The metre, as stated rather than inferred - and read
    # from the library rather than worked out from the
    # numerator. Six eight is six eighth notes, which is
    # three beats, not six: taking the numerator drew every
    # bar line at twice its width, and only in compound
    # time, where four four hid it.
    signatures = list(
        lead.recurse().getElementsByClass("TimeSignature")
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

    # Each tune read on its own. A single part reads exactly
    # as it always has: one tune, placed after itself, the
    # verse asked for. Combined tunes are placed where the
    # score puts them, and each takes the verse its own words
    # are in.
    verses_taken = [
        _verse_for(member, verse) if combined else verse
        for member in members
    ]

    reads = [
        _read_voice(member, beats_per_bar, taken, positioned=combined)
        for member, taken in zip(members, verses_taken)
    ]

    if not any(read["pitches"] for read in reads):
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

    # Every tune runs to the longest one's end, padded with
    # bars of rest - the shape the hand-typed round is
    # written in, and what Piece.read requires, since one
    # shared chart has to cover each tune exactly. A single
    # part is its own longest tune and is left untouched.
    total = max(sum(read["durations"]) for read in reads)

    if combined:
        for read in reads:
            _pad_to(read, total, beats_per_bar)

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
        for read in reads
        for number, length in zip(read["pitches"], read["durations"])
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
    key_signatures = _key_signatures(score.parts, lead)

    chart = _printed_chart(parts, float(total), beats_per_bar)

    chart_source = "printed" if chart else None

    if not chart and polyphony:
        chart = chart_from_notes(
            polyphony, float(total), beats_per_bar, key
        )
        chart_source = "detected" if chart else None

    def pitch_text_of(read):
        return " ".join(
            REST if number == REST
            else midi_to_note(
                number, _key_at(beat, key_signatures, key)
            )
            for number, beat in zip(read["pitches"], read["pitch_beats"])
        )

    def duration_text_of(read):
        return " ".join(
            str(length) if length.denominator == 1
            else f"{length.numerator}/{length.denominator}"
            for length in read["durations"]
        )

    if not combined:

        read = reads[0]

        pitch_text = pitch_text_of(read)
        duration_text = duration_text_of(read)
        lyric_text = _lyric_lines(read, bpm)

        feedback = (
            f"Read {read['sung']} notes from "
            f"{lead.partName or 'part ' + str(index + 1)}, "
            f"written in {metre.ratioString if metre else '4/4'}. "
        )

    else:

        names = _tune_names(members)

        def divided(texts):
            return "\n".join(
                f"=== {name} ===\n{text}"
                for name, text in zip(names, texts)
            )

        pitch_text = divided(pitch_text_of(read) for read in reads)
        duration_text = divided(duration_text_of(read) for read in reads)
        lyric_text = divided(_lyric_lines(read, bpm) for read in reads)

        counted = ", ".join(
            f"{read['sung']} from {name}"
            for name, read in zip(names, reads)
        )

        feedback = (
            f"Read {len(reads)} parts together: {counted}, "
            f"written in {metre.ratioString if metre else '4/4'}. "
        )

        took = [
            f"{name} (verse {taken})"
            for name, taken in zip(names, verses_taken)
            if taken != verse
        ]

        if took:
            feedback += (
                f"Words for {', '.join(took)} were taken from "
                f"a different verse from the one asked for, "
                f"since that is where that part's words are. "
            )

    feedback += (
        f"The lengths are the score's own, so nothing was "
        f"repaired or rounded to a grid. "
        f"This sounds like {key} major."
    )

    # What was done about repeats, in one of three shapes:
    # nothing to say, unfolded, or refused. A score with no
    # repeat marks gets no sentence at all.
    where = f" after bar {first_bar}" if first_bar else ""

    if unfolded is None:

        feedback += (
            f" The score has repeat markings"
            f" ({_describe_structure(printed_marks)}) that could not"
            f" be unfolded, so it was imported as printed,"
            f" once through. Bar numbers{where} may not match"
            f" a performance."
        )

    elif unfolded and played_beats != printed_beats:

        feedback += (
            f" Repeats unfolded ({_describe_structure(printed_marks)}):"
            f" {printed_beats:g} beats printed,"
            f" {played_beats:g} played."
        )

        if dropped:
            feedback += (
                f" The {_describe_structure(left)} could not"
                f" be placed and was left as printed, so bar"
                f" numbers{where} may not match a performance."
            )

    elif dropped:

        feedback += (
            f" The score has {_describe_structure(printed_marks)}"
            f" that could not be unfolded, so it was imported"
            f" as printed, once through. Bar numbers{where}"
            f" may not match a performance."
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

    # The lyric sentences describe the lead tune - for a
    # single part, the only one; for a combined entry, its
    # first, which is as much as one sentence can say.
    lead_read = reads[0]

    syllables = lead_read["syllables"]

    if syllables and any(token != "_" for token in syllables):

        if lead_read["marked"]:
            feedback += (
                " Lyrics were found, with the words joined "
                "as the score marks them."
            )

        elif lead_read["stamped"]:
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

        if lead_read["verses"] > 1 and not combined:
            feedback += (
                f" The score has {lead_read['verses']} verses; verse "
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