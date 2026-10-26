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

## Auto: at most three columns (2026-10-26, Matthew: "a little too generous")

- Auto used `repeat(auto-fit, minmax(least, 1fr))`, which on a 2560 screen
  gave four columns. Now it is container-query breakpoints: one strip,
  two from 2 x least + gap, three from 3 x least + 2 gaps, never four
  (MAX_AUTO_COLUMNS). Kalimba/harp: 2 columns from ~1280px, 3 from ~1930px;
  piano 2 from ~1600px, 3 from ~2410px.
- Tried and dropped: capping how big a strip may be drawn (max width) and
  capping columns with a percentage inside `minmax(max(...))`. Chrome does
  not count that percentage when working out how many auto-fit columns fit,
  so a 1920 screen fell to one column. Breakpoints are plain and testable.
- Still scale-driven: how many BEATS go in a column is fixed (32), not
  worked out from the screen's height. See the question below.

## Columns fit the screen's height; pages turned with the arrows (2026-10-26)

Matthew: a column should hold as many rows as fit before wrapping to the
next, counting the other UI above the lanes; then pages, turned with the
arrows, each starting at a phrase.

- Python (`phrase_ranges`): Auto and Two draw the song as ONE PIECE PER
  PHRASE (the tab's `row_starts`) under one header, with data-columns,
  data-least (72% of natural width), data-max (3 Auto, 2 Two) and
  data-cap (a cropped keyboard's widest). As it stands that is the one
  tall strip. A piece that is not the last leaves its end beat line to
  the next and keeps a 4px margin (the last keeps 24), so phrases sit
  14px apart. `chunk_ranges`/CHUNK_BEATS and the CSS container-query
  columns are gone. One column and one-phrase songs: byte-identical
  (240 renders).
- Browser (`FLOW_JS`, installed once by `demo.load(fn=None, js=...)`):
  columns from the width (Auto: floor of width / least, at most 3; Two:
  2). Room for a page: in full screen the section's height less
  everything above the lanes (controls, tabs, size, warning line) less
  the pager; in the page, the lanes' box (70vh). Whole phrases are
  packed into a column until the next would not fit (a phrase taller
  than a column gets one to itself), columns into pages. One page
  shows; a pager ("Page 2 of 7", ◀ ▶) and the ← → keys turn it (not
  while typing in a box). Each column carries its own copy of the
  header. Re-packs on a redraw, resize, tab change or full screen; the
  page you are on is kept. In the page, one column stays the scrolling
  strip (a page per phrase was no help at 1366 wide).
- Found: Gradio patches a redrawn view into the same element, which
  threw the packed pages away while the layout thought it was done; it
  now re-packs whenever the pages are missing.
- Checked in the real app (Playwright, Wellerman): pages fit the screen
  in full screen at 1920x1080 (2 columns, 6 pages), 1366x768 (2, 7) and
  2560x1440 (3, 2), piano 1920 (2, 4); in the page at 1920 the page
  fits its box; Two / One / Auto switch; → twice gives page 3, Escape
  keeps it; flute and harp fine; no page errors. 39 tests in
  test_melody_columns.py (the browser half only by reading FLOW_JS);
  13 mutations caught; 308 pass across the melody, wind, tab and
  interface files.
- Pre-existing, not from this work: sometimes after Load Wellerman a
  toast "Value: song:0 is not in the list of choices" (the chord sheet's
  key radio). Seen once on 7c7b564 (before today) and once now; a race.

## Part choice in the Melody bar (2026-10-26)

Matthew: a song of several tunes (partner songs, a choral score imported
whole) showed only its first tune in the Melody section; mirror the
mixer's "Your part", not linked to it.

- `melody_page(..., part_label)`: the tunes come from `music.part_names`,
  `keep_part` keeps the choice if the song still has it, else the first;
  the phrase list and the piece are the chosen tune's (`list_phrases`
  and `selected_piece` already took a part). Returns "parts" and "part".
- main.py: a "Part" dropdown in the slim bar after the phrase list,
  hidden unless the song has more than one tune; one more output and
  one more input (`part_label`, after `columns`) of `refresh_melody`.
  Separate from the mixer's choice (the mixer keeps its own in the
  browser).
- Checked: tests/test_melody_part.py (11, hand-read from the partner
  songs: Three Blind Mice first, Frere Jacques four lines); three
  mutations caught. Live: Twinkle shows no Part; the partner songs show
  it on Three Blind Mice, choosing Frere Jacques redraws its words and
  its four-phrase list; no page errors.

Still open
- Not in the wind view or the tab (they already read in rows).
- Beat height ("Dense") and narrower margins: not done; try the columns
  first.
- The rest of the Melody controls are still busy (Matthew's note): the
  Guitar/ukulele row shows on every tab, Show/Chords go/Columns are
  three radios.
