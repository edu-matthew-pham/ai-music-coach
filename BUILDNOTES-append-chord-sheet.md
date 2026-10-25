## The chord sheet

PLAN-chord-sheet.md, built in one session after the lever harp's
stage 2 landed (ddc30d9). A "Chords" section below Playback:
every chord on one instrument at once, with the key's notes at
the top, for preparing before playback or looking a key up with
no song loaded.

- **`chord_sheet.py` (new, plain Python, no Gradio).** The 24
  browsing keys, a key's own seven chords, the song's keys and
  the chords each plays, what the dropdown offers, and the page
  HTML. It draws nothing of its own: every picture is the one
  the mixer draws, stacked the same way, so the two cannot
  disagree.
- **Minor keys need a home-note option, so Scale gained one.**
  A minor is its relative major's seven notes with a different
  home (A minor = C's notes, A orange). Every Scale picture -
  piano, guitar, ukulele, both violins, kalimba and the harp -
  takes an optional `home=`; one helper (`_home_semitone`)
  replaces six copies of the same line. Left out, it is the
  key's own tonic, exactly as before. **All 20,526 existing
  pictures (11 instruments, 6 keys, 14 roots, 11 qualities,
  every layer) are byte-identical before and after**, the
  harp's included; the harp's Scale code was touched with
  Matthew's say-so, for this one parameter.
- **The key chosen on the sheet is never the song's key.** It is
  a view setting. The sheet's events are wired only to its own
  controls; the key and chart boxes are read, never written
  (pinned by an AST test on main.py, and checked live: the key
  box stayed F major while the sheet browsed D major).
- **The sheet always says where its key came from:** "Key: F
  major, from the song" / "Key: D major, your choice. The
  song's own key is F major." / "Key: C major. No song loaded -
  browsing." A "Back to the song" button appears only while
  browsing a song.
- **Song keys come first in the dropdown.** A piece with a key
  change ("G, Ab from beat 8") lists each stretch, and each shows
  the chords that play while its key is in force (a chord belongs
  to the key where it starts). Then all 24 browsing keys, majors
  and minors listed separately - unlike the key box, which pairs
  "C major / A minor" as one signature, because the sheet needs
  to know which note is home.
- **When the sheet switches to the song:** when the key box's
  text changes (a song loaded, or the key retyped), or the
  current choice no longer exists. An edit to the chart alone
  does not pull a browsed key back (checked live). Known edge: loading
  a different song in the *same* key while browsing another key
  keeps the browsed key - the key text did not change.
- **"A song" means the chart has chords.** The key box always
  holds a key, even on a fresh page, so it cannot be the signal.
- **Chords with no shape show the chord's notes, labelled** "No
  standard shape - showing the chord's notes." - the mixer's own
  fallback (kalimba Gm/Eb/Eb7, every instrument's diminished
  chord, guitar's rarer ones).
- **Live check, not just tests.** gradio 6.30 and the
  0.0.18 component wheel installed in the sandbox; the real
  app launched and driven in Chromium: start (C major, browsing)
  -> load the Wellerman (switches to F major "from the song",
  Dm Gm A Bb F) -> pick D major (your choice, key box unchanged,
  back button appears) -> back (hides) -> Kalimba tab (exactly
  one "no standard shape": the Gm) -> edit the chart while on A
  minor (stays). No page errors.
- **Tests:** `tests/test_chord_sheet.py`, 85. Expected chords
  written out by hand for seven keys and checked in all 24
  against the key's own notes; song sections, key changes, the
  fallbacks for stale choices; every instrument's sheet has a
  card per chord and one stacked picture each; home is orange
  on the right note for C and A minor on all 11 instrument
  variants; naming the tonic as home changes nothing. Mutation
  checked: four deliberate breakages (minor keeps the major's
  home; chords not rotated to home; harp ignores the home
  option; stale song choice not guarded) each made tests fail.
- **Not run by me:** the interface test files
  (`test_interface_wiring.py`, `test_interface_runs.py`) and the
  full suite - left for Matthew, as agreed. main.py changed, so
  those are the ones to watch.

### Open, deliberately not done

- Remembering the last instrument tab (per-viewer convenience).
- Harmonic minor (the raised seventh) - A minor here is the
  natural minor's seven notes only.
- F sharp major's seventh chord is named E#dim (the key's own
  scale spells it E#); its picture is correct.
- Every tab's pictures are drawn on each refresh (about 10 ms
  for all six); if that ever matters, draw only the visible tab.
