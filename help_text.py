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
ukulele, a violin chart, a chromatic kalimba, or a 19-string
lever harp. Each except the harp has its own size toggle
once it's ticked on - piano between two and three octaves,
guitar between a compact eight frets and the full thirteen,
ukulele between six and ten (its own shapes stay lower on
the neck than guitar's, and its short scale makes a player
less likely to go far up it at all), kalimba between 34
keys and 41 (the 41 adds a row of seven bass tines, F3 to
B3, under the centre). Four kalimba notes - F4, C5, F5, C6
- have a tine on both rows, and both are marked. The lever
harp is set to the key: Scale marks the strings that sound
the key's notes and lifts a lever tab on each string that
has to be raised. Its levers only sharpen, so a flat key
loses notes (F needs a B-flat) - a key note no string can
sound is named under the picture. Chord notes rings a
string that is one lever flip from a chord tone, which is
how a borrowed chord shows up. Violin's
toggle is
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
left hand against a triad right hand on piano (little finger on the
lowest key of each hand, thumb on the root for the right; on 3
octaves it is always the true root-position shape, and on 2 it is
the same chord rearranged to fit, with the sheet saying so), a double stop
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
open or barre shape either. The kalimba's
shape is the chord's tones on neighbouring tines, one thumb
sweep (two for a few sevenths), middle row first, with the
root added from the bass row on the 41-key; Eb, Gm and Eb7
have no such sweep on this layout. The lever harp's shape is
one string per chord tone within an octave of strings, with a
raised lever tab on each string that has to be up - the
chord's own levers, whatever the key; every chord of the four
basic kinds has one. Any of these says so rather than showing
nothing.

**Preview next chord** dims in a second picture underneath
the current one, showing whichever layers are already
switched on for whatever chord comes next - a look ahead at
the next change before it arrives, the same idea as the
Notes panel's own next-phrase preview.

## The chord sheet

The **Chords** section, below Playback, is for looking over
before you play: every chord on one instrument at once, with
a picture of the key's notes at the top. Pick the instrument
from its tabs; each has its own size choice, separate from the
mixer's. Piano starts on 3 octaves. Click any card to enlarge it
(click it again, or press Escape, to close), or press **Full
screen** to give the whole sheet the window (Escape leaves it).

With a song loaded it starts on the song's key and shows the
chords the song plays, and says so ("from the song"). Pick
any other key in the **Key** box there to browse it - every
major and minor key is listed - and it says "your choice"
instead, with a **Back to the song** button. Browsing never
changes the song's own key. With no song it shows C major
until you pick another. A minor key uses its major key's
notes with its own home note marked, so A minor is C
major's seven notes with A as home.

Above the tabs, **Show on every chord** has two ticks, Chord
shape and Chord notes, both on to start. They are different
colours, so together they read as the shape sitting on top of
the notes; untick one to see the other alone. Where an
instrument has no standard shape for a chord it shows every
place the chord's notes fall, and says so. If you untick both,
the notes are shown, so a chord is never left blank.

On the kalimba tab, a second picture, **Playing the scale in
order**, numbers the key's eight notes 1 to 8 going up from home.
The middle row is a zigzag from the centre tine, so the numbers
alternate between thumbs; blue is the left thumb, purple the
right, grey the centre tine (either), and home has an orange
ring. A key with sharps or flats uses the top row for them.

## The melody view

The **Melody** section, below Chords, shows the tune in the
boxes above on an instrument, to look over before you play.
Time runs down the page like a falling-notes video: one lane
for each tine, and a block where each note falls, as long as
the note lasts, with the word sung beside it. Pick **Whole
part** or one phrase from the dropdown there; it is separate
from the Song section's own phrase choice and never changes it.

On the kalimba a block is blue for the left thumb, purple for
the right, and grey for the centre tine (either thumb). Each
lane is named by its middle-row note, with the top-row note
under it. A note on the top row (a sharp or flat) is marked
with a small up triangle, and one on the bass row with a down
triangle. A note that appears twice on the kalimba is drawn on
the middle row. Kalimba starts on 41 keys.

On the lever harp each lane is a string (C red, F blue, as on
the harp). A sharp or flat sits on the string below it, with a
small tab and an up arrow to say that string's lever must be up
for the note. On the piano the lanes are the keys, starting at
C3: wide lanes for the white keys, narrow ones for the black
keys. The piano shows only the keys the tune needs with a little
spare, so a short tune is not a keyboard of empty lanes. Piano
starts on 3 octaves.

**Show** has two ticks, Melody and Chords, both on to start. The
chords come from the chart in the Song section: each is a pale
pink block in the lanes of its notes, behind the melody and as
long as the chord lasts, with its name and a bar the same length
in the left margin. With no chart there is nothing to show for
Chords. If you untick both, the melody is shown, so the view is
never blank.

**Chords go** picks where those blocks sit: **Near the melody**
(the default) puts each chord's notes at whatever is closest to
what the melody is playing, so your hands need not jump; **As in
the chord sheet** puts them where the Chords section's beginner
shape does. A chord the chord sheet has no shape for goes near the
melody either way.

**Top of the lanes** starts on **Short picture**: the real
instrument above the lanes, cropped to its upper part, each of its
columns over its own lane, like the falling-note piano videos.
**Full picture** keeps the whole instrument, which is tall.
**Plain labels** is just a row of lane names, the smallest. On the
piano the picture is cropped to the lanes shown.

On the guitar and ukulele tabs the melody is drawn as tab: a
line for each string (the high string on top), the fret number
where each note falls (0 is an open string), the words underneath,
and the tab has a row for each phrase (a long phrase is cut at a
bar line, so no row is wider than sixteen beats), like printed tab. Every note takes the lowest fret that plays it, the nearest the
nut, so a note's place never depends on the others; hover a note to
see why it is there. It is a suggested fingering, not the only one:
a high passage can jump about, and a later choice will keep your
hand in one position. Both start on the longer neck. Chords and the
instrument picture are not on the tab yet, and the Show, top of the
lanes and chords-go choices do not change it.

If the tune has notes the instrument does not have, they are
drawn in red in a strip marked "off" at the left, and a line
above says how many and whether Octave up or Octave down in
the Song section would bring every note on. The notes are never
moved for you.

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