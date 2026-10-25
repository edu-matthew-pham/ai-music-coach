## Piano shapes: fingers in the right order

Found by Matthew reading the chord sheet: G showed 5 1 3 in the
right hand. The shape code put every note at its pitch class
inside one octave per hand (so it would fit two octaves), which
drew a hand's fifth *below* its root for roots F to B. The left
hand had the same fault (thumb left of little finger).

- **`piano_shape_voicing(root, quality, octaves)` (new)** says
  where every finger goes. **3 octaves: the real shape for every
  chord** - left hand root (5) and fifth (1); right hand an
  octave up, root (1), third (3), fifth (5), rising. The widest
  (B) reaches key 31 of 36, hands always 5 keys apart.
- **2 octaves cannot hold that** (a root-position right hand from
  B runs off the edge), so each hand is put in rising order and
  the fingers follow the notes: left 5 on the lowest, 1 on the
  higher; right 1 lowest and 5 highest, middle finger 3 in root
  position or 2 for an inversion. 14 of the 24 major/minor chords
  are rearranged this way (C to E are not). The sheet says
  "Rearranged to fit two octaves" under those cards.
- **Chord sheet's piano tab starts on 3 octaves**
  (`default_variant`); other tabs unchanged. The mixer's own size
  choice is untouched.
- **Pictures:** 1,056 of 20,526 renders changed, all of them
  piano shapes (528 per size); every other picture is
  byte-identical.
- **Tests:** 11 new in `test_chord_shapes.py` (voicing written out
  from the intervals for 48 chords, fit and no overlap, fingers
  ascending, 2-oct notes equal 3-oct notes, marks render, the
  inversion fingering) and 2 in `test_chord_sheet.py`. Mutation
  checked (unsorted left hand, 3 octaves wrapping, inversion
  fingered 1-3-5: all caught; the last needed a test added).
- **Known limit, not changed:** roots like F#, Bb, Db put the
  thumb on a black key, where teachers often change the
  fingering. 1-3-5 is correct for the notes, not always the most
  comfortable.
- **Seventh chords** draw the triad only, as before.
