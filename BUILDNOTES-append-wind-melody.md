# Wind melody (flute and alto sax) - build notes (appended)

Plan: PLAN-wind-melody.md (Pattern Detectors project).

## Stage 1 - the view, without fingering data (2026-10-26)

Matthew's design, mocked up in the Design canvas and agreed: a chart
per note in phrase rows, left to right (lanes were tried and
dropped: a wind note is a hand shape, not a place).

Built
- `wind_melody.py`, plain Python like `melody_lanes.py`. Data first:
  `wind_blocks(piece, instrument, table=None)` gives one block per
  sounding note (written pitch, concert name, octave shift, lyric,
  chord, role, keys); `wind_rows` cuts them into phrase rows (the
  same `row_starts` the guitar tab uses) with the chord tones each
  row leaves out; `fold_repeats` folds a row identical to the one
  before into one marked x2; `wind_view` draws it.
- Flute sounds as written. Alto sax reads +9 semitones (a major
  sixth above concert), spelled in the written key (F concert reads
  D major, so Bb reads G and A reads F#). Big name = what the
  player reads; grey line = the concert note the chord sheet uses.
- Chord role of a note (R, 3, 5, 7...) is worked out in CONCERT
  pitch against the chord the note BEGINS under (a held note keeps
  it), so it matches the chord card whichever instrument.
- A note outside the written range (flute C4-C7, alto sax written
  Bb3-F#6) moves by whole octaves, nearest first, and gets the same
  amber pill as the lanes ("8va"). Same rule as melody_blocks.
- "Not in this phrase" column at the right of each row: per chord,
  the chord tones no note of the row plays, each drawn at the octave
  nearest the row's own notes (mean pitch; ties go lower). Frere
  Jacques over F: phrases 1-2 miss the 5th, 3-4 the root, 5-6
  nothing, 7-8 the 3rd.
- A pill over a chart counts the keys that change from the note
  before when it is four or more. Never shown when either fingering
  is unknown.
- Flute and Alto sax are NOT in `INSTRUMENTS` (the mixer and chord
  sheet have no picture for them); `melody_lanes.supported_families`
  adds them after the others, one size each, and `melody_view`
  hands them to `wind_view`. Show applies; header and placement do
  not. New checkbox "Flute and sax: fold a repeated phrase" (default
  on), one more input to `refresh_melody` (after prefer_low).
- `wind_fingerings.py`: the fingerings are DATA. `FINGERINGS` is
  EMPTY: a note with no entry draws a grey dashed "no fingering yet"
  chart, the legend says so, and nothing is guessed.

NOT BUILT / BLOCKED
- The fingering tables. Whether a fingering is right cannot be
  tested; typing a whole chromatic range from memory was judged
  unsafe (students would be taught it). Matthew is to supply a
  standard flute chart and a standard alto sax chart to transcribe.
  When it arrives: fill `FINGERINGS`, name the sheet in `SOURCE`,
  extend `KEY_LAYOUT` to the keys the chart shows (side, palm,
  trill, thumb Bb, foot keys - the layout now is only the finger
  holes, the thumb or octave key and the flute's right pinky).
  The four skipped tests in tests/test_wind_fingerings.py (every
  note of the range has an entry; no two notes draw alike) start to
  bite then.
- Chord sheet cards for winds (the chord tones as note charts).
  Agreed in design, not started.
- Alternate fingerings toggle (side Bb and the like): not built
  because the alternates are not known from a source yet.
- Repeat ticks for identical consecutive NOTES: none of the test
  songs has one.

Found
- Chord charts must cover the music's length exactly (the checker
  says so); several early test fixtures were wrong on that, not
  the code.
- Lyrics need one syllable per sung note in a Piece, even in tests.

Checked
- tests/test_wind_melody.py (53 tests, expectations worked out by
  hand from Frere Jacques in F; the fingering tables in them are
  INVENTED so adjacent notes differ by known key counts) and
  tests/test_wind_fingerings.py (layout well-formed; 4 skip until
  a chart is transcribed). 247 pass with the melody lanes, harp,
  piano, chords and fretted-tab files (not the full suite).
- Updated two pins in tests/test_melody_lanes.py: the family list
  now ends Flute, Alto sax; refresh_melody takes `fold`.
- 14 rule mutations (transposition, role naming, role from written
  pitch, missing-tone rule, pill limit, fold ignoring the chord,
  range direction, written key spelling, key-change count, lyric
  escaping, unknown-fingering pill, ring on every note, nearest
  octave, chord taken at note end): two survived at first (the ring
  colour; a note held across a chord change) and got tests; all
  caught now.
- Looked at in a browser (Playwright) with invented fingerings:
  rings, roles, x2 rows, the right-hand column and pills draw as in
  the mock-up. The label column was too narrow ("Phrases 3-4"
  wrapped); widened.
- Not run: the full pytest suite, the interface test files that
  need gradio, the Playwright browser tests of the real app, a
  click-through of the live app.
