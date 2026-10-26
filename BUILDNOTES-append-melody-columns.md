# Melody lanes in columns - build notes (appended)

Plan: PLAN-melody-lanes.md (Pattern Detectors project).

## Columns (2026-10-26, Matthew's review)

Problem (measured, Wellerman, full screen 1920x1080): the lanes are
drawn to the page's width, so a wider screen made every beat taller.
One beat was ~60px and a screen held ~15 beats (about 4 bars) on the
kalimba and harp, ~20 on the piano.

Built
- `chunk_ranges(cuts, total_beats, columns)`: the song cut into strips
  of about CHUNK_BEATS (32) beats, each cut at the phrase start nearest
  an even share (ties go earlier), so a phrase is never split. Cuts
  come from `fretted_tab.row_starts` (same phrase starts as the tab).
  One column, or a song that rounds to one strip (under 48 beats),
  draws the one tall strip exactly as before.
- `lanes_html(..., columns, cuts)`: the lane set, positions and header
  are worked out once for the whole song (so the strips line up and a
  cropped piano is cropped the same everywhere); only the body is drawn
  per strip. A note belongs to the strip it BEGINS in; a chord layer
  block or name that runs over a cut is on both, clipped. Beat numbers
  and bar lines are the song's own ("beat 37" at the top of strip two);
  a strip may start part way through a beat (19.5) and the grid stays
  true.
- Layout is CSS only: a grid, strips left to right then down (like the
  wind view's phrase rows), each with its own sticky header.
  - Auto: `repeat(auto-fit, minmax(least, 1fr))` where `least` is 72%
    (AUTO_SCALE) of the strip's natural width. Kalimba 41 keys: two
    columns from ~1280px, harp similar, piano 3 octaves only from
    ~1600px (at 1366 it stays one, its note names would be ~6px).
    Where only one strip fits, a container query makes the strips one
    tall strip again: no gaps, `display:contents` so the first header
    stays pinned all the way down, later headers hidden.
  - Two columns: always two. One column: today's picture.
- New "Columns" choice (Auto / One column / Two columns) in the Melody
  controls, one more input to `refresh_melody` (after prefer_low).
- "Top of the lanes" choice REMOVED from the screen (Matthew: Compact
  is enough; the others are unlikely to be used). `refresh_melody` no
  longer takes `header` and always passes HEADER_COMPACT; the other
  headers are still in melody_lanes.py (and tested), just not reachable
  from the screen.

Measured (Wellerman, beats on screen, kalimba 41 / harp / piano 3 oct)
- 1920x1080: one column 15 / 14 / 20; two columns 66 / 63 / 84 in all,
  a beat 30 / 31 / 24px (was 60 / 63 / 48).
- 1366x768: kalimba and harp two columns, a beat ~21px; piano stays
  one column (34px).

Checked
- 240 renders (4 songs x 5 instruments x 4 headers x 3 Show settings):
  One column byte-identical to before; Auto identical for the short
  songs, different only for the two long ones, as intended.
- tests/test_melody_columns.py (29 tests; cuts worked out by hand from
  the Wellerman's phrase starts: 36 68 100 136 168). 14 rule mutations
  (farthest cut, tie later, note by end, chord not clipped, relative
  beat numbers, chord ending at the cut kept, Two not forced, scale
  ignored, container threshold, no display:contents, grid line floor,
  One ignored, header only on strip one, chord names only on strip
  one): three survived at first and got tests; all caught now.
- 218 pass with the melody, harp, piano, chord, tab and interface
  wiring files (not the full suite).
- Playwright on the rendered HTML: Auto at 1920 and 1366 (kalimba),
  1200 in-page (one column, header pinned after scrolling 2500px),
  full screen two columns (first row's headers pinned, second row's
  below). Not run: the real Gradio app, the full pytest suite.

## Controls cleanup (2026-10-26, Matthew: "the UI takes too much space")

- The three rows of controls over the pictures are now ONE slim bar:
  Show, Chords go, Columns, Full screen. "Chords go" became a dropdown
  (same values), the bar went from ~210px to ~85px.
- The guitar/ukulele options (fingering, width, open strings, lower
  positions) show only on the Guitar and Ukulele tabs; the flute/sax
  "fold a repeated phrase" checkbox only on Flute and Alto sax
  (`melody_lanes.option_rows(family)`, wired to each tab's select). The
  rows start hidden; their values still reach the redraw.
- Full screen hides the "Melody on the instrument" heading and its
  sentence (`.melody-intro`).
- Fixed after: in full screen the phrase list and status line were
  squeezed to slivers (the section is a fixed-height column);
  `#melody.melody-full > * { flex-shrink: 0 }` makes it scroll instead.
- Fewer lines (Matthew: "no need to take too many lines"): the phrase
  list joined the slim bar, the status line ("The whole tune.") is
  hidden in full screen, and the size choice (34/41 keys, 8/13 frets)
  sits at the right of the tab names' line. In full screen the notes
  now start ~175px down, from ~375px.
- Checked in the real app (gradio 6.30 installed in the container,
  Playwright): rows appear and vanish with the tab, Columns and the
  guitar fingering still redraw, flute still draws, no page errors;
  tests/test_interface_runs.py passes (10). New tests (35 in
  test_melody_columns.py); two option_rows mutations caught.

Still open
- Not in the wind view or the tab (they already read in rows).
- Beat height ("Dense") and narrower margins: not done; try the columns
  first.
- The rest of the Melody controls are still busy (Matthew's note): the
  Guitar/ukulele row shows on every tab, Show/Chords go/Columns are
  three radios.
