"""
A score that prints its own chords should be read, not
re-guessed.

MusicXML can carry chord symbols the same way a lead sheet
does - a name above the staff, at a stated beat. Where a
file has them, invariant 5 says reading beats detecting:
a human wrote that symbol down, which is stronger evidence
than anything inferred from which notes happen to be
sounding. Where a file has none, the existing polyphony
detection is exactly as before.

These fixtures are built in memory with music21 rather than
committed as files, the same way a unit test builds any
other small piece of data - a chord symbol or two is not
worth a fixture file, and it keeps every case exact about
what it is testing.
"""

import os

import pytest

from musicxml_import import import_musicxml, parts_in, _printed_chart


def _build(path, chord_symbols=(), notes=(), time_signature="4/4"):
    """
    A minimal score: a time signature, some chord symbols
    at given offsets, and some notes at given offsets.

    notes is a list of (offset, midi, length) triples.
    chord_symbols is a list of (offset, name) pairs.
    """

    from music21 import stream, note, harmony, meter

    part = stream.Part()
    part.insert(0, meter.TimeSignature(time_signature))

    for offset, name in chord_symbols:
        symbol = harmony.ChordSymbol(name)
        part.insert(offset, symbol)

    for offset, midi, length in notes:
        part.insert(offset, note.Note(midi, quarterLength=length))

    score = stream.Score()
    score.append(part)
    score.write("musicxml", fp=str(path))


def _import(path):
    label = parts_in(str(path))[0]
    return import_musicxml(str(path), label)


def test_a_printed_chord_becomes_the_chart(tmp_path):

    path = tmp_path / "test.musicxml"

    _build(
        path,
        chord_symbols=[(0, "Em"), (2, "G")],
        notes=[(0, 64, 1), (1, 64, 1), (2, 67, 1), (3, 67, 1)]
    )

    _, _, _, _, feedback, chart, _, _ = _import(path)

    assert chart == "| Em . G . |"
    assert "printed" in feedback


def test_no_printed_symbols_falls_back_to_detection(tmp_path):
    """
    A file with real polyphony but no chord symbols reads
    exactly as it always did: detected, not printed.
    """

    path = tmp_path / "test.musicxml"

    from music21 import stream, chord as chord_mod, meter, note

    part = stream.Part()
    part.insert(0, meter.TimeSignature("4/4"))
    part.insert(0, chord_mod.Chord(["E4", "G4", "B4"], quarterLength=2))
    part.insert(2, chord_mod.Chord(["G4", "B4", "D5"], quarterLength=2))

    score = stream.Score()
    score.append(part)
    score.write("musicxml", fp=str(path))

    _, _, _, _, feedback, chart, _, _ = _import(path)

    assert chart
    assert "printed" not in feedback
    assert "sounding together" in feedback


def test_a_slash_chords_bass_note_is_dropped_not_the_root():
    """
    Invariant 12: the chart holds one name per chord because
    it must parse and play. D/F# is D with F# in the bass -
    the chart keeps D and drops the bass note, which is
    display detail the chart was never meant to carry.
    """

    from music21 import stream, harmony, meter

    part = stream.Part()
    part.insert(0, meter.TimeSignature("4/4"))
    part.insert(0, harmony.ChordSymbol("D/F#"))

    chart = _printed_chart([part], 4.0, 4.0)

    assert chart == "| D . . . |"


def test_an_unmappable_quality_falls_back_to_its_triad_shape():
    """
    C9 (a dominant ninth) has no exact match in the app's
    ten chord qualities. Its underlying triad is still
    major, so it becomes plain C rather than being dropped -
    a plainer chord that plays is worth more than an exact
    one the app cannot represent.
    """

    from music21 import stream, harmony, meter

    part = stream.Part()
    part.insert(0, meter.TimeSignature("4/4"))
    part.insert(0, harmony.ChordSymbol("C9"))

    chart = _printed_chart([part], 4.0, 4.0)

    assert chart == "| C . . . |"


def test_a_chord_with_no_representable_triad_is_dropped():
    """
    A power chord has no third, so it has no triad to fall
    back to (music21 calls its quality "other", same as its
    kind). Nothing to fall back to, so it is left out rather
    than guessed - the same choice invariant 6 makes anywhere
    else a guess would be worse than a gap.
    """

    from music21 import stream, harmony, meter

    part = stream.Part()
    part.insert(0, meter.TimeSignature("4/4"))
    part.insert(0, harmony.ChordSymbol("Cpower"))

    chart = _printed_chart([part], 4.0, 4.0)

    assert chart == ""


def test_a_no_chord_mark_is_skipped_not_a_crash():
    """
    A printed "N.C." (no chord) mark is real notation, not a
    malformed file - a real Disney lead sheet (Mulan's "I'll
    Make a Man Out of You") crashed the whole import on one
    of these. music21 parses it as a ChordSymbol with kind
    "none" and no root pitch at all, so symbol.root() is
    None; the surrounding chord should carry through the gap
    exactly as it would for a beat with no symbol printed.

    Built through MusicXML directly rather than
    harmony.ChordSymbol("N.C.") - that string form raises in
    music21 before ever reaching root(), so it would not
    reproduce the real bug. The <kind>none</kind> shape below
    is what a real file actually contains.
    """

    from music21 import converter

    xml = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1"><part-name>Music</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <time><beats>4</beats><beat-type>4</beat-type></time>
      </attributes>
      <harmony print-frame="no">
        <root><root-step text="">C</root-step></root>
        <kind text="">none</kind>
      </harmony>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
    </measure>
  </part>
</score-partwise>
"""

    score = converter.parse(xml)

    chart = _printed_chart(list(score.parts), 4.0, 4.0)

    assert chart == ""


def test_a_no_chord_mark_between_real_chords_does_not_crash():
    """
    The same "N.C." case, but sitting between two real
    printed chords rather than alone - the gap it leaves
    should be filled from the chord before it, same as any
    other beat with nothing printed. Built through MusicXML
    directly, same reasoning as the test above: constructing
    a rootless ChordSymbol any other way doesn't reproduce
    what a real file actually contains.
    """

    from music21 import converter

    xml = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1"><part-name>Music</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <time><beats>4</beats><beat-type>4</beat-type></time>
      </attributes>
      <harmony print-frame="no">
        <root><root-step text="">E</root-step></root>
        <kind text="">minor</kind>
      </harmony>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
      <harmony print-frame="no">
        <root><root-step text="">C</root-step></root>
        <kind text="">none</kind>
      </harmony>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
    </measure>
    <measure number="2">
      <harmony print-frame="no">
        <root><root-step text="">G</root-step></root>
        <kind text="">major</kind>
      </harmony>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
    </measure>
  </part>
</score-partwise>
"""

    score = converter.parse(xml)

    chart = _printed_chart(list(score.parts), 8.0, 4.0)

    assert chart == "| Em . . . | G . . . |"


def test_offsets_are_read_across_the_whole_piece_not_one_measure():
    """
    A chord symbol's own .offset resets to zero at every
    measure - only a flattened part turns that into one
    running count from the start of the piece. Read the
    unflattened way, a chord in the second bar collides
    with whatever is in the first bar's equivalent beat,
    and every bar after the first is silently wrong.
    """

    from music21 import stream, harmony, meter, note

    part = stream.Part()
    part.insert(0, meter.TimeSignature("4/4"))

    # Bar 1: nothing printed. Bar 2: a chord on its second
    # beat - absolute beat 5, not beat 1.
    part.insert(4, harmony.ChordSymbol("G"))

    for offset in range(8):
        part.insert(offset, note.Note(60, quarterLength=1))

    chart = _printed_chart([part], 8.0, 4.0)

    # fill_gaps stretches the first (only) chord back to
    # the start, so the whole chart is G - but it has to be
    # one chord lasting the whole piece, not two bars each
    # thinking they hold beat 1.
    assert chart == "| G . . . | . . . . |"


def test_a_pickup_chord_lands_on_its_true_half_beat():
    """
    A symbol on the "and" of a beat used to have to give up
    that timing entirely - the chart only held one token per
    beat, so this landed floored to the beat it started
    within. Now a genuine half-beat offset keeps its true
    position: the previous chord (Em) carries through the
    first half of the last beat, and G arrives on its own
    half via the bare ">G" token - a chord already sounding
    just continuing, with only the second half new.
    """

    from music21 import stream, harmony, meter

    part = stream.Part()
    part.insert(0, meter.TimeSignature("4/4"))
    part.insert(0, harmony.ChordSymbol("Em"))
    part.insert(3.5, harmony.ChordSymbol("G"))

    chart = _printed_chart([part], 4.0, 4.0)

    assert chart == "| Em . . >G |"


def test_a_finer_than_half_beat_pickup_still_floors():
    """
    Only an EXACT half keeps its precision. A sixteenth-note
    pickup (offset 3.25) is finer than a chart split can
    hold, so it still gives up its timing entirely and
    floors to the beat it starts within - the same graceful
    fallback as before, not a crash and not a wrong split.
    """

    from music21 import stream, harmony, meter

    part = stream.Part()
    part.insert(0, meter.TimeSignature("4/4"))
    part.insert(0, harmony.ChordSymbol("Em"))
    part.insert(3.25, harmony.ChordSymbol("G"))

    chart = _printed_chart([part], 4.0, 4.0)

    assert chart == "| Em . . G |"


def test_duplicate_symbols_on_a_second_staff_are_read_once():
    """
    A grand-staff piano part often prints the same chord
    symbols on both staves. Reading every part should not
    double the chart or disagree with itself.
    """

    from music21 import stream, harmony, meter, note

    def staff():
        part = stream.Part()
        part.insert(0, meter.TimeSignature("4/4"))
        part.insert(0, harmony.ChordSymbol("C"))
        part.insert(2, harmony.ChordSymbol("G"))
        part.insert(0, note.Note(60, quarterLength=4))
        return part

    chart = _printed_chart([staff(), staff()], 4.0, 4.0)

    assert chart == "| C . G . |"


def test_chord_symbols_are_not_counted_as_notes(tmp_path):
    """
    music21 models a chord symbol as a kind of chord, so it
    passes every "just the notes" filter a real note passes.
    Left in, four real notes and two printed chord symbols
    would be read as six notes, and the two symbols would
    turn into phantom pitches in the melody.
    """

    path = tmp_path / "test.musicxml"

    _build(
        path,
        chord_symbols=[(0, "Em"), (2, "G")],
        notes=[(0, 60, 1), (1, 62, 1), (2, 64, 1), (3, 65, 1)]
    )

    label = parts_in(str(path))[0]

    assert "4 notes" in label

    pitches, durations, _, _, _, _, _, _ = import_musicxml(
        str(path), label
    )

    assert len(pitches.split()) == 4


def test_a_wordy_tempo_mark_does_not_crash_the_import(tmp_path):
    """
    A metronome mark can be words alone - "Moderately",
    with no number - and music21 reads its number as None.
    A wordy mark says nothing a BPM box can hold, so the
    import falls back to the default rather than falling
    over. Found by a real published arrangement, not
    invented.
    """

    from music21 import stream, note, meter, tempo

    path = tmp_path / "test.musicxml"

    part = stream.Part()
    part.insert(0, meter.TimeSignature("4/4"))
    part.insert(0, tempo.MetronomeMark("Moderately"))

    for offset in range(4):
        part.insert(offset, note.Note(60 + offset, quarterLength=1))

    score = stream.Score()
    score.append(part)
    score.write("musicxml", fp=str(path))

    label = parts_in(str(path))[0]

    _, _, _, bpm, _, _, _, _ = import_musicxml(str(path), label)

    assert bpm == 100