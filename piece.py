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
"""


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
        self.key = key
        self.chart = chart or ""

        # What the file or the example says it goes at,
        # which the player is free to ignore.
        self.tempo = tempo

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
        """

        from music import read_music, read_lyrics, read_chords

        pitches, durations = read_music(pitch_text, duration_text)

        piece = Piece(
            pitches, durations, None, key, chart_text, tempo
        )

        # Checked against the notes, and kept as written so
        # that the line breaks in it survive: they are what
        # says where the phrases fall.
        read_lyrics(lyric_text, piece.sung())

        piece.lyrics = lyric_text or None

        read_chords(chart_text, durations)

        return piece

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

    def slice(self, first, last):
        """
        The stretch from one note to another, as a piece.

        Everything comes with it: the lyrics for those
        notes, and the chords sounding under them, cut in
        beats rather than in notes because a chart is
        written in bars and the melody is not.

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
            self.key,
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
        """

        if not self.chart.strip():
            return ""

        from chords import read_chart, ChartError

        try:
            chords, bars = read_chart(self.chart)

        except ChartError:
            return ""

        if not chords:
            return ""

        length = int(round(closed - opened))

        if length <= 0:
            return ""

        beats_per_bar = 4

        if bars:
            beats_per_bar = int(round(bars[0][1])) or 4

        # What is sounding on each beat of the slice.
        sounding = []

        for beat in range(length):

            at = opened + beat

            found = None

            for start, chord_length, name in chords:

                if start <= at < start + chord_length:
                    found = name
                    break

            sounding.append(found)

        # Named where it changes, a dot where it carries
        # on. The first beat always names its chord, even
        # if the slice began in the middle of one: a phrase
        # starting halfway through a bar of D minor is
        # still in D minor.
        tokens = []

        previous = None

        for beat in range(length):

            name = sounding[beat]

            if name is None:
                tokens.append("." if tokens else "")

            elif beat == 0 or name != previous:
                tokens.append(name)

            else:
                tokens.append(".")

            previous = name

        if not tokens or not tokens[0]:
            return ""

        lines = []

        for position in range(0, len(tokens), beats_per_bar):

            lines.append(
                " ".join(tokens[position:position + beats_per_bar])
            )

        return "| " + " | ".join(lines) + " |"

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
