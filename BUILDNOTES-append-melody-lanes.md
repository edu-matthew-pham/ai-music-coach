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
