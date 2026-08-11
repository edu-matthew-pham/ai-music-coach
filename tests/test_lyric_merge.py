"""
Correcting lyrics must never move them.

The file owns the timing: each syllable is attached to a
note, and that matching happened at import before
anything was respelled. A paste rewrites the words and
nothing else, so every test here checks first that the
number of syllables came back unchanged.

The words used are public domain. The files this feature
exists for are not, and their lyrics are not committed.
"""

import pytest

from lyric_merge import (
    merge_lyrics,
    fit_line,
    assign_words,
    joined_words,
    syllabify,
    closeness,
    bare
)


def count(text):
    return len(text.split())


def test_a_word_split_without_hyphens_is_rejoined():
    """
    The case the feature exists for: a file that split a
    word across notes and wrote no hyphen to say so, so
    nothing in the file itself can recover the word.
    """

    messy = "TWIN- KLE TWIN KLE LIT TLE STAR"

    fixed, report = merge_lyrics(
        messy, "Twin- kle twin- kle lit- tle star"
    )

    assert count(fixed) == count(messy)
    assert fixed == "Twin- kle twin- kle lit- tle star"


def test_the_number_of_syllables_never_changes():
    """
    One note, one syllable, before and after. A syllable
    added or dropped moves every word after it onto the
    wrong note.
    """

    for messy, pasted in [
        ("TWIN KLE TWIN KLE LIT TLE STAR",
         "Twin- kle twin- kle lit- tle star"),
        ("THERE ONCE WAS A SHIP THAT PUT TO SEA",
         "There once was a ship that put to sea"),
        ("SOON MAY THE WEL LER MAN COME",
         "Soon may the Wel- ler- man come"),
    ]:
        fixed, report = merge_lyrics(messy, pasted)

        assert count(fixed) == count(messy), report


def test_a_line_that_does_not_match_is_left_alone():
    """
    Refusing is the safe answer. A word in capitals is
    ugly; a word on the wrong note is wrong.
    """

    messy = "TWIN KLE TWIN KLE LIT TLE STAR\nNOTH ING LIKE THIS AT ALL HERE"

    fixed, report = merge_lyrics(
        messy,
        "Twinkle twinkle little star\n"
        "How I wonder what you are"
    )

    assert count(fixed) == count(messy)

    # The second line matched nothing, so it kept what it
    # had rather than taking words that are not its own.
    assert "NOTH ING LIKE THIS AT ALL HERE" in fixed
    assert "did not match" in report


def test_the_two_sides_need_not_break_in_the_same_places():
    """
    The bug this design replaced. A file breaks where the
    singer breathes, often inside a word; the paste breaks
    where lyrics are written out. Matching line to line
    forced a split word into whichever line held its first
    syllable and everything after it drifted.
    """

    # The file breaks inside "little" and inside "wonder".
    messy = "TWIN- KLE TWIN KLE LIT\nTLE STAR HOW I WON\nDER WHAT YOU ARE"

    fixed, report = merge_lyrics(
        messy,
        "Twinkle twinkle little star\n"
        "How I wonder what you are"
    )

    assert count(fixed) == count(messy)

    assert fixed == (
        "Twin- kle twin- kle lit- tle star\n"
        "How I won- der what you are"
    )


def test_the_phrases_can_come_from_the_words():
    """
    A file's line breaks are wherever the import guessed.
    The paste's are a human's idea of where the phrases
    fall, which is better information and free.
    """

    messy = "TWIN KLE TWIN\nKLE LIT TLE STAR"

    fixed, report = merge_lyrics(
        messy, "Twinkle twinkle\nlittle star"
    )

    assert fixed.split("\n") == ["Twin- kle twin- kle", "lit- tle star"]
    assert "phrases now follow" in report


def test_the_file_keeps_its_phrasing_when_not_asked():
    messy = "TWIN KLE TWIN\nKLE LIT TLE STAR"

    fixed, report = merge_lyrics(
        messy, "Twinkle twinkle\nlittle star",
        take_phrasing=False
    )

    assert [len(line.split()) for line in fixed.split("\n")] == [3, 4]


def test_near_spellings_count_as_the_same_word():
    """
    An apostrophe or a missing letter is the same word
    written differently, not a different word.
    """

    assert closeness(bare("tonguin'"), bare("tonguing")) > 0.75
    assert closeness(bare("SHORE"), bare("shore")) == 1.0

    assert closeness(bare("shore"), bare("elephant")) < 0.5


def test_a_line_shorter_than_its_words_is_refused():
    """
    Four notes cannot carry five words without something
    being dropped.
    """

    tokens = ["A", "B", "C"]

    runs, score = assign_words(tokens, ["one", "two", "three", "four"])

    assert runs is None


def test_every_syllable_belongs_to_exactly_one_word():
    """
    Which is what preserves the count by construction:
    the assignment decides where the boundaries fall,
    never how many pieces there are.
    """

    tokens = "TWIN KLE TWIN KLE LIT TLE STAR".split()

    runs, score = assign_words(
        tokens, ["twinkle", "twinkle", "little", "star"]
    )

    flat = [position for run in runs for position in run]

    assert sorted(flat) == list(range(len(tokens)))
    assert all(len(run) >= 1 for run in runs)


def test_held_notes_stay_held():
    """
    An underscore is the word before, still sounding. It
    is not a syllable waiting to be given a word.
    """

    fixed, report = fit_line(
        "STAR _ _", "star _ _"
    )

    assert fixed[1] == "_"
    assert fixed[2] == "_"


def test_a_word_over_several_notes_is_hyphenated():
    """
    Written back the way the app reads it: a trailing
    hyphen on every piece but the last.
    """

    pieces = syllabify("wellerman", 3)

    assert len(pieces) == 3
    assert pieces[0].endswith("-")
    assert pieces[1].endswith("-")
    assert not pieces[2].endswith("-")

    assert "".join(piece.rstrip("-") for piece in pieces) == "wellerman"


def test_a_word_on_one_note_is_left_whole():
    assert syllabify("star", 1) == ["star"]


def test_hyphens_are_read_when_they_are_there():
    """
    A file that did write its hyphens says which syllables
    belong together, and that reading still works.
    """

    words = joined_words("Twin- kle lit- tle star".split())

    assert [word for word, positions in words] == [
        "twinkle", "little", "star"
    ]


def test_nothing_to_do_is_said_rather_than_done():
    fixed, report = merge_lyrics("", "Twinkle twinkle")

    assert "no lyrics" in report

    fixed, report = merge_lyrics("TWIN KLE", "")

    assert "Paste the words" in report
    assert fixed == "TWIN KLE"


def test_a_paste_holding_more_than_the_file_sings():
    """
    A tab holds every verse; a file often sings some. The
    stretch that fits the notes is found, whole lines at a
    time, rather than the paste being refused.
    """

    messy = "TWIN KLE TWIN KLE LIT TLE STAR"

    fixed, report = merge_lyrics(
        messy,
        "Up above the world so high\n"
        "Twinkle twinkle little star\n"
        "Like a diamond in the sky"
    )

    assert count(fixed) == count(messy)
    assert fixed == "Twin- kle twin- kle lit- tle star"


def test_a_paste_that_is_not_this_song_is_refused():
    messy = "TWIN KLE TWIN KLE LIT TLE STAR"

    fixed, report = merge_lyrics(
        messy,
        "Nothing here resembles it\n"
        "Entirely different words again"
    )

    assert count(fixed) == count(messy)
    assert "did not match" in report or "no part" in report


def test_the_corrected_lyrics_still_read_as_lyrics():
    """
    The result has to survive the app's own reader: one
    syllable per note, which is what read_lyrics checks.
    """

    from music import read_lyrics

    messy = "THERE ONCE WAS A SHIP THAT PUT TO SEA"

    fixed, report = merge_lyrics(
        messy, "There once was a ship that put to sea"
    )

    syllables = read_lyrics(fixed, count(messy))

    assert len(syllables) == count(messy)


def test_the_real_file_is_the_shape_this_was_built_for():
    """
    A structural check on a third-party file, with none of
    its words written down: it carries lyrics in capitals
    with no hyphens anywhere, so nothing in the file can
    say which syllables belong to one word. That is the
    case letter-matching exists for, and the case reading
    hyphens cannot serve.
    """

    import os

    path = os.path.join(
        os.path.dirname(__file__), "fixtures", "midi", "d_FR1924.mid"
    )

    if not os.path.exists(path):
        pytest.skip("the fixture is not present")

    from music import list_midi_tracks, import_midi_file

    (
        pitches, durations, lyrics, bpm,
        feedback, chart, chart_notes, key
    ) = import_midi_file(path, list_midi_tracks(path)[0])

    tokens = lyrics.split()

    sung = len([note for note in pitches.split() if note != "R"])

    assert len(tokens) == sung, "one syllable per sung note"

    assert "-" not in lyrics, "no hyphens to join words by"

    assert lyrics.upper() == lyrics, "shouting"


def test_a_word_lands_on_a_note_the_file_left_empty():
    """
    A file can give a note no word at all, and the import
    writes an underscore there. That looks identical to a
    held note but means the opposite: nothing is being
    held, the word is simply missing.

    Skipping those threw pasted words away in silence,
    which is the worst thing this module can do - a word
    was pasted and vanished with nothing said.
    """

    fixed, report = merge_lyrics(
        "TWIN KLE _ TWIN KLE", "Twinkle up twinkle"
    )

    assert count(fixed) == 5

    assert "up" in fixed.split()
    assert "landed on notes the file left without any" in report


def test_a_held_word_is_still_held():
    """
    The other reading of an underscore: a word sounding
    on, which starts with a real syllable and holds after
    it. Those keep their underscores.
    """

    fixed, report = merge_lyrics(
        "SOON MAY THE WEL LER MAN COME _ _",
        "Soon may the Wellerman come"
    )

    assert count(fixed) == 9
    assert fixed.endswith("come _ _")


def test_no_pasted_word_is_ever_dropped():
    """
    Every word of an accepted line appears in the result.
    A word that cannot be placed is a fault worth failing
    on, not something to leave out quietly.
    """

    fixed, report = merge_lyrics(
        "ONE _ TWO _ THREE _ FOUR",
        "One two three four five six seven"
    )

    written = " ".join(fixed.split()).lower()

    for word in ["one", "two", "three", "four"]:
        assert word in written