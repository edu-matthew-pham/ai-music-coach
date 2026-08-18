# piece.py

"""
A piece of music, in one object.

The app grew out of three text boxes, and for a long time
that was all the music there was: functions parsed the
boxes each time they needed them. Every feature since -
rests, lyrics, keys, chords, several parts - has added
another argument to those functions rather than another
field to anything, because there was nothing to add a
field to. That is why comparing a performance now takes
ten arguments, and why adding one to the wrong half of
the call sites is the mistake this codebase keeps making.

This is the thing to add fields to.

Two ideas kept separate here, having been muddled before:

The tempo of the song is part of the song, as a marking on
a score is. The tempo you are singing at today is not: you
slow a piece down to learn a harmony line, and the piece
is unchanged. So a piece carries the tempo it was written
or imported at, and what the player sets is theirs.

Likewise the piece is what the music is, not what anyone
wants done with it. Which part you are singing, which
harmony style, whether the metronome is on - none of those
belong here, however often they travel alongside.

A Piece is still one tune. Several tunes sung together
(PLAN-multi-part.md) are written as sections in the same
three boxes, divided by a "=== name ===" line; Piece.read
never sees more than one tune at a time, unchanged from
before this existed. read_parts is the boundary that
splits the boxes and hands each section to Piece.read in
turn - a box with no divider is one section, so nothing
about this changes what a single-tune song does.
"""

import re

PART_HEADER = re.compile(r"^[ \t]*===[ \t]*(.+?)[ \t]*===[ \t]*$", re.MULTILINE)


def _split_box(text):
    """
    One box's text, cut into (name, body) sections by
    "=== name ===" divider lines.

    No divider found: one section, name None, body is the
    whole text - exactly what every box has always held.
    """

    text = text or ""

    matches = list(PART_HEADER.finditer(text))

    if not matches:
        return [(None, text)]

    sections = []

    for index, match in enumerate(matches):

        start = match.end()
        end = (
            matches[index + 1].start()
            if index + 1 < len(matches) else len(text)
        )

        # Only the newline right after the header and right
        # before the next one is trimmed - a body's own
        # internal blank lines (lyric phrase breaks) are
        # left exactly as written.
        sections.append((match.group(1), text[start:end].strip("\n")))

    return sections


def split_parts(pitch_text, duration_text, lyric_text=""):
    """
    The pitch, duration and lyric boxes, cut into tunes.

    Returns a list of (name, pitch_text, duration_text,
    lyric_text) tuples, in the order written. The pitch and
    duration boxes must agree on how many tunes there are
    and what each is called, in the same order - a piece
    only has one true division into parts, and the two
    boxes are both describing it. The lyric box may divide
    the same way, or may carry no divider at all (a piece
    with no lyrics, or - only when there is a single tune -
    one tune's plain lyric line, exactly as before this
    existed).

    No divider anywhere: one tune, name None. This is every
    song the app has ever had, and this is the path all of
    them still take.
    """

    from music import MusicInputError

    pitch_sections = _split_box(pitch_text)
    duration_sections = _split_box(duration_text)

    pitch_names = [name for name, _ in pitch_sections]
    duration_names = [name for name, _ in duration_sections]

    if pitch_names != duration_names:
        raise MusicInputError(
            "The pitch and duration boxes divide into "
            "different parts - make the \"=== name ===\" "
            "lines match, in the same order, in both."
        )

    lyric_sections = _split_box(lyric_text)
    lyric_names = [name for name, _ in lyric_sections]

    if lyric_names == [None]:
        # No divider in the lyric box at all. Fine as-is
        # when there is only one tune (today's shape,
        # unchanged); ambiguous for several, since there
        # would be no way to say which tune the words
        # belong to.
        if len(pitch_sections) == 1:
            lyric_sections = [(None, lyric_text or "")]

        elif (lyric_text or "").strip():
            raise MusicInputError(
                "This piece has several parts, so the "
                "lyrics need their own \"=== name ===\" "
                "lines too, matching the pitch box - or "
                "leave the lyrics box empty."
            )

        else:
            lyric_sections = [
                (name, "") for name in pitch_names
            ]

    elif lyric_names != pitch_names:
        raise MusicInputError(
            "The lyric box's parts don't match the pitch "
            "box's - make the \"=== name ===\" lines the "
            "same, in the same order, in both."
        )

    return [
        (name, p_text, d_text, l_text)
        for (name, p_text), (_, d_text), (_, l_text)
        in zip(pitch_sections, duration_sections, lyric_sections)
    ]


class Piece:
    """
    Pitches, durations, and everything that goes with them.

    Durations are in beats, so nothing here depends on how
    fast it is played, which is what lets a piece be sliced,
    harmonised and charted without a tempo in sight.
    """

    def __init__(
        self,
        pitches,
        durations,
        lyrics=None,
        key="C",
        chart="",
        tempo=None
    ):
        self.pitches = list(pitches)
        self.durations = list(durations)
        self.lyrics = lyrics
        self.chart = chart or ""

        # The key is never stored as a bare string: `key`
        # holds the timeline, and .key is a view onto its
        # first entry, always - not a second fact that could
        # be constructed to disagree with it. A plain string
        # ("G") is accepted here and wrapped into a one-entry
        # timeline, so every existing call site keeps working
        # unchanged; an already-parsed timeline (a list of
        # (beat, name) pairs) is accepted as-is, for callers
        # that already have one - Piece.read among them.
        if isinstance(key, str):
            self.key_changes = [(0.0, key)]

        else:
            self.key_changes = list(key)

        # What the file or the example says it goes at,
        # which the player is free to ignore.
        self.tempo = tempo

    @property
    def key(self):
        """
        The opening key, as every caller has always read it.

        Always the timeline's own first entry - never a
        separate value that construction could leave out of
        step with it. A piece that never changes key (every
        piece before this format existed, and most pieces
        after) has a one-entry timeline, so this is exactly
        what it always was: the one key the piece is in.
        """

        return self.key_changes[0][1]

    def key_at(self, beat):
        """
        Which key is in force at a given beat.

        The same shape as chord_at: walks the timeline,
        returns whichever key was most recently in force.
        A single-key piece returns that one key for every
        beat, since its timeline only ever has one entry -
        this is not a special case, it is what the general
        walk already does with one entry.
        """

        from harmony import key_at

        return key_at(self.key_changes, beat)

    @staticmethod
    def read(pitch_text, duration_text, lyric_text="",
             key="C", chart_text="", tempo=None):
        """
        Read a piece out of the text boxes.

        Parsed once, here, instead of separately in every
        function that needs the music. The checking is the
        same checking as before and reports the same
        errors, since those are what tell a player what
        they have mistyped.

        `key` is the key box's own raw text - "G", or "G,
        Ab from beat 156" for a piece that genuinely
        modulates - read here the same way chart_text and
        lyric_text are: once, at the boundary, into the
        shape the rest of the piece actually uses.
        """

        from music import read_music, read_lyrics, read_chords
        from harmony import read_key

        pitches, durations = read_music(pitch_text, duration_text)

        piece = Piece(
            pitches, durations, None, read_key(key),
            chart_text, tempo
        )

        # Checked against the notes, and kept as written so
        # that the line breaks in it survive: they are what
        # says where the phrases fall.
        read_lyrics(lyric_text, piece.sung())

        piece.lyrics = lyric_text or None

        read_chords(chart_text, durations)

        return piece

    @staticmethod
    def read_parts(pitch_text, duration_text, lyric_text="",
                    key="C", chart_text="", tempo=None):
        """
        Read one or several tunes out of the text boxes.

        Returns a list of (name, Piece) pairs, in the order
        written - a single, undivided piece (the only kind
        that existed before several-tune songs did) comes
        back as one pair, name None, and that Piece is
        exactly what Piece.read already returns for the
        same boxes: this function's only new work is
        splitting the boxes first, in split_parts.

        Key, chart and tempo are shared across every tune,
        by design - a round has one chart, not several.
        """

        sections = split_parts(pitch_text, duration_text, lyric_text)

        return [
            (
                name,
                Piece.read(
                    p_text, d_text, l_text, key, chart_text, tempo
                )
            )
            for name, p_text, d_text, l_text in sections
        ]

    def phrases(self):
        """
        The piece divided into phrases, one per line of the
        lyrics.
        """

        from music import phrases_from_lyrics

        return phrases_from_lyrics(
            self.pitches, self.durations, self.lyrics or ""
        )

    def phrase(self, number):
        """
        One phrase of the piece, as a piece.
        """

        found = self.phrases()

        if not found:
            return self

        if number < 0 or number >= len(found):
            from music import MusicInputError

            raise MusicInputError(
                f"There are {len(found)} phrases in this "
                f"music, so there is no phrase "
                f"{number + 1}."
            )

        first, last = found[number]

        return self.slice(first, last)

    def __len__(self):
        return len(self.pitches)

    def __repr__(self):
        return (
            f"Piece({len(self.pitches)} notes, "
            f"{self.beats():g} beats, key {self.key})"
        )

    def beats(self):
        """
        How long the piece lasts, in beats.
        """

        return sum(self.durations)

    def seconds(self, bpm):
        """
        How long it lasts at a given tempo.
        """

        return self.beats() * 60 / bpm

    def sung(self):
        """
        How many notes are actually sung, rests aside.
        """

        from notes import is_rest

        return len([
            pitch for pitch in self.pitches
            if not is_rest(pitch)
        ])

    def starts(self):
        """
        Where each note begins, in beats from the start.
        """

        beat = 0.0

        found = []

        for length in self.durations:
            found.append(beat)
            beat += length

        return found

    def key_between(self, opened, closed):
        """
        The keys in force over a stretch, windowed and
        rebased to start at 0 - the same shape
        chart_between already gives the chart, for the same
        reason: a phrase beginning after a key change is
        still in that key, not the whole piece's opening
        one. A phrase straddling the change keeps both, at
        their own beat relative to the phrase's own start.
        """

        changes = []

        active = self.key_changes[0][1]

        for beat, name in self.key_changes:

            if beat >= closed:
                break

            if beat <= opened:
                active = name
                continue

            changes.append((beat - opened, name))

        return [(0.0, active)] + changes

    def slice(self, first, last):
        """
        The stretch from one note to another, as a piece.

        Everything comes with it: the lyrics for those
        notes, the chords sounding under them (cut in
        beats rather than in notes because a chart is
        written in bars and the melody is not), and
        whichever key was actually in force - a phrase
        starting after a modulation is still in the new
        key, not the piece's opening one.

        This is the conversion the rest of the app kept
        getting wrong by doing it in several places at
        once, so it is done here and only here.
        """

        first = max(0, first)
        last = min(len(self.pitches) - 1, last)

        if last < first:
            return Piece([], [], None, self.key, "", self.tempo)

        starts = self.starts()

        opened = starts[first]

        closed = starts[last] + self.durations[last]

        return Piece(
            self.pitches[first:last + 1],
            self.durations[first:last + 1],
            self.lyrics_between(first, last),
            self.key_between(opened, closed),
            self.chart_between(opened, closed),
            self.tempo
        )

    def lyrics_between(self, first, last):
        """
        The syllables belonging to a stretch of notes.

        Syllables are counted against sung notes, so the
        rests in between have to be discounted before the
        words can be found.
        """

        if not self.lyrics:
            return self.lyrics

        from notes import is_rest

        syllables = self.lyrics.split()

        before = len([
            pitch for pitch in self.pitches[:first]
            if not is_rest(pitch)
        ])

        within = len([
            pitch for pitch in self.pitches[first:last + 1]
            if not is_rest(pitch)
        ])

        return " ".join(syllables[before:before + within])

    def chart_between(self, opened, closed):
        """
        The chords sounding over a stretch of time.

        Written out again as a chart, with the first chord
        reaching back to the start of the slice: a phrase
        beginning in the middle of a bar of D minor is
        still in D minor.

        Every chord (including a half-beat split, "A>B") is
        clipped to the window and re-based to start at the
        slice's own beat 0, then handed to write_chart -
        the same function a detected chart is written with,
        so a slice does not need its own parallel token-
        building logic. A chord already sounding when the
        slice opens is clipped to start exactly at 0, which
        is what lets write_chart name it there rather than
        writing a leading dot.

        One disclosed edge case: write_chart only recognises
        an EXACT half-beat start as a genuine split. Slicing
        re-bases every chord's start relative to `opened`,
        so a split chord whose true position survives the
        rebasing only if `opened` itself sits on a whole or
        half beat of the original chart. A phrase opening on
        some other fraction (rare - most phrases start on a
        beat or a clean pickup) would floor a split chord
        inside it to the nearest whole beat, the same
        graceful fallback a chart with no split information
        at all already gets.
        """

        if not self.chart.strip():
            return ""

        from chord_detector import write_chart
        from chords import read_chart, ChartError

        try:
            chords, bars = read_chart(self.chart)

        except ChartError:
            return ""

        if not chords:
            return ""

        # Rounded up, since a chart has to cover the music
        # it sits over and is written in whole beats.
        import math

        length = int(math.ceil(closed - opened - 0.01))

        if length <= 0:
            return ""

        beats_per_bar = 4

        if bars:
            beats_per_bar = int(round(bars[0][1])) or 4

        windowed = []

        for start, chord_length, name in chords:

            clipped_start = max(start, opened)
            clipped_end = min(start + chord_length, opened + length)

            if clipped_end <= clipped_start:
                continue

            windowed.append((
                clipped_start - opened,
                clipped_end - clipped_start,
                name
            ))

        if not windowed:
            return ""

        return write_chart(windowed, length, beats_per_bar)

    def chord_at(self, beat):
        """
        The chord sounding at a moment, or None.
        """

        if not self.chart.strip():
            return None

        from chords import read_chart, chord_at, ChartError

        try:
            chords, bars = read_chart(self.chart)

        except ChartError:
            return None

        return chord_at(chords, beat)