"""
A score reads as a score.

The point of this path is that nothing has to be inferred
that the file already states: the lengths are written
values, the metre and key are given, and lyrics are
attached to their notes. So these check that what the
file says survives, rather than checking a repair.

The fixture is the app's own O Holy Night, which is why
it can be committed.
"""

import os
from fractions import Fraction

import pytest

FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "musicxml",
    "o-holy-night-satb.mxl"
)


def present():
    return os.path.exists(FIXTURE)


def imported(label="1"):
    from musicxml_import import import_musicxml

    return import_musicxml(FIXTURE, label)


def test_parts_are_named_as_the_score_names_them():
    """
    No guessing from General MIDI numbers: a score carries
    the name the engraver gave each part, and a part with
    lyrics is a part someone sings.
    """

    if not present():
        pytest.skip("the score fixture is not present")

    from musicxml_import import parts_in

    labels = parts_in(FIXTURE)

    assert any("Soprano" in label for label in labels)
    assert any("with words" in label for label in labels)


def test_the_lengths_are_the_scores_own():
    """
    Nothing rescaled, nothing snapped. A dotted quarter is
    three quarters of a beat because the score says so.
    """

    if not present():
        pytest.skip("the score fixture is not present")

    pitches, durations, lyrics, bpm, feedback, chart, poly, key = imported()

    lengths = [Fraction(value) for value in durations.split()]

    assert Fraction(3, 4) in lengths
    assert Fraction(1, 4) in lengths

    # Every length is something notation can write.
    for length in lengths:
        assert length.denominator <= 64


def test_a_tie_is_one_note_sung_once():
    """
    A note tied across a bar line is written twice on the
    page and sung once. Left as two, the second gets no
    syllable and every word after it slides.
    """

    if not present():
        pytest.skip("the score fixture is not present")

    pitches, durations, lyrics, bpm, feedback, chart, poly, key = imported()

    sung = len([note for note in pitches.split() if note != "R"])

    assert len(lyrics.split()) == sung


def test_the_words_are_joined_into_words():
    """
    The file marks every syllable "single" and relies on a
    trailing space to say where a word ends, which is how a
    printed score is typed. music21 strips that space, so
    it is read from the file directly - without it, "Ho"
    and "ly" arrive as two words.
    """

    if not present():
        pytest.skip("the score fixture is not present")

    pitches, durations, lyrics, bpm, feedback, chart, poly, key = imported()

    assert "Ho-" in lyrics.split()
    assert "ly" in lyrics.split()

    assert "bright-" in lyrics.split()


def test_word_ends_are_read_per_syllable_not_by_position():
    """
    The trailing-space reading was once a list indexed by
    note count - and this part has 129 notes but 125
    syllables (held notes carry no lyric), so from the first
    held note on, every word end was read from the wrong
    syllable: "di vine" arrived unjoined and "O night"
    joined. Now the flag is stamped on each syllable itself.
    These are the tokens that were wrong, checked against the
    file's own text.
    """

    if not present():
        pytest.skip("the score fixture is not present")

    pitches, durations, lyrics, bpm, feedback, chart, poly, key = imported()

    tokens = lyrics.split()

    # "di" has no trailing space in the file: di-vine.
    assert tokens.count("di-") == 6
    assert "di" not in tokens

    # "O " does: O night, never O-night.
    assert "O-" not in tokens

    # "voi" -> voi-ces, twice.
    assert tokens.count("voi-") == 2


def test_the_chart_is_exactly_as_long_as_the_music():
    """
    True by construction here, which is the point. The
    score states its divisions, so the melody and the
    voices under it are on one clock and nothing has to be
    rescaled onto anything else.
    """

    if not present():
        pytest.skip("the score fixture is not present")

    from chords import chart_beats, read_chart

    pitches, durations, lyrics, bpm, feedback, chart, poly, key = imported()

    music = sum(Fraction(value) for value in durations.split())

    read_chart(chart)

    assert chart_beats(chart) == float(music)


def test_what_comes_out_reads_as_music():
    """
    The same contract the MIDI importer meets, so
    everything above the import works unchanged.
    """

    if not present():
        pytest.skip("the score fixture is not present")

    from music import read_music, read_lyrics, list_phrases

    pitches, durations, lyrics, bpm, feedback, chart, poly, key = imported()

    read_music(pitches, durations)

    sung = len([note for note in pitches.split() if note != "R"])

    read_lyrics(lyrics, sung)

    # Phrases arrive as line breaks, correctable by hand.
    assert len(list_phrases(pitches, durations, lyrics)) > 1


def test_the_feedback_says_nothing_was_repaired():
    """
    Which is the difference worth telling a person about:
    a MIDI import may have respelled the timing, and this
    one had no need to.
    """

    if not present():
        pytest.skip("the score fixture is not present")

    pitches, durations, lyrics, bpm, feedback, chart, poly, key = imported()

    assert "score's own" in feedback


def test_a_part_number_is_read_from_a_label():
    from musicxml_import import part_number_from

    assert part_number_from("2  Piano, ALTO, 61 notes") == 2
    assert part_number_from(None) == 0
    assert part_number_from("nonsense") == 0


def test_the_extension_decides_which_importer_runs():
    """
    Both paths end in the same eight values, so nothing
    above the import needs to know which kind of file
    arrived.
    """

    from music import is_score_file, import_music_file

    assert is_score_file("piece.mxl")
    assert is_score_file("piece.musicxml")
    assert not is_score_file("piece.mid")
    assert not is_score_file(None)

    if not present():
        pytest.skip("the score fixture is not present")

    from_score = import_music_file(FIXTURE, "1")

    assert len(from_score) == 8

    midi = os.path.join(
        os.path.dirname(__file__), "fixtures", "midi",
        "d_ML_10791.mid"
    )

    if os.path.exists(midi):

        from music import list_music_parts

        from_midi = import_music_file(midi, list_music_parts(midi)[0])

        assert len(from_midi) == len(from_score)


def test_a_bar_in_compound_time_is_read_from_the_score():
    """
    Six eight is six eighth notes, which is three beats and
    not six. Taking the numerator drew every bar line at
    twice its width - and only in compound time, so a four
    four score hid it entirely.

    The library states the bar's length; nothing here
    should be working it out.
    """

    from music21 import meter

    for ratio, beats in [
        ("4/4", 4.0),
        ("3/4", 3.0),
        ("6/8", 3.0),
        ("9/8", 4.5),
        ("12/8", 6.0),
        ("2/2", 4.0),
    ]:
        signature = meter.TimeSignature(ratio)

        assert float(signature.barDuration.quarterLength) == beats


def test_the_words_are_joined_as_the_score_marks_them():
    """
    A score written by notation software marks each
    syllable begin, middle, end or single. Reading that is
    the format's own answer; the trailing space in the
    printed text is a fallback for scores that mark
    nothing.
    """

    from music21 import note as m21note

    item = m21note.Note("C4")
    item.lyrics.append(m21note.Lyric(text="Co", syllabic="begin", number=1))

    from musicxml_import import _syllable

    assert _syllable(item, 1) == "Co-"

    ending = m21note.Note("D4")
    ending.lyrics.append(
        m21note.Lyric(text="lors", syllabic="end", number=1)
    )

    assert _syllable(ending, 1) == "lors"


def test_a_verse_is_taken_whole_and_alone():
    """
    A score can write several verses under one line of
    notes. music21's convenience property joins them with
    newlines, and that string went into the boxes as one
    token and split into several later - so a two verse
    score arrived with more syllables than notes.
    """

    from music21 import note as m21note

    from musicxml_import import _syllable

    item = m21note.Note("C4")
    item.lyrics.append(m21note.Lyric(text="Heart", number=1))
    item.lyrics.append(m21note.Lyric(text="Time", number=2))

    assert _syllable(item, 1) == "Heart"
    assert _syllable(item, 2) == "Time"

    # And the joined string is never what lands in a box.
    assert "\n" not in _syllable(item, 1)


# Multi-key scores: a piece that genuinely modulates (Mulan's
# own "I'll Make a Man Out of You" changes from G major to Ab
# partway through) used to be read as one key throughout -
# the key box's own value, which is all _stated_key ever
# looked at. Melody pitches after the change came out spelled
# in the wrong dialect, since one midi_to_note(number, key)
# call served the whole piece. These build a small synthetic
# score directly (real key changes are rare enough that no
# committable fixture has one) rather than reusing the O Holy
# Night fixture, which never modulates.

def _build_modulating_score(path):

    from music21 import stream, note, key as m21key, meter

    part = stream.Part()
    part.insert(0, meter.TimeSignature("4/4"))
    part.insert(0, m21key.KeySignature(1))       # G major
    part.insert(8, m21key.KeySignature(-4))      # Ab major

    # F#4 (midi 66) spells unambiguously differently in G
    # (F#) versus Ab (Gb); Eb4 (midi 63) the same the other
    # way (Eb in Ab, D# in G) - either dialect used for the
    # wrong half would show up as a visibly wrong name, not
    # just a technically-equal enharmonic swap.
    part.insert(0, note.Note(66, quarterLength=1))
    part.insert(8, note.Note(63, quarterLength=1))

    score = stream.Score()
    score.append(part)
    score.write("musicxml", fp=str(path))


def test_a_note_after_the_key_change_spells_in_the_new_key(tmp_path):

    from musicxml_import import import_musicxml, parts_in

    path = tmp_path / "modulating.musicxml"

    _build_modulating_score(path)

    label = parts_in(str(path))[0]

    pitches, _, _, _, feedback, _, _, key = import_musicxml(
        str(path), label
    )

    words = pitches.split()

    # The note before the change: G major's own dialect.
    assert words[0] == "F#4"

    # The note after: Ab major's, not G's D#4.
    assert words[-1] == "Eb4"

    # The key box itself now holds the whole timeline -
    # stage 3's own change, transparently captured on
    # import: nothing about how a person imports differs,
    # the box just already says the whole story.
    assert key == "G, Ab from beat 8"

    assert "changes key" in feedback
    assert "Ab major" in feedback
    assert "bar 3" in feedback


def test_a_single_key_score_gets_no_key_change_note(tmp_path):
    """
    Regression pin: the common case (one signature, or none)
    must not grow a spurious "changes key" sentence, and
    every note must still spell in the one key throughout -
    exactly the behaviour before this feature existed.
    """

    from music21 import stream, note, key as m21key, meter

    from musicxml_import import import_musicxml, parts_in

    path = tmp_path / "single_key.musicxml"

    part = stream.Part()
    part.insert(0, meter.TimeSignature("4/4"))
    part.insert(0, m21key.KeySignature(1))
    part.insert(0, note.Note(66, quarterLength=1))
    part.insert(4, note.Note(63, quarterLength=1))

    score = stream.Score()
    score.append(part)
    score.write("musicxml", fp=str(path))

    label = parts_in(str(path))[0]

    pitches, _, _, _, feedback, _, _, key = import_musicxml(
        str(path), label
    )

    words = pitches.split()

    # Both notes spelled in G throughout - the second is
    # D#4, not Eb4, since nothing ever changed key.
    assert words[0] == "F#4"
    assert words[-1] == "D#4"

    assert key == "G"
    assert "changes key" not in feedback


def test_a_key_change_shown_only_on_another_part_is_still_caught(
    tmp_path
):
    """
    A modulation is sometimes restated on an accompaniment
    part's engraving without being reprinted on the vocal
    line's own staff - reading only the selected part would
    miss it entirely, even though the vocal line is
    genuinely in the new key from that point on.
    """

    from music21 import (
        stream, note, key as m21key, meter, instrument
    )

    from musicxml_import import import_musicxml, parts_in

    path = tmp_path / "cross_part.musicxml"

    voice = stream.Part()
    voice.insert(0, instrument.Vocalist())
    voice.insert(0, meter.TimeSignature("4/4"))
    voice.insert(0, m21key.KeySignature(1))
    voice.insert(0, note.Note(66, quarterLength=4))
    voice.insert(8, note.Note(63, quarterLength=4))

    piano = stream.Part()
    piano.insert(0, instrument.Piano())
    piano.insert(0, meter.TimeSignature("4/4"))
    piano.insert(0, m21key.KeySignature(1))
    piano.insert(8, m21key.KeySignature(-4))
    piano.insert(0, note.Note(50, quarterLength=8))

    score = stream.Score()
    score.append(voice)
    score.append(piano)
    score.write("musicxml", fp=str(path))

    label = parts_in(str(path))[0]

    pitches, _, _, _, feedback, _, _, key = import_musicxml(
        str(path), label
    )

    words = pitches.split()

    assert words[0] == "F#4"

    # The vocal part's own note after beat 8 - it never
    # restated the signature itself, but the compatible
    # piano part did, and that is enough to spell it right.
    assert "Eb4" in words

    assert "changes key" in feedback


def test_a_transposing_parts_signature_is_never_borrowed(tmp_path):
    """
    A part whose transposition differs from the selected
    part's (a Bb trumpet against a concert-pitch voice) is
    excluded outright: its signature is written in its own
    transposed pitch space, and borrowing it to spell a
    different part's notes would spell them wrong on
    purpose, not by accident.
    """

    from music21 import (
        stream, note, key as m21key, meter, instrument, interval
    )

    from musicxml_import import import_musicxml, parts_in

    path = tmp_path / "transposed.musicxml"

    voice = stream.Part()
    voice.insert(0, instrument.Vocalist())
    voice.insert(0, meter.TimeSignature("4/4"))
    voice.insert(0, m21key.KeySignature(1))
    voice.insert(0, note.Note(66, quarterLength=4))
    voice.insert(8, note.Note(63, quarterLength=4))

    trumpet = stream.Part()
    bb_trumpet = instrument.Trumpet()
    bb_trumpet.transposition = interval.Interval("M-2")
    trumpet.insert(0, bb_trumpet)
    trumpet.insert(0, meter.TimeSignature("4/4"))
    trumpet.insert(0, m21key.KeySignature(3))
    trumpet.insert(8, m21key.KeySignature(-2))
    trumpet.insert(0, note.Note(50, quarterLength=8))

    score = stream.Score()
    score.append(voice)
    score.append(trumpet)
    score.write("musicxml", fp=str(path))

    label = parts_in(str(path))[0]

    pitches, _, _, _, feedback, _, _, key = import_musicxml(
        str(path), label
    )

    words = pitches.split()

    # Still spelled in G throughout - the trumpet's own
    # signature (a different key entirely, in its own
    # transposed space) is never consulted.
    assert words[0] == "F#4"
    assert "D#4" in words
    assert "Eb4" not in words

    assert "changes key" not in feedback