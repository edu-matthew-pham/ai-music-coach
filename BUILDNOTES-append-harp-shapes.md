## Lever harp, stage 2: chord shapes (and chord-spelling alignment)

PLAN-lever-harp.md stage 2. Rule-generated, verified, rendered;
not yet played on the real harp. Stage 1 (strings, lever
search, Scale and Chord notes) is already on main.

### Spelling alignment (done first, as handed over)

- `lever_harp_chord_overlay(key, tones, spelling=None)` labels
  through `_spelled`; `chord_overlay_for` passes `spelling=`
  to the harp like every other instrument.
- The Scale layer and the "Not on this harp: Bb" footer stay
  key-spelled: they are about the key.
- `test_chord_marks_are_spelled_by_the_chord_not_the_key` no
  longer excludes the harp. It checks the harp for spelling
  only, like violin: its marks follow the key's lever setting
  (a G-major harp sounds F#, a C-major one only rings it), so
  *which* strings are marked depends on the key by design.
- DESIGN.md invariant 4 and the ownership table updated
  (project doc), including one new row: the harp's Chord-notes
  marks follow the key's lever setting, and `mixer_data`
  builds chord overlays once, in the song's opening key.

### The shape rule (`lever_harp_shape_strings`)

One string per chord tone, no string twice, the tones exactly
the chord's, lowest and highest string at most 7 strings apart
(an octave of the diatonic strings). Each string at the lever
state that sounds its tone: down, or raised a semitone. Among
shapes that pass, in order: fewest levers raised; root as the
lowest note; narrowest span; lowest string nearest the middle
of the harp; then leftmost, only for determinism. Searched per
chord (a few hundred combinations), not a table.

**Key-independent, and that departs from the plan's wording.**
The plan said a shape needing a lever other than the key's
setting says so with a flip mark, which would make a shape
depend on the key. Built instead: a shape is the strings and
levers the chord itself needs, whatever the key, so its marks
never move with the key (the property every other
instrument's shapes have, and the one `mixer_data` assumes).
A lever the key already has raised is raised in the shape too.
Cost: a harpist in G sees F# drawn as a raised lever on D's
shape even though that lever is already up. Easy to switch if
playing says the flip-only version is better.

### What it gives (all 48: 12 roots x major, minor, 7, m7)

Every one of the 48 gets a shape; nothing falls back. Spans
are 4 to 6 strings. In C: C = C5 E5 G5, Am = A4 C5 E5, F = F4
A4 C5, G = G4 B4 D5 - no levers. Chords with accidentals raise
what they need: D = D5 F5^ A5, E = E4 G4^ B4, Bb = A4^ D5 F5
(Bb is the raised A), Db = C5^ F5 G5^, F# = F4^ A4^ C5^ (three
levers, nothing natural), Eb7 = D5^ G5 A5^ C6^ (the widest). ^
is a raised lever.

### Verified

- All 48 against `chord_semitones` (not against the rule): one
  string per tone, none twice, pitches exactly the chord's,
  within the reach, a lever raising one semitone and never more.
- A hand-worked table of 14 chords pinned string by string,
  including every awkward case.
- Shape overlay: SHAPE_COLOUR marks, one raised tab per raised
  lever, identical in every key, spelled by the chord (Db reads
  Db F Ab), stacks in register, qualities outside the four
  return None (the caller falls back to Chord notes).
- Rendered to PNG over the structure and looked at (C, Bb, Db,
  Eb7).
- **Every instrument's SVG output diffed before/after against
  main (0e7de8d): 35,123 renders** (all instruments x 12 keys x
  12 roots x 11 qualities, structure/scale/diagram/chord/shape).
  Changes only in the lever harp: 725 chord-layer renders, and
  once label text is stripped from the harp's 1,584 chord
  renders there are 0 differences (no mark moved - only words);
  576 shape renders (12 keys x 48, None -> shape). Everything
  else, kalimba included, byte-identical.

### Open, for playing / later

- Play: C, Am, F, G (no levers); D, E, Bb (one lever); Db and
  F# (three); Eb7 (the widest). The rule picks strings within
  an octave; whether a hand reaches them, and whether Bb as
  A^ D F feels right against an inversion, is yours to judge.
- Only the four qualities are shaped; maj7, sus, 6 etc. return
  None. Extending is a tuple and a test parameter, once checked.
- The harp's Chord-notes layer uses the opening key's lever
  setting for the whole song (see DESIGN.md). A modulating song
  keeps its first key's setting on that one layer; the Scale
  layer and the shapes are right throughout.
- Stage 0 on the real harp still open: F3 on a tuner, each
  lever working.
