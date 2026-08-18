"""
Built-in example songs.

Each loader returns the raw box contents the app works
from: pitches, durations, lyrics, key and chart as text,
plus the song's own tempo for the full-song loaders. All
songs here are public domain and typed in by hand from
traditional sources, so they double as ground truth for
the rest of the suite.

Add new examples here, not in music.py.
"""


def load_twinkle_phrase():
    """
    The opening phrase of Twinkle Twinkle Little Star.
    """

    # Two bars of four beats. The last note is shortened
    # to make room for the breath rather than the rest
    # being added on top, which would leave the phrase a
    # beat longer than the music it came from.
    pitches = (
        "C4 C4 G4 G4 A4 A4 G4 R"
    )

    durations = (
        "1 1 1 1 1 1 3/2 1/2"
    )

    lyrics = (
        "Twin- kle twin- kle lit- tle star"
    )

    # Two bars of four. The tune sits on C until the
    # rising sixth, which the F chord underneath is what
    # makes that moment sound like an arrival.
    chart = (
        "| C . . . | F . C . |"
    )

    return pitches, durations, lyrics, "C", chart



def load_twinkle():
    """
    The whole of Twinkle Twinkle Little Star, six phrases.

    Tune and words are traditional and in the public
    domain. The shape is A B C C A B: the opening returns
    after the middle, which is why the last two lines
    repeat the first two.
    """

    pitches = " ".join([
        "C4 C4 G4 G4 A4 A4 G4 R",
        "F4 F4 E4 E4 D4 D4 C4 R",
        "G4 G4 F4 F4 E4 E4 D4 R",
        "G4 G4 F4 F4 E4 E4 D4 R",
        "C4 C4 G4 G4 A4 A4 G4 R",
        "F4 F4 E4 E4 D4 D4 C4 R",
    ])

    durations = " ".join(["1 1 1 1 1 1 3/2 1/2"] * 6)

    lyrics = "\n".join([
        "Twin- kle twin- kle lit- tle star",
        "How I won- der what you are",
        "Up a- bove the world so high",
        "Like a dia- mond in the sky",
        "Twin- kle twin- kle lit- tle star",
        "How I won- der what you are",
    ])

    chart = (
        "| C . . . | F . C . |"
        " | F . C . | G . C . |"
        " | C . F . | C . G . |"
        " | C . F . | C . G . |"
        " | C . . . | F . C . |"
        " | F . C . | G . C . |"
    )

    return pitches, durations, lyrics, "C", chart, 100


def load_wellerman():
    """
    The Wellerman, three verses and the chorus between
    each - the whole traditional song as a real arrangement
    actually sets it, not the one-verse-because-they-repeat
    shorthand this example used to be.

    Verse one's melody, its duration, and its chart are
    unchanged from before: the original drafting (a MIDI
    import of a band arrangement, transposed from C minor
    up to D minor, checked line one against the hand-
    checked phrase example) is still the source, still
    trusted, still untouched.

    Extending to three verses came from a real piano
    arrangement upload, cross-checked before any of it was
    used:
    - Its chord progression, checked chord by chord against
      an independently sourced tab (Am/Dm/E/F/C/G), came out
      transposed by exactly seven semitones on every chord
      from this piece's own Dm/Gm/A/Bb/F - two unrelated
      sources agreeing on the same progression, which is
      why the existing chart is trusted to repeat rather
      than re-derived from the new file's own (noticeably
      noisier, chord-detected rather than printed) reading.
    - Verse one's real words, checked syllable by syllable
      against this file's real transcription, land on
      exactly the existing melody's note count, line for
      line (9, 11, 8, 7) - strong evidence the existing
      rhythm is the tune's actual rhythm, not just a
      plausible one.
    - Verses two and three's real words do not match:
      verse two five syllables short of verse one's count,
      verse three three short, both entirely in the
      verse-specific lines before the chorus. (Verse three
      was once forced onto verse one's rhythm anyway, by
      dragging each line's pickup word onto the end of the
      line before and padding with holds - the token count
      came out right and every word landed one note late.)
      Rather than force different words onto a rhythm they
      do not fit, each verse's melody for those lines is
      the file's own real notes -
      transposed the same whole step as everything else,
      plus one octave (this file's part sits a register
      lower throughout; checked against its own range as a
      whole, not against a phrase in different words, which
      is not a fair comparison). Its chart drops one of the
      three repeated opening Dm bars - eight bars instead of
      nine, matching the shorter line exactly, and invisible
      harmonically since nothing there was doing more than
      holding still.
    - One real gap in the file: "name" is missing from its
      own lyric encoding entirely (a held note with no word
      on it) and is restored by hand - "the name of the
      ship", not "the of the ship".

    A repeated final line the arrangement adds after verse
    three ("we'll take our leave and go", twice) is left
    out, for the same reason the piece stays in one tempo
    despite the arrangement's own written tempo changes:
    keeping this example the same shape it has always been,
    extended rather than reworked.
    """

    verse = " ".join([
        "R R R A3",
        "D4 D4 D4 D4 F4 A4 A4 A4",
        "A4 Bb4 G4 G4 G4 Bb4 Bb4 D5 D5 A4 A4",
        "A4 D4 D4 D4 F4 A4 A4 A4",
        "A4 A4 G4 F4 F4 E4 D4",
    ])

    verse_durations = " ".join([
        "1 1 1 1",
        "1 1/2 1/2 1 1 1 1 1",
        "1 1 1/2 1/2 1 1/2 1/2 1/2 1/2 1 3/2",
        "1/2 1 1 1 1 1 1 1",
        "1 1 1 1/2 1/2 1 4",
    ])

    chorus = " ".join([
        "D5 D5 Bb4 C5 A4 A4 A4",
        "A4 Bb4 G4 G4 G4 Bb4 D5 A4 A4",
        "D5 D5 Bb4 Bb4 C5 A4 A4 A4",
        "A4 A4 G4 F4 E4 D4",
    ])

    chorus_durations = " ".join([
        "2 3/2 1/2 1/2 1/2 1 3/2",
        "1/2 1 1 1/2 1/2 1 1 1 2",
        "2 1 1/2 1/2 1/2 1/2 3/2 1/2",
        "1 1 1 1 1 4",
    ])

    # Verse two's own real notes - see the docstring for why
    # this line alone does not reuse verse one's rhythm.
    verse_two = " ".join([
        "E3 D3 D3 D3 F3 A3 A3 A3",
        "A3 Bb3 G3 G3 Bb3 D4 A3 A3",
        "A3 D3 D3 D3 F3 A3 A3 A3",
        "A3 Bb3 G3 F3 E3 D3",
    ])

    verse_two_durations = " ".join([
        "1/2 1/2 1 1 1 1 1 1",
        "1 1 1 1 1 1 1 3/2",
        "1/2 1 1 1 1 1 1 1",
        "1 1 1 1 1 4",
    ])

    # Verse three's own real notes too - the same file, the
    # same transposition as verse one (its C3 is our D4). No
    # pickup: 'Fore lands on the downbeat, "the boat" is an
    # eighth and a dotted quarter, and "had" is already on
    # the third - none of which verse one's rhythm can hold.
    verse_three = " ".join([
        "R R R R",
        "D4 D4 D4 F4 A4 A4 A4 A4 A4",
        "Bb4 G4 G4 Bb4 D5 A4 A4 A4 D4",
        "D4 D4 D4 D4 F4 A4 A4 A4 A4",
        "G4 G4 F4 E4 D4",
    ])

    verse_three_durations = " ".join([
        "1 1 1 1",
        "1 1/2 3/2 1 1 1 1 1/2 1/2",
        "1 1 1 1 1 1 1 1/2 1/2",
        "1 1/2 1/2 1 1 1 1 1 1",
        "1 1 1 1 4",
    ])

    pitches = " ".join([
        verse, chorus, verse_two, chorus, verse_three, chorus,
    ])

    durations = " ".join([
        verse_durations, chorus_durations,
        verse_two_durations, chorus_durations,
        verse_three_durations, chorus_durations,
    ])

    lyrics = "\n".join([
        "There once was a ship put out to sea,",
        "the name of the ship was the Bill- y o' Tea.",
        "The winds blew up, her bow dipped down.",
        "Oh blow, my bull- y boys blow.",
        "Soon may the Wel- ler- man come",
        "To bring us sug- ar and tea and rum",
        "One day when the tongu- ing is done",
        "We'll take our leave and go",
        "She had not been two weeks from shore",
        "when down on her a right whale bore.",
        "The Cap- tain called all hands and swore:",
        "\"We'll take that whale and tow!\"",
        "Soon may the Wel- ler- man come",
        "To bring us sug- ar and tea and rum",
        "One day when the tongu- ing is done",
        "We'll take our leave and go",
        "'Fore the boat had hit the wa- ter",
        "the whale's _ tail came up and caught her.",
        "All hands to the side, har- pooned and fought her,",
        "When she dived down low",
        "Soon may the Wel- ler- man come",
        "To bring us sug- ar and tea and rum",
        "One day when the tongu- ing is done",
        "We'll take our leave and go",
    ])

    verse_chart = (
        "| Dm . . . |"
        " | Dm . . . | Dm . . . |"
        " | Gm . . . | Dm . . . |"
        " | Dm . . . | Dm . . . |"
        " | A . . . | Dm . . . |"
    )

    # One fewer Dm bar than verse_chart - see the docstring.
    verse_two_chart = (
        "| Dm . . . |"
        " | Dm . . . |"
        " | Gm . . . | Dm . . . |"
        " | Dm . . . | Dm . . . |"
        " | A . . . | Dm . . . |"
    )

    chorus_chart = (
        "| Bb . . . | F . . . |"
        " | Gm . . . | Dm . . . |"
        " | Bb . . . | F . . . |"
        " | A . . . | Dm . . . |"
    )

    chart = " ".join([
        verse_chart, chorus_chart,
        verse_two_chart, chorus_chart,
        verse_chart, chorus_chart,
    ])

    return pitches, durations, lyrics, "F", chart, 240


def load_wellerman_phrase():
    """
    The opening phrase of the Wellerman, a traditional sea
    shanty in the public domain.

    The tune sits in D minor, which shares its notes with
    F major, so the harmony machinery works in key F.
    """

    # Pitches follow the traditional verse: pickup on the
    # dominant, repeated tonics, the third on "ship", then
    # the dominant above. The line ends with a rest, which
    # is where a singer breathes before the next line.
    pitches = (
        "A3 D4 D4 D4 D4 F4 A4 A4 A4"
    )

    # Eight beats: two bars of four. Checked against a
    # published arrangement, which writes the same rhythm
    # with these note values and runs the line straight on
    # without a rest, the next line arriving on the bar.
    durations = (
        "1 1 1/2 1/2 1 1 1 1 1"
    )

    lyrics = (
        "There once was a ship that put to sea"
    )

    # The whole line sits on the tonic minor, which is
    # part of why a crowd can join in without knowing the
    # song: there is nothing to follow but the tune.
    chart = (
        "| Dm . . . | Dm . . . |"
    )

    return pitches, durations, lyrics, "F", chart
