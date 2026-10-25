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

## Stage 3 - picture header, chords layer (2026-10-26, unattended)

Built
- Controls above the tabs: **Show** (Melody, Chords; both on),
  **Top of the lanes** (Plain labels | Instrument picture) and
  **Chords go** (Near the melody | As in the chord sheet). All
  three are view settings; none writes the boxes.
- Defaults (my calls, to check in use): plain labels, because the
  pictures are tall (kalimba ~340px, harp ~400px on a wide page
  with a sticky header); chords near the melody, per decision 14.
- Chord layer: `chord_spans(piece)` (from `read_chart`, cut to the
  piece's length) and `chord_blocks(piece, instrument, melody,
  placement)` -> one block per chord tone. Drawn first, pale
  magenta (the chord-notes colour at 25% opacity, 55% if the
  melody is unticked), the melody on top. Left margin: a bar the
  chord's length and its name (the name is dropped under 14px, the
  bar stays, so a chart of half-beat chords stays readable).
- Near the melody: the melody's average pitch over the chord's
  beats (else over the whole tune, else the instrument's middle);
  each chord tone goes to the pitch within six semitones of it,
  moved an octave at a time onto the instrument if it is off.
  Chord tones are therefore not a voicing (a C chord under a C4
  melody is G3 C4 E4). Known limit, see below.
- As in the sheet: kalimba tines from `kalimba_shape_tines`, harp
  strings from `lever_harp_shape_strings`, piano keys from
  `piano_shape_voicing` (both hands); no shape -> near the melody.
- Picture header: the instrument's own `structure_for` picture
  nested under the lane names, cropped to the lanes shown and
  shifted so each column is over its lane. To make that exact the
  lanes now take their picture's column width (kalimba 36, harp 30,
  piano white 44 and black 26), where stage 1 used 36 throughout.
  Piano crop also holds the chord layer's keys.

Found / limits
- "Near the melody" chooses by closeness, not by voicing: it can
  put a chord's fifth below its root. Right for "hands need not
  jump", not for "this is how to finger it". The chord sheet's
  shape stays the fingering reference.
- A chord changing faster than a beat draws blocks too short to
  read; the plan's thin-band idea is not built (still open).
- An imported file was not available overnight; try one.

Checked
- tests/test_melody_lanes_chords.py (23 tests); six mutations
  (nothing-ticked fallback, window, placement switch, kalimba and
  harp picture offsets, piano crop ignoring chords) all caught.
- All 20,526 existing renders byte-identical.
- Live (Playwright): Wellerman, chord blocks present by default
  (150) and gone when Chords is unticked; picture header, As in the
  chord sheet, harp tab; no page errors.

## Follow-up (2026-10-26, Matthew's review)

- **Short picture** added as the header default (Matthew: "can we
  have a short version of the instrument picture"). The picture is
  cropped to 55% of its height (at least 100px): kalimba 34 keys 100,
  41 keys 113, harp 143, piano 108. Full picture and plain labels
  stay as choices. Changes the stage 3 default (was plain labels).
- Chords near the melody confirmed as the default.
- Half-beat chords now get a small (9px) name in the margin;
  quarter-beat and shorter keep only their bar.
- Tests: 79 in the three melody files; three more mutations caught.

## Stage 4a/4b - guitar and ukulele tab, layer 1 (2026-10-26)

Plan: PLAN-fretted-tab.md. Built the first layer only (Nearest the
nut); Stay in a position and Smart shifting are not built.

Built
- `fretted_tab.py`, plain Python like `melody_lanes.py`: data first
  (`fretted_blocks`), drawing second (`tab_html`), wired in through
  `melody_view` (Guitar and Ukulele go to `fretted_view`).
- Rule: every note takes the lowest fret that plays it within the
  neck shown (guitar 8 or 13 frets, ukulele 6 or 10). A note's place
  depends on nothing else, so it is fully stable.
- Strings are counted by physical line, bottom line first as the
  tuning list is stored; the ukulele is re-entrant (its G is higher
  than its C), so its lowest note is its C string (C4), not its G.
- Out of range: red block on a line of its own above the strings,
  and a line counting them with the octave-shift check (only claimed
  if a shift of 12 really fits every note).
- Each note has a "why" tooltip ("fret 3 on the high E string - the
  lowest fret that plays G"). Tab wraps every 16 beats.
- Both start on the longer neck (13 and 10 frets) so fewer notes
  fall off the end. Chords, the picture header and the Show,
  header and placement controls do not apply to the tab yet; the
  view says so.

Found
- The Wellerman on the guitar shows exactly the weakness the plan
  predicted for layer 1: the hand jumps between frets 10, 5 and 3
  within a line. That is the evidence for layer 2.
- The Wellerman is wider than the 10-fret ukulele (lowest note D3,
  neck starts at C4), and says so.
- The "lower string wins a tie" rule can never fire: no two strings
  of either instrument share an open pitch, so two places never
  have the same fret. The mutation that flips it survives; it is an
  equivalent mutant, left in the rule only so the order is defined.

Checked
- tests/test_fretted_tab.py (26 tests, frets worked out by hand
  from the tunings); seven of eight mutations caught (the eighth
  is the equivalent mutant above).

## Tab rows follow the phrases (2026-10-26, Matthew's review)

- Matthew: rows should break at the most logical pause, where a
  hand position could switch, not every 16 beats. Now `row_starts
  (piece)`: a row begins at every phrase (the lyric lines), and a
  phrase longer than 16 beats is cut at the latest bar line that
  keeps the row within 16 (the chart's bars, else every four beats),
  or at 16 itself if there is no bar line to use. Rows are as wide
  as their phrase. Layer 2 (a position per phrase) will therefore be
  a position per row, with its label at the row's start.
- Width cap: the tab never stretches past its natural size (48px a
  beat), so it no longer spreads across a wide page.
- `tab_html(..., starts=None)` still wraps every 16 beats if given
  no row starts (used by tests and as a fallback).
- Tests: 34 in tests/test_fretted_tab.py; six row mutations, all
  caught (the limit-fallback one needed a test for a bar line
  longer than 16 beats, added).

## Stage 4c - layer 2, Stay in a position (2026-10-26)

Matthew's design, built as agreed: group in advance (not greedily),
a width he can change, open strings optionally free.

Built
- `Stay in a position` fingering in `fretted_tab.py`. A position is
  a window of N frets (4 to 8, default 5, held to the frets shown).
  Per note a bit mask says which windows hold one of its places; a
  note with an open-string place fits every window when open strings
  are free (the default).
- `_group_notes`: a dynamic programme over the whole tune picks the
  split by, in order: fewest positions; fewest cuts at a place that
  is not a pause; most even runs (smallest sum of squared sizes).
  A pause is after a rest, on a bar line, or at a phrase start.
  Deterministic; same tune, same answer.
- Within a group: the lowest window that holds every note, and each
  note takes its lowest fret in it (open strings kept when free).
  Label = the group's lowest fretted fret, or "open strings".
- Blocks gain `segment` and `position`; `why` names the box
  ("... inside the frets 8 to 12 position").
- Drawing: a green bracket and label over each group, drawn row by
  row (a group crossing a row break is bracketed in both rows).
- Controls (Melody section): Fingering, Position width, Open strings
  are free. They only change the guitar and ukulele tabs.
- Default fingering stays Nearest the nut (Matthew: simple first).

Found
- The fewest-positions rule makes the Wellerman one position: frets
  6 to 10 at width 5, 10 to 13 at width 4 (all notes within the box
  or open), against nearest-the-nut's jumping between frets 1 and 10.
  Correct by the rules, but the low-neck answer a teacher might
  prefer is not offered: nothing prefers a LOWER position across
  groupings (within a group the lowest window is taken). Worth
  watching in use.
- Wider width never needs more positions (tested on the Wellerman).

Checked
- 68 tests in tests/test_fretted_tab.py, frets and groups worked out
  by hand; every note is the pitch asked for and every box is no
  wider than the width, over 3 instruments x 5 widths on the
  Wellerman. Ten rule mutations, all caught (two survivors, bar
  lines as pauses and the width cap, got new tests).


## Chords on the guitar and ukulele tab (follow-up to stage 4)

Decided with Matthew: the picture header is dropped for guitar and
ukulele (the tab is the picture); chords go on the tab, as printed
tab does, as names with small Guitar Pro style chord boxes.

- fretted_tab.py: `chord_shape(name, instrument)` (the chord sheet's
  beginner shapes; None when none exists), `chord_box_svg` (44 px
  box, 4 frets, x / o above the strings, magenta dots with finger
  numbers, barre bar, "Nfr" when the shape starts above fret 1),
  `chord_layer(piece, instrument)` (uses melody_lanes.chord_spans),
  `tab_html(..., chords)`, `fretted_view(..., show)`.
- The heading grows by 78 px when chords are shown. A chord of a
  beat or more gets name + box, half a beat the name, less a tick.
- Show is honoured (Chords only draws no notes; neither ticked is
  the melody); `melody_view` passes it through. Header and
  placement still do not apply to the tab.
- Elements carry classes (chord-name, chord-box, chord-dot,
  chord-open, chord-mute, chord-barre, chord-base) for tests.

Checked: 13 new tests (C = x 3 2 0 1 0 gives 1 cross, 2 rings, 3
dots; F barre at 1; Eb7 starts at 6fr; Twinkle row 1 has 3 boxes;
Show cases; no chart). Mutations: window rule, nut thickness, size
thresholds, Show rule, ukulele shapes - all caught after two
survivors got tests. 20,526 melody renders byte-identical.
Looked at Twinkle on guitar and ukulele: legible; ukulele G draws
its 2-fret bar as a barre (from the shape data).


## Prefer lower positions toggle (2026-10-26, Matthew asked for it)

Checkbox in the Melody section, off by default; only changes Stay in
a position (Nearest the nut ignores it). Named in the legend and in
each note's hover text when on.

- First try, "lowest frets first, then fewest changes" over any cut,
  was degenerate: the Wellerman split into 61 positions, i.e. nearest
  the nut with brackets. Dropped.
- Built rule: when on, `_group_notes` ranks (cuts away from a phrase
  start, total of each run's lowest window fret counted once per
  note, fewest runs, most even). So a position can change at each
  phrase, never mid-phrase unless one position cannot hold the
  phrase. No tuned weights; deterministic.
- Wellerman, guitar 13 frets, width 5: off = 1 position (frets
  6-10, fret total 1431); on = 13 positions alternating about frets
  1-5 and 6-10 (total 1052). Width 6: 11 positions, total 882.
  Width 4: 13 positions, total 1218.
- Known: it hops between the low and the 6-10 block phrase by phrase
  on the Wellerman; that is the trade the toggle states.

Checked: 8 new tests (hand-worked masks, off changes nothing, only at
phrase starts, never wider than the width, legend/hover text, nearest
the nut ignores it); five rule mutations all caught; 20,526 melody
renders byte-identical.
