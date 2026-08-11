# lyric_merge.py

"""
Correct imported lyrics against the words as written.

A MIDI file's lyrics are whatever the person who
sequenced it typed. Real files arrive shouting in
capitals, with words split at odd places and no hyphen to
say they were split, and with the arranger's name and a
copyright notice sitting in the first few events as
though they were sung. The timing is fine - each syllable
is attached to its note, and the app matched them at
import before anything was respelled - but the words
themselves are a mess.

Pasting the words in fixes that, and only that. The paste
rewrites syllables; it never moves them and never changes
how many there are. One note has one syllable, before and
after, so every word keeps the moment it was sung on.

The decision is made a line at a time and is all or
nothing:

- the syllable count must match exactly, because a
  different count cannot be assigned to the same notes
  without shifting something, and a word landing on the
  wrong note is worse than a word in capitals;
- most of the words must be close, which is what says
  this is the same line rather than a coincidentally
  similar one;
- and then the whole line is replaced, including any one
  word that differs more than the rest. Half-correcting a
  line leaves it worse than either leaving it or fixing
  it.

A line failing either test keeps its original words and
is reported. The result lands in the lyrics box, where
anything wrong is a keystroke from right.

Nothing here is learned. Both sides are already words:
lining up two sequences of them is arithmetic with a
known answer, and how close two spellings are is counted
in characters. A model would guess at what can be
computed.
"""

import re
from difflib import SequenceMatcher


# How close two words must be to count as the same word
# differently spelled. Nought is nothing alike, one is
# identical; tonguing against tonguin' sits near nine
# tenths.
SAME_WORD = 0.75

# And how much of a line must match for the line to be the
# same line. Short words match short words by accident -
# "the" against "thee", "we" against "he" - so a line is
# only accepted when most of it agrees in order.
SAME_LINE = 0.6

# Lines this short are not accepted on similarity alone:
# with two or three words the agreement is as likely to
# be luck as recognition.
ENOUGH_WORDS = 2


def split_syllables(text):
    """
    The syllable tokens of a lyric line, in order.
    """

    return text.split()


def bare(token):
    """
    A syllable with its markings and punctuation removed.

    Comparison is about the letters. The hyphen that says
    a word continues, the underscore that holds one, and
    the apostrophes and commas of ordinary writing all
    tell us nothing about whether two spellings are the
    same word.
    """

    return re.sub(r"[^a-z0-9]", "", token.lower())


def joined_words(syllables):
    """
    The words the syllables spell, and which tokens made
    each one.

    A trailing hyphen means the word continues, so the
    joining is a marker being read rather than a decision
    being made. Underscores hold the word before and add
    no letters.

    Returns a list of (word, [positions]).
    """

    words = []

    building = ""
    positions = []

    for position, token in enumerate(syllables):

        letters = bare(token)

        if token.endswith("_") or token == "_":
            # A held syllable belongs to the word before it
            # and spells nothing of its own.
            if positions:
                positions.append(position)
            continue

        building += letters
        positions.append(position)

        if token.endswith("-"):
            continue

        words.append((building, positions))

        building = ""
        positions = []

    if building or positions:
        words.append((building, positions))

    return words


def closeness(first, second):
    """
    How alike two spellings are, from nought to one.
    """

    if not first and not second:
        return 1.0

    if not first or not second:
        return 0.0

    return SequenceMatcher(None, first, second).ratio()


def syllabify(word, count):
    """
    Split a word into a given number of syllable tokens.

    Not by pronunciation - by letters, evenly, with a
    hyphen after every token but the last. The tokens only
    have to spell the word between them and carry the
    marks the app reads; where exactly a long word is
    divided is a printing convention, and the box is
    editable.

    Asked for one token, the word comes back whole, which
    is the ordinary case.
    """

    if count <= 1:
        return [word]

    if len(word) < count:
        # Nothing sensible to divide. The word goes on the
        # first note and the rest are held, which is what
        # an underscore means.
        return [word] + ["_"] * (count - 1)

    size = len(word) / count

    pieces = []

    for index in range(count):

        start = round(index * size)
        end = round((index + 1) * size)

        pieces.append(word[start:end])

    return [
        piece + "-" for piece in pieces[:-1]
    ] + [pieces[-1]]


def assign_words(tokens, words, most_tokens=6):
    """
    Which syllables of the file spell which pasted word.

    Not by reading the file's hyphens: the files this
    exists for are the ones without them. "TWIN KLE TWIN
    KLE" carries no mark to say those are two words, which
    is exactly why the words have to be pasted in. So the
    letters are matched instead - consecutive syllables
    are gathered until their letters spell the next word.

    Every word takes at least one syllable and every
    syllable belongs to exactly one word, so the count is
    preserved by construction: this decides where the
    boundaries fall, never how many pieces there are.

    Returns (runs, score): a list of token-index lists,
    one per word, and how well the letters agreed overall.
    Runs is None when no assignment is possible, which is
    a line with fewer syllables than words.
    """

    letters = [bare(token) for token in tokens]

    count_words = len(words)
    count_tokens = len(tokens)

    if count_words == 0 or count_tokens < count_words:
        return None, 0.0

    # best[i][j]: the best total score for the first i
    # words using the first j syllables.
    best = [
        [None] * (count_tokens + 1)
        for _ in range(count_words + 1)
    ]

    best[0][0] = (0.0, None)

    for index in range(1, count_words + 1):

        for used in range(index, count_tokens + 1):

            for take in range(1, min(most_tokens, used) + 1):

                previous = best[index - 1][used - take]

                if previous is None:
                    continue

                spelled = "".join(
                    letters[used - take:used]
                )

                score = previous[0] + closeness(
                    spelled, words[index - 1]
                )

                if (
                    best[index][used] is None
                    or score > best[index][used][0]
                ):
                    best[index][used] = (score, take)

    if best[count_words][count_tokens] is None:
        return None, 0.0

    # Walk the choices back out.
    runs = []

    index = count_words
    used = count_tokens

    while index > 0:

        score, take = best[index][used]

        runs.append(list(range(used - take, used)))

        used -= take
        index -= 1

    runs.reverse()

    total = best[count_words][count_tokens][0]

    return runs, total / count_words


def fit_line(original, pasted):
    """
    Rewrite one line's syllables from the pasted words.

    Returns (syllables, matched) - the new tokens and how
    much of the line agreed, or the original tokens and
    the score that failed.

    The number of syllables never changes. The words are
    laid back over the same positions they were sung on.
    """

    tokens = split_syllables(original)

    spoken = [word for word in pasted.split() if bare(word)]

    wanted = [bare(word) for word in spoken]

    if not tokens or not wanted:
        return tokens, 0.0

    runs, matched = assign_words(tokens, wanted)

    if runs is None:
        return tokens, 0.0

    # Two or three words agreeing is as likely to be luck
    # as recognition.
    if len(wanted) < ENOUGH_WORDS or matched < SAME_LINE:
        return tokens, matched

    # The line is the line. Every word in it now comes from
    # the paste, including one that differs more than the
    # rest: a half-corrected line reads worse than either
    # an uncorrected or a corrected one.
    rebuilt = list(tokens)

    for word, run in zip(spoken, runs):

        held = [
            position for position in run
            if tokens[position] == "_"
        ]

        sung = [
            position for position in run
            if position not in held
        ]

        if not sung:
            # Every syllable of this word is a held note,
            # which the file is entitled to say. Leave them.
            continue

        pieces = syllabify(word, len(sung))

        for position, piece in zip(sung, pieces):
            rebuilt[position] = piece

        for position in held:
            rebuilt[position] = "_"

    return rebuilt, matched


def best_window(tokens, wanted, line_starts, most_tries=40):
    """
    The stretch of pasted words this part actually sings.

    Whole lines only, because a paste holding six verses
    of a song the file sings two of should give up verses,
    not halves of them.

    Returns (first_word, last_word) or None.
    """

    if not line_starts:
        return None

    bounds = list(line_starts) + [len(wanted)]

    best = None
    best_score = 0.0

    for index in range(min(len(line_starts), most_tries)):

        first = bounds[index]

        # The most lines from here whose words still fit
        # the notes.
        last = first

        for edge in bounds[index + 1:]:

            if edge - first > len(tokens):
                break

            last = edge

        if last <= first:
            continue

        runs, score = assign_words(tokens, wanted[first:last])

        if runs is not None and score > best_score:
            best = (first, last)
            best_score = score

    if best is None or best_score < SAME_LINE:
        return None

    return best


def merge_lyrics(lyric_text, pasted_text, take_phrasing=True):
    """
    Correct the lyrics box against pasted words.

    The whole part is matched at once, not line by line.
    The two sides do not break in the same places and
    there is no reason they should: the file's line breaks
    fall where a singer breathes, often in the middle of a
    word, while the pasted words break where lyrics are
    written out. Matching line against line forces a word
    split across a breath into whichever line held its
    first syllable, and everything after it drifts.

    So the syllables are matched as one run, letting a
    word span a break, and the breaks are put back
    afterwards - either where the paste puts them, which
    is a human's idea of where the phrases are, or where
    the file had them.

    Acceptance is still granular: each pasted line is
    scored on its own, and a line that did not really
    match keeps the syllables the file had. A verse the
    file does not sing costs that verse, not the song.

    Returns (lyrics, report).
    """

    if not lyric_text or not lyric_text.strip():
        return lyric_text, "There are no lyrics to correct."

    if not pasted_text or not pasted_text.strip():
        return lyric_text, "Paste the words to correct them against."

    tokens = split_syllables(lyric_text)

    # Where the file breaks, as syllable positions, so the
    # phrasing can be put back exactly if it is kept.
    original_breaks = []

    seen = 0

    for line in lyric_text.split("\n")[:-1]:
        seen += len(split_syllables(line))
        original_breaks.append(seen)

    # The pasted words as one run, remembering which word
    # each of its lines starts at.
    words = []
    line_starts = []
    line_of_word = []

    for number, line in enumerate(pasted_text.split("\n")):

        spoken = [word for word in line.split() if bare(word)]

        if not spoken:
            continue

        line_starts.append(len(words))

        for word in spoken:
            words.append(word)
            line_of_word.append(number)

    wanted = [bare(word) for word in words]

    # A tab holds every verse; a file often sings some of
    # them. More words than notes is not a failed paste, it
    # is a paste with more in it than this part sings - so
    # the stretch of it that does fit is found, rather than
    # the whole thing being refused.
    if len(wanted) > len(tokens):

        chosen = best_window(tokens, wanted, line_starts)

        if chosen is None:
            return lyric_text, (
                f"The words hold {len(wanted)} syllables but "
                f"the music has {len(tokens)} notes, and no "
                f"part of the paste fits them. Check that "
                f"these are this part's words."
            )

        first, last = chosen

        words = words[first:last]
        wanted = wanted[first:last]
        line_of_word = line_of_word[first:last]

        line_starts = [
            start - first
            for start in line_starts
            if first <= start < last
        ]

    runs, matched = assign_words(tokens, wanted)

    if runs is None:
        return lyric_text, (
            "The words could not be laid over the notes. "
            "Check that the paste is this part's words."
        )

    # Scored per pasted line, so a verse that is not in the
    # file costs that verse and not the song.
    rebuilt = list(tokens)

    kept = []
    filled = []
    corrected_lines = 0

    for index, start in enumerate(line_starts):

        end = (
            line_starts[index + 1]
            if index + 1 < len(line_starts)
            else len(words)
        )

        scores = [
            closeness(
                "".join(bare(tokens[position]) for position in runs[at]),
                wanted[at]
            )
            for at in range(start, end)
        ]

        if not scores:
            continue

        score = sum(scores) / len(scores)

        if end - start < ENOUGH_WORDS or score < SAME_LINE:
            kept.append(index + 1)
            continue

        corrected_lines += 1

        for at in range(start, end):

            run = runs[at]

            held = [
                position for position in run
                if tokens[position] == "_"
            ]

            sung = [
                position for position in run
                if position not in held
            ]

            if not sung:

                # Every note of this word is an underscore.
                # That can mean two things and they need
                # telling apart: a word genuinely held on -
                # which starts with a syllable and holds
                # after it - or a note the file gave no
                # word to at all. This run has no syllable
                # to hold, so it is the second, and the
                # pasted word belongs on it.
                #
                # Skipping instead threw the word away in
                # silence, which is the worst thing this
                # module can do: a word was pasted and
                # vanished with nothing said.
                rebuilt[run[0]] = words[at]

                for position in run[1:]:
                    rebuilt[position] = "_"

                filled.append(words[at])

                continue

            for position, piece in zip(
                sung, syllabify(words[at], len(sung))
            ):
                rebuilt[position] = piece

            for position in held:
                rebuilt[position] = "_"

    # The breaks. The paste's are a human's idea of where
    # the phrases fall; the file's are wherever the import
    # guessed. Taking the paste's is why pasting is worth
    # doing twice over.
    if take_phrasing and corrected_lines:

        breaks = sorted({
            runs[start][0]
            for start in line_starts[1:]
            if runs[start]
        })

    else:
        breaks = original_breaks

    lines = []
    last = 0

    for position in breaks:

        if position <= last or position > len(rebuilt):
            continue

        lines.append(" ".join(rebuilt[last:position]))
        last = position

    lines.append(" ".join(rebuilt[last:]))

    report = (
        f"Corrected {corrected_lines} of "
        f"{len(line_starts)} lines."
    )

    if take_phrasing and corrected_lines:
        report += (
            f" The phrases now follow the words as pasted "
            f"({len(lines)} of them)."
        )

    if filled:
        report += (
            f" {len(filled)} word"
            f"{'s' if len(filled) != 1 else ''} landed on "
            f"notes the file left without any: "
            f"{', '.join(filled[:6])}"
            f"{'...' if len(filled) > 6 else ''}."
        )

    if kept:
        report += (
            f" Lines {', '.join(str(n) for n in kept)} did "
            f"not match and keep what the file had."
        )

    return "\n".join(lines), report