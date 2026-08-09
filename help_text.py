# help_text.py

"""
What the app says about itself to someone new.

Kept apart from the interface so that the words can be
read, corrected and tested on their own, and so main.py
stays a description of which control is wired to what.
"""

from notes import REST
from harmony import MAJOR_SCALES


HELP_TEXT = f"""
## What this does

You give it a line of music. It plays the line, records
you singing it, and shows you what you sang against what
was written: which notes you hit, how far off you were in
cents, and where you came in early or late.

## Getting started

Press **Load Twinkle Phrase**, then **Generate Playback**
to hear it. Press record, sing along with the count-in,
then press **Compare** to see how it went.

## Writing music by hand

Three boxes describe the music, one entry per note.

**Pitches** are note names with an octave: `C4` is middle
C, `F#4` and `Bb3` are the black notes, and `{REST}` is a
rest, which is silence you can breathe in.

**Durations** are lengths in beats, written as fractions:

    1      a beat
    1/2    half a beat
    1/4    a quarter of a beat
    3/2    a dotted beat
    1/3    one note of a triplet

Dotted notes are always three over something, because a
dot adds half again. Decimals work too if you prefer them.

**Lyrics** are one syllable per note, separated by spaces.
A syllable that continues a word ends in a hyphen, as in
`Twin- kle`. A word held across several notes is written
once, with `_` under the notes that carry it on. Rests
take no syllable.

## Bringing in a MIDI file

Drop a file in and the boxes fill themselves. If the file
has several tracks, a dropdown lets you choose which part
to sing: a choral file will have one track per voice, and
often a piano reduction as well.

A whole piece is more than anyone practises at once, so
it arrives divided into phrases of about eight seconds,
broken where the music rests. Pick one from the dropdown.

Anything the import fills in can be edited by hand
afterwards. The boxes are the music; the file is only how
it got there.

## Chords

The **Chords** box is optional, and written in bars of
beats:

    | Dm .  Bb . | F  .  .  . |
    | Dm .  .    | F  .  .    |

Each token is one beat and a dot holds the chord on, so
the first line is two bars of four with a chord change
halfway through the first. The bars set the metre
themselves: three slots to a bar is three four.

Importing a file fills the chart in for you, read from
every voice sounding together.

**Suggest chords** fills it for any music in the boxes.
Where several voices are sounding it reads what the
harmony actually is. Where there is only a melody it
suggests what would fit, which is a weaker answer worth
having: a tune does not state its harmony, but the notes
on the strong beats narrow it, and the key offers only
seven chords to choose between. Either way the chart is
yours to edit.

Switch **Chords** on in the playback section to hear the
chart strummed underneath, voiced below the melody so it
supports the line rather than covering it. A chord sounds
when it arrives and again on each bar line it lasts
through, so the harmony stays present under a long note.

The chart has to last as long as the music, but it does
not have to line up with it note for note. A chord covers
many notes, and a syncopated melody crosses the bar lines
freely.

## Keys and harmony

**Detect key** reads the notes and tells you what key they
sound like, with the runners up and how close they are.
Short melodies often genuinely fit several keys, so it
names more than one rather than guessing.

The key you choose is used to build the harmony line.
Each of the {len(MAJOR_SCALES)} settings is named twice,
as in `F major / D minor`, because a key signature belongs
to both equally: a piece in D minor uses the notes of F
major. A note outside the chosen key is still harmonised,
at the nearest note in the scale.

## Singing

**Part** is the line you are performing: melody, harmony
or bass. The bass sings the root of each chord and holds
it while the tune moves, so it needs a chord chart. It decides both what the guide plays and what
your recording is judged against, so a harmony singer is
not marked wrong for singing the harmony.

**Guide while recording** is what you hear as you sing.
*The other part* plays the opposite line, which is how
harmony is usually practised: the melody in your ears and
your own line in your voice.

Every recording begins with four counted-in beats.

## Reading the result

The **piano roll** shows the written notes as boxes and
your singing as a line through them. A note begun below
and slid up to appears as exactly that. Gaps in the line
are breaths and consonants, not mistakes.

The **tuning chart** shows how far each note was from
where it should be, in cents. A hundred cents is a
semitone; within fifteen counts as in tune.

If you sang in a different octave from the written music,
choose it under **Octave** and the comparison follows you
there.

## When something looks wrong

Notes reported an octave below what you sang usually mean
the microphone is losing the bottom of your voice, which
laptop and webcam microphones do. Brief spikes at the ends
of notes are the detector being confused by consonants,
not by you.
"""