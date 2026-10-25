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


## Chord marks spell themselves by the chord

Same session, after Matthew spotted "C#" on a Db shape render
(drawn in C). The shape was right; the label came from the key.

- **New: `chords.chord_spellings(name)`** - each tone spelled
  by letter from the root (third two letters up, fifth four,
  seventh six) plus whatever sharp or flat lands it: Db = Db F
  Ab, Gm = G Bb D, E = E G# B, Bb7 = Bb D F Ab. A tone needing
  a double accidental falls back to the plain name in the
  root's direction (Gbm = Gb A Db) - agreed with Matthew, rare.
  Single-accidental letters theory requires are kept: Abm = Ab
  Cb Eb, C# = C# E# G#, Fdim = F Ab Cb.
- **Where it applies:** the Chord-notes layer on piano, guitar,
  ukulele, violin and kalimba, and the Chord-shape labels on
  violin and kalimba (piano/guitar/ukulele shapes show finger
  numbers). Scale stays key-spelled. **Lever harp left on key
  spelling** - its chord layer belongs to PLAN-lever-harp.md's
  chat; a handover prompt was given to Matthew.
- **Measured, not assumed:** every render (20526 across all
  instruments, six keys, 14 roots, all 11 qualities) diffed
  before/after. Changes only in Chord-notes and Chord-shape
  label text; zero changes once label text is stripped (no mark
  moved); lever harp, Scale and structure byte-identical.
- **A test that was wrong, not the code:** the new "same labels
  in every key" test failed on violin. Violin's chord layer
  marks only notes inside the key's own fingering pattern, so
  which tones appear is key-dependent by design. The test now
  checks violin for spelling only.
- `mixer_data.py`: comment only - the "spelled in the opening
  key, cosmetic known gap" note described exactly this gap and
  was rewritten. DESIGN.md invariant 4 updated (project doc).
