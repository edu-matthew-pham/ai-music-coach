# Melody lanes - build notes (appended)

Plan: PLAN-melody-lanes.md (Pattern Detectors project).

## Stage 1 - kalimba (2026-10-26, built unattended)

Built
- `melody_lanes.py`: plain Python, reads the song's text, never
  writes the boxes (AST tests pin that). `melody_blocks(piece,
  instrument)` gives one block per note: lane, start, length
  (beats), note name as written (no octave), lyric, thumb, row,
  in_range. `lanes_html` draws it: sticky header SVG over a
  scrolling body SVG, time DOWN the page, lanes scale with the page.
- Kalimba: 17 lanes named by the middle-row note, top-row note
  under it. Placement prefers middle, then top, then bass. Doubled
  tines (F4 C5 F5 C6) use the middle row. Thumbs: blue left, purple
  right, grey centre.
- Out of range: red "off" strip, notes not moved. Message counts
  below/above and says "Octave up/down would bring every note on"
  ONLY if a shift of 12 really fits every note; else says the song
  is wider than the instrument. Wellerman (lowest D3) is off on
  both sizes; octave up fits.
- Melody section in main.py between Chords and Practice; nav link;
  own phrase dropdown (Whole part first), per-family tabs, size
  radio. Kalimba defaults to 41 keys (it holds more of real songs).
- Show/layout reads: `refresh_melody` reads the boxes only.

Found / decided
- Labels are note names as written (Bb stays Bb), no octave.
- Blocks shorter than 16px draw no label (half-beat notes were
  clipped).
- Five boxes change at once when a song loads, so the dropdown's
  old label can arrive before its new choices; the dropdown allows
  a custom value and `keep_phrase` falls back to Whole part.
  (Otherwise Gradio raised "not in the list of choices".)
- Not fixed, reported: `_absolute_pitch` gives the wrong octave for
  Cb/B#-style spellings (pre-existing convention).

Checked
- 37 tests in tests/test_melody_lanes.py; five mutations (row
  preference, thumb sides, range check, start offset, lyric
  escaping) all caught.
- All 20,526 existing instrument renders byte-identical.
- Live in the real app (Playwright): phrase dropdown, Twinkle,
  Wellerman, both sizes, no page errors.

## Stage 2 - harp and piano (2026-10-26, unattended)

Built
- Placement is now one function, `_place(pitch, instrument)` ->
  (lane, row, lever); kalimba, harp and piano each have a range
  and a message word (tine, string, key).
- Harp: 19 strings F3..C6, C red and F blue. A natural note is
  its own string; a sharp or flat is the string below with its
  lever up (block gets `lever=True`, a small lever tab and an
  up arrow). C#6 is on (C6's lever); D6 is above the harp.
- Piano: lanes start at C3 (decision 13); 2 octaves = C3..B4,
  3 octaves = C3..B5. White lanes 36 wide, black lanes 22 wide
  centred on the join. Cropped to the song's lowest and highest
  note plus two keys, widened to white keys, clamped to the
  keyboard. Out-of-range notes still go in the red "off" strip.
- A cropped (<14 lanes) picture has a wrapper max-width so lanes
  do not balloon on a wide page.
- Melody tab order follows INSTRUMENTS (Piano, Kalimba, Harp).

Found
- The shading had to paint white lanes first and black lanes
  after, or a white lane's stripe covered half of the black one.
- Not confirmed against a real keyboard: C3 as the first key
  (decision 13 said to confirm in stage 2). C4 is 48 here, the
  same convention as the rest of the code.

Checked
- tests/test_melody_lanes_harp_piano.py (17 tests, expected
  lanes worked out by hand), plus the stage 1 tests: 54 pass.
- All 20,526 existing renders byte-identical.
- Live: Twinkle on all three Melody tabs, no page errors.
