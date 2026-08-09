import mido
import pytest

from midi_import import (
    MidiImportError,
    import_midi,
    snap_to_beat,
    keep_melody
)


def write_midi(path, notes, bpm=120, lyrics=None):
    """
    Build a simple MIDI file for a test.

    notes is a list of (midi_number, beats).
    """

    ticks = 480

    midi_file = mido.MidiFile(ticks_per_beat=ticks)
    track = mido.MidiTrack()
    midi_file.tracks.append(track)

    track.append(
        mido.MetaMessage(
            "set_tempo",
            tempo=mido.bpm2tempo(bpm),
            time=0
        )
    )

    for position, (number, beats) in enumerate(notes):

        if lyrics is not None and position < len(lyrics):
            track.append(
                mido.MetaMessage(
                    "lyrics",
                    text=lyrics[position],
                    time=0
                )
            )

        track.append(
            mido.Message(
                "note_on", note=number, velocity=80, time=0
            )
        )

        track.append(
            mido.Message(
                "note_off",
                note=number,
                velocity=0,
                time=int(beats * ticks)
            )
        )

    midi_file.save(path)

    return path


def test_imports_a_simple_melody(tmp_path):
    path = write_midi(
        str(tmp_path / "simple.mid"),
        [(60, 1), (64, 1), (67, 2)],
        bpm=100
    )

    pitches, durations, lyric_text, bpm, chart, chart_notes = import_midi(path)

    assert pitches == "C4 E4 G4"
    assert durations == "1 1 2"
    assert bpm == 100


def test_imports_karaoke_lyrics(tmp_path):
    path = write_midi(
        str(tmp_path / "lyrics.mid"),
        [(60, 1), (64, 1)],
        lyrics=["la", "la"]
    )

    pitches, durations, lyric_text, bpm, chart, chart_notes = import_midi(path)

    assert lyric_text == "la la"


def test_notes_without_words_are_marked_as_held(tmp_path):
    """
    A file with fewer syllables than notes keeps the words
    it has. The notes with nothing of their own carry on
    the syllable before them, which is what a score means
    by writing a word once and holding it.
    """

    path = write_midi(
        str(tmp_path / "odd.mid"),
        [(60, 1), (64, 1), (67, 1)],
        lyrics=["only", "two"]
    )

    # Two lyric events against three notes.
    midi_file = mido.MidiFile(path)
    events = [
        m for t in midi_file.tracks for m in t
        if m.type == "lyrics"
    ]
    assert len(events) == 2

    pitches, durations, lyric_text, bpm, chart, chart_notes = import_midi(path)

    assert lyric_text == "only two _"


def test_chords_keep_the_top_note():
    """
    When notes start together, the melody is taken to be
    the highest.
    """

    together = [
        (0.0, 1.0, 60),
        (0.0, 1.0, 64),
        (0.0, 1.0, 67),
        (1.0, 1.0, 65)
    ]

    melody = keep_melody(together)

    assert [number for _, _, number in melody] == [67, 65]


def test_awkward_lengths_snap_to_beats():
    assert snap_to_beat(0.98) == 1.0
    assert snap_to_beat(0.52) == 0.5

    # Nearer a double dotted quarter than a dotted one.
    assert snap_to_beat(1.7) == 1.75

    # A double dotted whole note is a length in its own
    # right, so it is kept rather than rounded down.
    assert snap_to_beat(7.0) == 7.0


def test_unreadable_file_is_reported(tmp_path):
    path = tmp_path / "noise.mid"
    path.write_bytes(b"this is not midi")

    with pytest.raises(MidiImportError, match="could not be read"):
        import_midi(str(path))


def test_empty_file_is_reported(tmp_path):
    midi_file = mido.MidiFile()
    midi_file.tracks.append(mido.MidiTrack())

    path = str(tmp_path / "empty.mid")
    midi_file.save(path)

    with pytest.raises(MidiImportError, match="No notes"):
        import_midi(path)


def test_describe_tracks_lists_each_voice(tmp_path):
    """
    A file with a part per track describes them all, so
    the player can pick the line they are singing.
    """

    from midi_import import describe_tracks

    midi_file = mido.MidiFile(ticks_per_beat=480)

    voices = [
        [(72, 1), (74, 1)],
        [(60, 1), (62, 1)]
    ]

    for voice in voices:

        track = mido.MidiTrack()
        midi_file.tracks.append(track)

        for number, beats in voice:
            track.append(
                mido.Message(
                    "note_on", note=number, velocity=80, time=0
                )
            )
            track.append(
                mido.Message(
                    "note_off",
                    note=number,
                    velocity=0,
                    time=int(beats * 480)
                )
            )

    path = str(tmp_path / "satb.mid")
    midi_file.save(path)

    described = describe_tracks(path)

    assert len(described) == 2

    assert described[0][0] == 0
    assert "C5" in described[0][1]
    assert "C4" in described[1][1]


def test_importing_one_track_ignores_the_others(tmp_path):
    """
    Choosing a track imports that line alone, not the
    highest note of everything sounding at once.
    """

    midi_file = mido.MidiFile(ticks_per_beat=480)

    for numbers in ([72, 74], [60, 62]):

        track = mido.MidiTrack()
        midi_file.tracks.append(track)

        for number in numbers:
            track.append(
                mido.Message(
                    "note_on", note=number, velocity=80, time=0
                )
            )
            track.append(
                mido.Message(
                    "note_off", note=number, velocity=0, time=480
                )
            )

    path = str(tmp_path / "two.mid")
    midi_file.save(path)

    lower, durations, lyrics, bpm, chart, chart_notes = import_midi(
        path,
        track_number=1
    )

    assert lower == "C4 D4"

    upper, durations, lyrics, bpm, chart, chart_notes = import_midi(
        path,
        track_number=0
    )

    assert upper == "C5 D5"


def test_dotted_lengths_are_kept():
    """
    Dotted notes are ordinary music, and a file full of
    them drifts out of time if they round to the nearest
    plain note instead.
    """

    assert snap_to_beat(0.373) == 0.375
    assert snap_to_beat(1.748) == 1.75
    assert snap_to_beat(2.748) == 2.75
    assert snap_to_beat(0.87) == 0.875


def test_triplets_are_kept():
    assert snap_to_beat(0.334) == pytest.approx(1 / 3)
    assert snap_to_beat(0.665) == pytest.approx(2 / 3)


def test_plain_lengths_still_win_when_they_are_nearest():
    assert snap_to_beat(0.98) == 1.0
    assert snap_to_beat(0.51) == 0.5
    assert snap_to_beat(2.02) == 2.0


def make_gapped_file(path, groups, gap_beats=1.0):
    """
    Build a file whose notes fall into groups separated by
    rests, the way phrases are separated in real music.
    """

    ticks = 480

    midi_file = mido.MidiFile(ticks_per_beat=ticks)
    track = mido.MidiTrack()
    midi_file.tracks.append(track)

    waiting = 0

    for group in groups:

        for number in group:

            track.append(
                mido.Message(
                    "note_on",
                    note=number,
                    velocity=80,
                    time=waiting
                )
            )
            track.append(
                mido.Message(
                    "note_off", note=number, velocity=0, time=ticks
                )
            )

            waiting = 0

        waiting = int(gap_beats * ticks)

    midi_file.save(path)

    return path


def test_phrases_break_where_the_music_rests(tmp_path):
    from midi_import import describe_phrases

    path = make_gapped_file(
        str(tmp_path / "phrased.mid"),
        [
            [60, 62, 64, 65, 67],
            [67, 65, 64, 62, 60]
        ]
    )

    described = describe_phrases(path)

    assert len(described) == 2
    assert "Phrase 1" in described[0][1]
    assert "5 notes" in described[0][1]


def test_a_phrase_imports_on_its_own(tmp_path):
    path = make_gapped_file(
        str(tmp_path / "two_phrases.mid"),
        [
            [60, 62, 64, 65],
            [72, 74, 76, 77]
        ]
    )

    pitches, durations, lyrics, bpm, chart, chart_notes = import_midi(
        path,
        phrase_number=1
    )

    # The phrase is padded out to the bars around it, so
    # its chords, bar lines and downbeats have somewhere
    # to sit. The rests are the count before it and the
    # breath after.
    assert "C5 D5 E5 F5" in pitches
    assert pitches.startswith("R")
    assert pitches.endswith("R")


def test_short_phrases_are_joined_to_the_next(tmp_path):
    """
    Two notes alone are not worth practising, so they
    belong with what follows.
    """

    from midi_import import describe_phrases

    path = make_gapped_file(
        str(tmp_path / "short.mid"),
        [
            [60, 62],
            [64, 65, 67, 69, 71]
        ]
    )

    described = describe_phrases(path)

    assert len(described) == 1
    assert "7 notes" in described[0][1]


def test_asking_for_a_phrase_that_is_not_there(tmp_path):
    path = make_gapped_file(
        str(tmp_path / "one.mid"),
        [[60, 62, 64, 65]]
    )

    with pytest.raises(MidiImportError, match="not in this music"):
        import_midi(path, phrase_number=9)


def test_nothing_is_lost_when_a_track_is_split(tmp_path):
    """
    Every note of the track must appear in some phrase.
    """

    from midi_import import (
        read_notes,
        keep_melody,
        split_into_phrases
    )

    path = make_gapped_file(
        str(tmp_path / "whole.mid"),
        [
            [60, 62, 64, 65],
            [67, 69, 71, 72],
            [72, 71, 69, 67]
        ]
    )

    midi_file = mido.MidiFile(path)
    notes, bpm = read_notes(midi_file)
    melody = keep_melody(notes)

    phrases = split_into_phrases(melody)

    counted = sum(len(phrase) for phrase in phrases)

    assert counted == len(melody)


def test_lengths_are_written_as_fractions_of_a_beat(tmp_path):
    """
    Note lengths are fractions by nature, and writing them
    that way shows the structure: dotted notes are three
    over something, double dotted are seven over something.
    """

    path = write_midi(
        str(tmp_path / "fractions.mid"),
        [
            (60, 1),      # a beat
            (62, 0.5),    # an eighth
            (64, 0.75),   # dotted eighth
            (65, 1.5),    # dotted quarter
            (67, 2)       # a half note
        ]
    )

    pitches, durations, lyrics, bpm, chart, chart_notes = import_midi(path)

    assert durations == "1 1/2 3/4 3/2 2"


def test_fraction_lengths_read_back_the_same(tmp_path):
    """
    What the importer writes, the music boxes must read.
    """

    from music import read_beats

    path = write_midi(
        str(tmp_path / "roundtrip.mid"),
        [(60, 1 / 3), (62, 1 / 3), (64, 1 / 3), (65, 0.75)]
    )

    pitches, durations, lyrics, bpm, chart, chart_notes = import_midi(path)

    values = [read_beats(text) for text in durations.split()]

    assert sum(values[:3]) == pytest.approx(1.0)
    assert values[3] == pytest.approx(0.75)


def test_a_phrase_never_runs_past_the_cap():
    """
    Music that never rests still has to be divided. The
    cap is a hard limit, not a suggestion: it holds even
    when no note lands on a bar line to break at.
    """

    from midi_import import (
        split_into_phrases,
        LONGEST_PHRASE_SECONDS,
        beats_from_seconds
    )

    # Sixty beats of unbroken singing, deliberately off
    # the bar grid so no tidy break is available.
    melody = [
        (0.5 + position, 1.0, 60)
        for position in range(60)
    ]

    bpm = 120

    phrases = split_into_phrases(
        melody, beats_per_bar=4, bpm=bpm
    )

    cap = beats_from_seconds(LONGEST_PHRASE_SECONDS, bpm)

    assert len(phrases) > 1

    for phrase in phrases:

        first = phrase[0][0]
        last = phrase[-1][0] + phrase[-1][1]

        assert last - first <= cap


def test_a_long_phrase_prefers_to_break_at_a_bar_line():
    """
    Breaking mid bar is awkward to count in, so a bar line
    near the cap is taken in preference.
    """

    from midi_import import split_into_phrases

    melody = [
        (float(position), 1.0, 60)
        for position in range(60)
    ]

    phrases = split_into_phrases(melody, beats_per_bar=4)

    for phrase in phrases[1:]:
        assert phrase[0][0] % 4 == 0


def write_voice(midi_file, notes, words=None, ticks=480):
    """
    Add one voice to a file, optionally with its own words.

    Notation software writes lyrics into the staff they
    belong to, so each voice carries its own.
    """

    track = mido.MidiTrack()
    midi_file.tracks.append(track)

    for position, (number, beats) in enumerate(notes):

        if words is not None and position < len(words):
            track.append(
                mido.MetaMessage(
                    "lyrics", text=words[position], time=0
                )
            )

        track.append(
            mido.Message(
                "note_on", note=number, velocity=80, time=0
            )
        )
        track.append(
            mido.Message(
                "note_off",
                note=number,
                velocity=0,
                time=int(beats * ticks)
            )
        )

    return track


def test_each_voice_keeps_its_own_words(tmp_path):
    """
    A choral file carries a set of lyrics under every
    part. Reading them all together would give several
    times the syllables and match nothing.
    """

    midi_file = mido.MidiFile(ticks_per_beat=480)

    write_voice(
        midi_file,
        [(72, 1), (74, 1), (76, 1)],
        ["Glo-", "ri-", "a"]
    )

    write_voice(
        midi_file,
        [(60, 1), (62, 1), (64, 1)],
        ["Ah", "ah", "ah"]
    )

    path = str(tmp_path / "choral.mid")
    midi_file.save(path)

    pitches, durations, upper, bpm, chart, chart_notes = import_midi(
        path, track_number=0
    )

    assert upper == "Glo- ri- a"

    pitches, durations, lower, bpm, chart, chart_notes = import_midi(
        path, track_number=1
    )

    assert lower == "Ah ah ah"


def test_a_phrase_keeps_only_its_own_words(tmp_path):
    """
    Lifting one phrase out of a piece must lift its words
    with it, not the words of the whole song.
    """

    midi_file = mido.MidiFile(ticks_per_beat=480)

    # Four notes, since a shorter phrase would be folded
    # into the one after it.
    track = write_voice(
        midi_file,
        [(60, 1), (62, 1), (64, 1), (65, 1)],
        ["There", "once", "was", "a"]
    )

    # A rest, then a second phrase with its own words.
    for position, (number, word) in enumerate(
        [(65, "put"), (67, "to"), (69, "sea"), (71, "now")]
    ):
        track.append(
            mido.MetaMessage(
                "lyrics",
                text=word,
                time=480 if position == 0 else 0
            )
        )
        track.append(
            mido.Message(
                "note_on", note=number, velocity=80, time=0
            )
        )
        track.append(
            mido.Message(
                "note_off", note=number, velocity=0, time=480
            )
        )

    path = str(tmp_path / "phrases.mid")
    midi_file.save(path)

    pitches, durations, lyrics, bpm, chart, chart_notes = import_midi(
        path, phrase_number=1
    )

    assert lyrics == "put to sea now"


def test_unmatched_lyrics_are_left_out(tmp_path):
    """
    Words that do not line up with the notes are dropped:
    wrong words are worse than none.
    """

    midi_file = mido.MidiFile(ticks_per_beat=480)

    track = write_voice(
        midi_file,
        [(60, 1), (62, 1), (64, 1)]
    )

    # One stray syllable, after the singing has finished,
    # where no note begins. Note that it has to go at the
    # end: a lyric placed before a note delays that note
    # too, and would line up with it after all.
    track.append(
        mido.MetaMessage("lyrics", text="stray", time=240)
    )

    path = str(tmp_path / "stray.mid")
    midi_file.save(path)

    pitches, durations, lyrics, bpm, chart, chart_notes = import_midi(path)

    # The stray syllable lines up with nothing, so there
    # is nothing to keep.
    assert lyrics == ""


def test_a_long_phrase_is_divided_at_its_widest_breath():
    """
    Two sung lines are often separated by a breath too
    short to be written as a rest. Rather than treat every
    such gap as a phrase end, an overlong phrase is divided
    at its own widest gap, which is where the breath was.
    """

    from midi_import import split_at_widest_gap

    # Twelve beats of singing with a small gap halfway.
    melody = []
    time = 0.0

    for position in range(12):

        melody.append((time, 1.0, 60 + position))

        time += 1.0

        if position == 5:
            time += 0.3

    phrases = split_at_widest_gap(melody, longest_beats=8)

    assert len(phrases) == 2
    assert len(phrases[0]) == 6
    assert len(phrases[1]) == 6


def test_phrase_length_is_measured_in_time_not_notes():
    """
    Fourteen sixteenth notes and fourteen half notes are
    the same count and nothing like the same phrase. A
    breath is a length of time.
    """

    from midi_import import split_at_widest_gap

    # Sixteen quick notes, four beats in total: short
    # enough to sing in one breath despite the count.
    quick = [
        (position * 0.25, 0.25, 60)
        for position in range(16)
    ]

    assert len(split_at_widest_gap(quick, longest_beats=8)) == 1

    # Eight slow notes, thirty two beats: far too long,
    # despite being half as many notes.
    slow = []
    time = 0.0

    for position in range(8):
        slow.append((time, 4.0, 60))
        time += 4.0
        if position == 3:
            time += 0.5

    assert len(split_at_widest_gap(slow, longest_beats=8)) > 1


def test_a_phrase_within_the_limit_is_left_alone():
    from midi_import import split_at_widest_gap

    melody = [
        (position * 0.5, 0.5, 60)
        for position in range(6)
    ]

    assert split_at_widest_gap(melody, longest_beats=8) == [melody]


def test_the_same_music_phrases_differently_at_different_tempos():
    """
    A phrase is bounded by breath, and how much music fits
    in a breath depends on how fast it goes by. The same
    written notes are one phrase when quick and several
    when slow.
    """

    from midi_import import split_into_phrases

    # Twenty four beats of singing with small gaps, which
    # is a minute and a half at twenty beats a minute and
    # a few seconds at three hundred.
    melody = []
    time = 0.0

    for position in range(24):

        melody.append((time, 1.0, 60))

        time += 1.0

        if position % 4 == 3:
            time += 0.3

    quick = split_into_phrases(melody, 4, bpm=300)
    slow = split_into_phrases(melody, 4, bpm=40)

    assert len(slow) > len(quick)


def test_dividing_never_leaves_a_scrap():
    """
    Both halves must be worth singing, so a phrase is not
    divided in a way that leaves two or three notes alone.
    """

    from midi_import import (
        split_at_widest_gap,
        SHORTEST_PHRASE_NOTES
    )

    # The widest gap sits right at the start, where using
    # it would leave a single note behind.
    melody = [(0.0, 0.5, 60), (2.0, 0.5, 62)]

    for position in range(2, 12):
        melody.append((2.0 + position * 0.5, 0.5, 60 + position))

    for phrase in split_at_widest_gap(melody, longest_beats=8):
        assert len(phrase) >= SHORTEST_PHRASE_NOTES


def test_a_word_held_across_notes_marks_the_notes_that_carry_it():
    """
    A word sung across several notes is written once in a
    score, and the notes carrying it on are marked as held.
    Those notes must not throw away the words that did
    line up.
    """

    import tempfile
    import os

    midi_file = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    midi_file.tracks.append(track)

    words = {0: "A-", 2: "men"}

    for position, number in enumerate([60, 62, 64, 65]):

        if position in words:
            track.append(
                mido.MetaMessage(
                    "lyrics", text=words[position], time=0
                )
            )

        track.append(
            mido.Message(
                "note_on", note=number, velocity=80, time=0
            )
        )
        track.append(
            mido.Message(
                "note_off", note=number, velocity=0, time=480
            )
        )

    path = os.path.join(tempfile.mkdtemp(), "melisma.mid")
    midi_file.save(path)

    pitches, durations, lyrics, bpm, chart, chart_notes = import_midi(path)

    assert lyrics == "A- _ men _"


def test_partial_lyrics_are_kept(tmp_path):
    """
    Words for half the notes are still worth having.
    """

    midi_file = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    midi_file.tracks.append(track)

    for position, number in enumerate([60, 62, 64, 65, 67, 69]):

        if position < 2:
            track.append(
                mido.MetaMessage(
                    "lyrics", text=f"word{position}", time=0
                )
            )

        track.append(
            mido.Message(
                "note_on", note=number, velocity=80, time=0
            )
        )
        track.append(
            mido.Message(
                "note_off", note=number, velocity=0, time=480
            )
        )

    path = str(tmp_path / "partial.mid")
    midi_file.save(path)

    pitches, durations, lyrics, bpm, chart, chart_notes = import_midi(path)

    assert lyrics.startswith("word0 word1")
    assert lyrics.count("_") == 4


def test_repeated_notes_are_not_lost(tmp_path):
    """
    Several notes of the same pitch can sound at once: a
    piano part repeating a note under a held pedal, or two
    voices meeting on the same pitch.

    Keeping only the latest start loses every one but the
    last, which quietly drops a fifth of the notes in a
    real piano arrangement and gives every reader of those
    notes - chords, key, melody - the wrong music.
    """

    import mido

    from midi_import import read_notes

    midi_file = mido.MidiFile()
    track = mido.MidiTrack()
    midi_file.tracks.append(track)

    ticks = midi_file.ticks_per_beat

    # The same pitch struck twice, the second beginning
    # before the first has ended.
    track.append(mido.Message("note_on", note=60, velocity=64, time=0))
    track.append(mido.Message("note_on", note=60, velocity=64, time=ticks // 2))
    track.append(mido.Message("note_off", note=60, time=ticks // 2))
    track.append(mido.Message("note_off", note=60, time=ticks // 2))

    notes, bpm = read_notes(midi_file)

    assert len(notes) == 2


def test_every_note_in_a_real_file_is_read():
    """
    Checked against an independent parser, since a reader
    that silently drops notes looks perfectly healthy from
    the inside.
    """

    import os

    import mido

    miditoolkit = pytest.importorskip("miditoolkit")

    from midi_import import read_notes

    path = os.path.join(
        os.path.dirname(__file__),
        "fixtures", "midi", "o-holy-night-satb.mid"
    )

    if not os.path.exists(path):
        pytest.skip("the satb fixture is not present")

    ours, bpm = read_notes(mido.MidiFile(path))

    theirs = sum(
        len(instrument.notes)
        for instrument in miditoolkit.MidiFile(path).instruments
    )

    assert len(ours) == theirs