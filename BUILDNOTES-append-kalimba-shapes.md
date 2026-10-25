## Kalimba, stage 2: chord shapes

PLAN-kalimba.md stage 2. Rule-generated, verified, rendered;
not yet played on the real instrument.

- **The rule (`kalimba_shape_tines`).** A shape is one tine
  per chord tone (no note doubled, root present, tones exactly
  the chord's), at most one tine per column, playable as one
  thumb sweeping neighbouring columns or two sweeps - one per
  thumb, each on its own side of C4's centre column. Among
  shapes that pass, prefer one thumb, then fewer top-row
  tines (which also makes a doubled note use its middle-row
  copy), then root lowest, then nearest the centre. Searched
  per chord over each tone's tines (a few hundred
  combinations at most), not a table.
- **What it gives, measured over all 48 (12 roots x major,
  minor, 7, m7).** Key-of-C chords are three middle-row
  neighbours, root lowest (C = C4 E4 G4, Am = A4 C5 E5, F =
  F4 A4 C5, G = G4 B4 D5); accidentals take the top tine in
  the same column (E = E4 G#4 B4, Bb = D4 F4 A#4 - an
  inversion); sevenths are mostly a four-tine sweep (G7 =
  G4 B4 D5 F5). Three are two-thumb (Bb7, Cm7, Gm7).
- **No shape, honestly: Eb, Gm, Eb7.** Their tones never sit
  in neighbouring columns on this layout. The bass row looked
  like it rescued Gm and Eb (G4, A#3, D5) in a first prototype,
  but only because the prototype treated the bass tine's column
  as adjacent to the middle row's - the bass tine sits at a
  different depth, so that isn't a sweep. They return None, and
  the mixer falls back to Chord notes (confirmed through
  `mixer_data._diagrams`).
- **Bass row (Matthew's call this session).** On the 41-key
  the root is added from the bass row where it exists (roots
  F to B) as an extra low note, not part of either sweep;
  roots C to E have no bass tine and get the sweep alone. The
  sweep is identical on both variants, by test.
- **One real failure on the first test run, kept as evidence.**
  The "doubled note uses its middle copy" test failed on Fm7:
  the rule picks D#4 C4 F4(top) G#4 in one sweep over F4 D#4
  C4 + G#4 across two thumbs, because one thumb outranks the
  middle row. The rule's order was kept and the test now
  states it; Fm7 goes on the play-it list to settle which grip
  is actually easier.
- **Verified:** all 48 against `chord_semitones` (not against
  the rule), sweep shape per chord, a six-chord sample pinned
  by hand, bass addition on 41 vs 34, SHAPE_COLOUR marks only,
  viewBox stacking. Shapes rendered to PNG (cairosvg) over the
  structure and looked at. Every other instrument's SVG output
  byte-identical before and after (4455 renders hashed).
  Lever harp section untouched.
- **help_text.py:** only the kalimba half of the "no shapes
  yet" sentence changed; the harp's half stays.
- **Pre-existing, not acted on:** `tests/test_chords.py` has 7
  failures in a sandbox without `mido`, identical on untouched
  main - environment, not code.

### Open, for playing / later

- Play: C, Am, F, G, E, Bb (the plan's sample), plus Fm7 both
  ways and one two-thumb shape (Gm7).
- Six-note idea (both thumbs sweeping the whole chord, one
  octave each side): measured possible for 32 of 48 chords.
  Not built - a second-layer option like guitar's higher
  position, if wanted.
- Only the four qualities are shaped; maj7, sus, 6 etc. return
  None. Extending is a tuple and a test parameter, once
  checked.
