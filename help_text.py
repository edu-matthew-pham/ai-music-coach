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

You give it a line of music. It plays the line and draws
your singing as a live pitch line over the written notes,
so you can see where you are landing on the tune and where
you are drifting off it, as you sing.

## Getting started

Press **Load Twinkle**, then **Generate Playback** to hear
it. Tick **Mic** and allow the microphone when the browser
asks; sing along, and your pitch draws over the notes as
you go.

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

## Songs with several parts

A song can carry more than one tune sung at once - a
partner song, a round, a duet with an answering line.
Write each tune one after another in the pitch, length
and lyric boxes, with a divider line between them, the
same names in the same order in all three:

    === Three Blind Mice ===
    E4 D4 C4 ...
    === Frere Jacques ===
    C4 D4 E4 ...

A part that comes in late, or drops out early, is written
with bars of rest where it is silent; the parts do not
have to be the same length. Key, chords and tempo are
shared - a round has one chart. The buttons
**Load Frere Jacques / 3BM** and **Load Row Your Boat**
are both written this way, and a song without dividers is
one tune, exactly as before.

## Bringing in a file

Drop a MIDI or MusicXML file in and the boxes fill
themselves. If the file has several tracks, a dropdown
lets you choose which part to sing: a choral file will
have one track per voice, and often a piano reduction as
well.

A MusicXML score with several sung parts lands with all
of them together, written out with dividers as above, and
you pick which is yours in the mixer. Two voices sharing
one staff arrive as "Voice 1" and "Voice 2"; several sung
staves arrive under their own names. The dropdown still
offers each part alone if you want only one.

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

A chord that arrives on the "and" of a beat rather than
squarely on it - a strummed, syncopated push - writes as
two chords sharing one beat's slot, split by a `>`:
`D>G` means D for the first half of the beat, G for the
second. Leaving the first half off, `>G`, means the chord
already sounding just carries through the first half and
G is the only new arrival. A beat can only split in two -
into halves, not further.

Importing a file fills the chart in for you, read from
every voice sounding together. A score's own printed
chord symbols keep their half-beat timing where they have
it; a chord detected from the notes only ever lands on
the beat, since it is a best guess rather than something
stated.

**Suggest chords** fills it for any music in the boxes.
Where several voices are sounding it reads what the
harmony actually is. Where there is only a melody it
suggests what would fit, which is a weaker answer worth
having: a tune does not state its harmony, but the notes
on the strong beats narrow it, and the key offers only
seven chords to choose between. Either way the chart is
yours to edit.

Switch **Chords** on in Playback to hear the chart
strummed underneath, voiced below the melody so it
supports the line rather than covering it. A chord sounds
when it arrives and again on each bar line it lasts
through, so the harmony stays present under a long note.

The chart has to last as long as the music, but it does
not have to line up with it note for note. A chord covers
many notes, and a syncopated melody crosses the bar lines
freely.

## Playback

Press **Generate Playback** to build the mixer for
whatever is in the boxes right now, for the whole piece.
Six layers - Melody, Harmony above, Harmony below, Bass,
Chords, Metronome - each with its own level, mixed live in
the browser so moving a fader changes only loudness rather
than remaking anything. Edit the boxes and press the
button again to rebuild.

A song with several parts shows a **Singing** row above
the strip, one button per tune. Every tune is already
loaded and playing, so clicking one rebuilds nothing - it
only changes whose words show and whose line your pitch
draws against. **Show all parts** puts every tune's words side
by side. Rebuilding with Generate Playback keeps the part
you chose; loading a different song starts you on its
first part.

Click a bar on the chord strip to jump there. Shift-click
a second bar to loop that stretch, and **Repeat** decides
whether the loop plays once and stops or keeps going
round. The phrase list above the strip works the same way:
click a phrase to jump straight to its own exact start and
end (not always the same as the bar it falls in) and start
playing it, and shift-click a second phrase to loop that
whole stretch instead - a bar click and a phrase click can
extend the same selection between them. The phrase
currently playing shows in green.

**Notes** and **Lyrics** are their own toggles, and can
both be on together. Notes draws the written pitches for
the current phrase, one voice shown by default; Lyrics
shows the words, either as pills that light up one at a
time or a line of text coloured as it is sung.

**Instruments** draws the key on a piano, a guitar, a
ukulele, or a violin chart. Each has its own size toggle
once it's ticked on - piano between two and three octaves,
guitar between a compact eight frets and the full thirteen,
ukulele between six and ten (its own shapes stay lower on
the neck than guitar's, and its short scale makes a player
less likely to go far up it at all). Violin's toggle is
between first position alone and both positions together:
the full view adds first position's marks in one colour and
third position's in another, with a two-colour mark
wherever a note is reachable from both - a genuinely
different picture, not just a longer one. Guitar and
ukulele's shape mode does the same in their own full view,
showing the standard shape at both hand positions at once. A
shape needing more room than the compact view gives it still
draws at its real position, which can land past the edge of
a short neck; widening the view is the fix, not something
done automatically. The
instrument itself is always shown; **Scale**, **Chord notes**
and **Chord shape** are three independent layers on top of it,
any combination at once, with Chord shape on to start with.
Chord notes marks every place the current chord occurs;
Chord shape marks one beginner voicing instead - a standard
open or barre shape on guitar or ukulele (the two have
genuinely different shapes for the same chord, since the
tuning itself differs, not just the range), a root-and-fifth
left hand against a triad right hand on piano, a double stop
on two adjacent open or low strings on violin - each in its
own colour so the two chord layers stay readable together.
Showing both is useful in its own right: the shape gives a
fixed place to start, and the notes show everywhere else the
same chord tones fall, for an arpeggio or a right-hand
accompaniment that moves beyond the shape itself. A barre
chord is drawn as a barre, not simplified away: the
difficulty is real, and seeing it is part of learning it.
Violin's shape only exists in first position - a double stop
is a low, beginner shape, not something to teach further up
the neck - and ukulele's shape is only covered for the seven
natural-note roots, major and minor, since it has no single
settled convention the way guitar's shapes do and a shape
here is only shown where that's genuinely confident, not
just correct. A handful of guitar chords have no standard
open or barre shape either. Any of these says so rather than
showing nothing.

**Preview next chord** dims in a second picture underneath
the current one, showing whichever layers are already
switched on for whatever chord comes next - a look ahead at
the next change before it arrives, the same idea as the
Notes panel's own next-phrase preview.

## Keys and harmony

**Detect key** reads the notes and tells you what key they
sound like, with the runners up and how close they are.
Short melodies often genuinely fit several keys, so it
names more than one rather than guessing.

**Octave down** and **Octave up** move the whole written
line a full octave, for when a song sits too high or low
to sing comfortably. This changes the notation itself, so
playback and the mixer follow it; it is not the same as
the Notes panel's Down / As written / Up, which only shifts
how the notes are drawn while you sing.

The key you choose is used to build the harmony line.
Each of the {len(MAJOR_SCALES)} settings is named twice,
as in `F major / D minor`, because a key signature belongs
to both equally: a piece in D minor uses the notes of F
major. A note outside the chosen key is still harmonised,
at the nearest note in the scale.

## Singing along

Tick **Mic** in the mixer and your voice draws as a line
over the notes: on a box when you are on the note, above
or below it when you are sharp or flat. Gaps in the line
are breaths and consonants, not mistakes. Nothing is
scored yet - seeing the line against the notes is the
whole point, and it is enough to hear yourself land or
drift.

**Follow** scrolls the notes to keep up with the playhead;
**Repeat** loops a stretch you have selected, so you can
sing an awkward phrase over and over. If the notes sit in
a different octave from your voice, the **Notes** panel's
**Down / As written / Up** buttons move the drawn notes to
meet you rather than making you jump.

**Record** keeps a copy of what the microphone heard;
**Download recording** saves it once there is something to
save, which is useful for listening back or for reporting
a detection problem.

## When something looks wrong

A line drawn an octave below what you sang usually means
the microphone is losing the bottom of your voice, which
laptop and webcam microphones do. Brief spikes at the ends
of notes are the detector being confused by consonants,
not by you.
"""