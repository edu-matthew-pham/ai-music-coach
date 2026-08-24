# mixer_data.py

"""
The data half of the mixer, feeding the real MusicMixer
component.

separate_layers and the timeline logic already exist and
are already tested - moving from an HTML block to a real
component changed delivery, not synthesis. This module is
the seam: it assembles the dictionary the MusicMixer
component's value expects.

as_wav_data, the timeline builder, and the opening levels
and colours used to live in mixer_block.py, the old gr.HTML
mixer. That file is gone now (main.py talks to the real
component directly); this is where they live.
"""

import base64
import io

import numpy as np
from scipy.io import wavfile

from music import LAYER_NAMES, separate_layers
from harmony import MAJOR_SCALES
from instrument_diagrams import (
    INSTRUMENTS, chord_overlay_for, scale_overlay_for, shape_overlay_for,
    structure_for
)


# Levels a part starts at. The song in its own, pure form -
# melody, bass, and chords all audible - with only the
# harmony parts silent until brought in deliberately; a
# practice click sits under all of it. Harmonies default off
# because they're the thing being learned, not because the
# rest of the song should open thin.
OPENING_LEVELS = {
    "Melody": 1.0,
    "Instrumental": 1.0,
    "Harmony above": 0.0,
    "Harmony below": 0.0,
    "Bass": 1.0,
    "Chords": 1.0,
    "Metronome": 0.5
}

# The colours the app already uses for these voices, so a
# fader and the part it moves are recognisably the same
# thing on the picture.
LAYER_COLOURS = {
    "Melody": "#2e7d32",
    "Instrumental": "#8d6e63",
    "Harmony above": "#e65100",
    "Harmony below": "#6a1b9a",
    "Bass": "#00695c",
    "Chords": "#37474f",
    "Metronome": "#90a4ae"
}

# A song with several tunes in it needs a colour per tune,
# not just for the one "Melody". The first is Melody's own
# green, so a single-tune song and the first part of a
# several-tune song look the same; the rest are chosen to
# stay apart from each other and from the derived layers'
# colours above.
PART_COLOURS = [
    "#2e7d32",
    "#1565c0",
    "#ad1457",
    "#ef6c00",
    "#4527a0",
    "#00838f"
]


def part_colour(index):
    """
    The colour for the nth tune of a several-tune song.

    Wraps rather than running out: a song with more parts
    than colours repeats them, which is worse than having
    more colours but better than drawing nothing.
    """

    return PART_COLOURS[index % len(PART_COLOURS)]


def as_wav_data(track, sample_rate):
    """
    One layer as a sound file the browser can decode.

    Sent as data inside the page rather than as a file to
    fetch, because a fetch needs a route and a route needs
    the parts to outlive the request that made them. The
    cost is size, and the size is the reason a phrase is a
    better thing to mix than a whole song.
    """

    samples = np.asarray(track, dtype=np.float32)

    # Sixteen bit, which every browser decodes, and a
    # quarter of the size of float.
    peak = float(np.max(np.abs(samples))) if len(samples) else 0.0

    if peak > 1.0:
        samples = samples / peak

    encoded = (samples * 32767).astype(np.int16)

    buffer = io.BytesIO()

    wavfile.write(buffer, sample_rate, encoded)

    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _timeline(pitch_text, duration_text, key, bpm, chart_text,
              lyric_text, phrase_label):
    """
    The bars of the chart, in seconds.

    So the mixer can follow the music rather than only play
    it: which chord is sounding now, where to jump to, and
    which stretch to go round again.

    One entry per real bar, always - not one per chord run.
    A chord spanning several bars used to swallow them (one
    box claiming to be "bar 1", nothing shown for the bars
    after); a bar with more than one chord change used to
    split into several boxes each claiming to be its own
    bar. Both are the same mistake: a box was a chord run,
    not a bar. Now every bar gets a box, whether or not
    anything is sung in it - an instrumental intro is
    present and numbered like any other bar - and a bar's
    own chord changes (including a half-beat split written
    "A>B") sit inside that one box, each carrying its
    position within the bar rather than the song.

    Beats are turned into seconds here because the browser
    should not have to know what a beat is. It knows where
    it is in a sound file, and this says what is happening
    at that moment.
    """

    from music import selected_piece
    from chords import read_chart

    piece = selected_piece(
        pitch_text, duration_text, lyric_text, key,
        chart_text, phrase_label
    )

    if not piece.chart or not piece.chart.strip():
        return []

    chords, bars = read_chart(piece.chart)

    if not bars:
        return []

    per_beat = 60.0 / float(bpm)

    # The words under each bar, so the strip reads as the
    # song rather than as a row of chord names. Matched by
    # when they are sung, which is what the picture does.
    words_at = []

    position = 0.0
    tokens = iter(piece.lyrics.split() if piece.lyrics else [])

    for pitch, length in zip(piece.pitches, piece.durations):

        if pitch != "R":

            try:
                words_at.append((position, next(tokens)))

            except StopIteration:
                pass

        position += float(length)

    strip = []

    for number, (bar_start, bar_length) in enumerate(bars):

        bar_end = bar_start + bar_length

        bar_chords = []

        for chord_start, chord_length, name in chords:

            chord_end = chord_start + chord_length

            # No overlap with this bar at all.
            if chord_end <= bar_start or chord_start >= bar_end:
                continue

            # A chord already sounding when the bar opens
            # sits at the bar's own beat 0, however far
            # back it actually started - the same rule
            # invariant 2's slicing already follows. One
            # this way, at most, per bar: a genuinely new
            # start clamps to where it really begins.
            beat_in_bar = max(chord_start, bar_start) - bar_start

            bar_chords.append({
                "name": name,
                "beat_in_bar": beat_in_bar,
                "carried": chord_start < bar_start
            })

        words = " ".join(
            word for beat, word in words_at
            if bar_start <= beat < bar_end
        )

        strip.append({
            "bar": number + 1,
            "start": bar_start * per_beat,
            "end": bar_end * per_beat,
            "beats": bar_length,
            "chords": bar_chords,
            "words": words,
            "key": piece.key_at(bar_start)
        })

    return strip


def _diagrams(key, timeline):
    """
    The instrument pictures the mixer's diagram panel
    stacks, three layers per instrument, plus one alternate
    to the chord layer:

    - structure: the instrument itself (keys, frets,
      strings), key-independent, always sent - it is not a
      toggleable layer, since a picture of marks with no
      instrument under them is illegible.
    - scale: the notes of every distinct key this piece
      actually uses, transparent, for the Scale toggle - one
      entry per key name (most pieces use only one, so this
      is a one-entry dict in the ordinary case), since a
      modulating piece's Scale layer has to show the right
      key's notes on both sides of the change, not the
      opening key for the whole song.
    - chords: one transparent overlay per distinct chord
      this song's chart actually uses, for the "Chord
      notes" toggle - every place the chord's tones occur.
    - shapes: one transparent overlay per distinct chord,
      for the "Chord shape" toggle - one concrete beginner
      voicing instead of every occurrence. Missing for a
      chord this instrument has no standard shape for
      (violin has none at all; guitar only covers major,
      minor, dominant, and minor-seventh) - the panel falls
      back to the chords entry for that one card rather
      than showing nothing.

    Every instrument is included regardless of which the
    player has toggled on - the toggle is a display choice
    the browser makes with data it already has, the same
    way the Notes and Lyrics panels already work. Asking
    Python to rebuild the mixer value every time a toggle
    changes would make the toggle a round trip instead of
    a CSS switch.

    A chord name the chart uses but the theory module
    cannot read (a typo that slipped past chart validation
    elsewhere) is skipped rather than sent broken - the
    strip still shows the name; only its picture is
    missing, which is visible and correctable rather than
    a page that fails to render.
    """

    if not key:
        return {}

    from harmony import read_key, KeyError_
    from chords import ChartError

    try:
        key_changes = read_key(key)

    except KeyError_:
        return {}

    opening_key = key_changes[0][1]

    if opening_key not in MAJOR_SCALES:
        return {}

    structure = {
        instrument: structure_for(instrument)
        for instrument in INSTRUMENTS
    }

    # One Scale overlay per distinct key the piece actually
    # uses, not just the opening one - a modulating piece's
    # Scale layer would otherwise show the wrong key's notes
    # for every bar after the change (or, before this fix,
    # the whole panel would go blank: the guard above used to
    # reject the box's own multi-key text outright, since it
    # is not itself a single valid key name). Every bar in
    # the timeline carries its own key (Piece.key_at, the
    # same lookup transpose and harmony already use), so the
    # frontend picks the right entry at the playhead.
    distinct_keys = sorted({name for _, name in key_changes})

    scale = {
        key_name: {
            instrument: scale_overlay_for(key_name, instrument)
            for instrument in INSTRUMENTS
        }
        for key_name in distinct_keys
    }

    chord_names = sorted({
        chord["name"]
        for bar in timeline
        for chord in bar["chords"]
    })

    chords = {instrument: {} for instrument in INSTRUMENTS}
    shapes = {instrument: {} for instrument in INSTRUMENTS}

    for chord_name in chord_names:
        for instrument in INSTRUMENTS:

            try:

                # Spelled in the piece's opening key. The
                # marks themselves never move with the key -
                # checked directly: chord_overlay_for("G", ...)
                # and chord_overlay_for("Ab", ...) for the
                # same chord differ only in their text labels,
                # never in a mark's position - and a single
                # chord name can occur in more than one key's
                # section of a modulating piece, so there is
                # no one key that is straightforwardly
                # "correct" to spell it in. Left as a smaller,
                # cosmetic known gap rather than solved here.
                chords[instrument][chord_name] = chord_overlay_for(
                    opening_key, instrument, chord_name
                )

                shape = shape_overlay_for(
                    opening_key, instrument, chord_name
                )

                if shape is not None:
                    shapes[instrument][chord_name] = shape

            except ChartError:
                continue

    return {
        "structure": structure,
        "scale": scale,
        "chords": chords,
        "shapes": shapes,
    }


def _note_timeline(pitch_text, duration_text, key, bpm, chart_text,
                    harmony_style, lyric_text, phrase_label,
                    part_label=None):
    """
    Every note, in seconds, pitch-placed and layer-tagged.

    Same shape as _timeline(), one level finer: a box per
    note instead of per bar, for the mixer's note view. The
    layers are read the same way separate_layers builds the
    audio for them, so the picture and the sound can never
    disagree about what the harmony or bass actually is.

    Every sung tune carries its own words underneath it,
    same as tuning_plot.py draws them: a song with several
    tunes (PLAN-multi-part.md) has real, different lyrics
    on each, and all of them are sent. The generated
    harmony and bass lines still never have their own
    lyrics - they are not independent sung parts, they are
    voices derived from whichever tune is yours.
    """

    from music import (
        harmony_line, bass_line, mark_unsung_holds,
        phrase_chosen, part_chosen, UNSUNG_HOLD
    )
    from piece import Piece
    from notes import note_to_midi, is_rest

    parts = Piece.read_parts(
        pitch_text, duration_text, lyric_text, key, chart_text
    )

    number = phrase_chosen(phrase_label)

    piece = part_chosen(parts, part_label)

    if number is not None:
        piece = piece.phrase(number)

    per_beat = 60.0 / float(bpm)

    # A held note only reads as real singing if the run
    # around it is short - a genuine melisma. A longer run
    # is an unlyriced gap, almost always instrumental, and
    # is marked "*" rather than "_" so harmony and bass (built
    # for accompanying the sung line) can leave those spots
    # out, and so a person can correct the guess by hand,
    # same as any other lyric text.
    marked_lyrics = mark_unsung_holds(piece.lyrics) if piece.lyrics else piece.lyrics
    marked_words = marked_lyrics.split() if marked_lyrics else None

    # Which sung notes are unconfirmed, by position among the
    # sung notes only (rests never reach this list at all) -
    # harmony_line and bass_line preserve rests at the same
    # positions piece.pitches has them, so this same,
    # position-matched list applies unchanged to their output
    # too.
    unsung = (
        [word == UNSUNG_HOLD for word in marked_words]
        if marked_words is not None else None
    )

    def walk(pitches, durations, colour, layer, words=None, skip=None):

        notes = []
        position = 0.0
        note_index = 0

        for pitch, length in zip(pitches, durations):

            length = float(length)

            if is_rest(pitch):
                position += length
                continue

            if skip is not None and note_index < len(skip) and skip[note_index]:
                note_index += 1
                position += length
                continue

            entry = {
                "start": position * per_beat,
                "length": length * per_beat,
                "midi": note_to_midi(pitch),
                "layer": layer,
                "colour": colour
            }

            if words is not None and note_index < len(words):
                entry["word"] = words[note_index]

            notes.append(entry)
            note_index += 1
            position += length

        return notes

    all_notes = []

    # Every sung tune shows every note - nothing is ever
    # hidden from view or from editing. Only its word label
    # changes, "*" instead of "_", which is the guess
    # itself, sitting where it can be corrected.
    #
    # A single, undivided song has one tune and it is still
    # called "Melody", so every existing test and every
    # existing reader of that name keeps working. A song
    # with dividers sends each tune under its own name,
    # with its own words.
    named_parts = [name for name, _ in parts]

    if named_parts == [None]:

        all_notes += walk(
            piece.pitches, piece.durations, LAYER_COLOURS["Melody"],
            "Melody", words=marked_words
        )

    else:

        for index, (name, part_piece) in enumerate(parts):

            if number is not None:
                part_piece = part_piece.phrase(number)

            if name == (part_label or named_parts[0]):
                part_words = marked_words

            else:
                part_marked = (
                    mark_unsung_holds(part_piece.lyrics)
                    if part_piece.lyrics else part_piece.lyrics
                )

                part_words = part_marked.split() if part_marked else None

            all_notes += walk(
                part_piece.pitches, part_piece.durations,
                part_colour(index), name, words=part_words
            )

    for name, steps in (("Harmony above", 2), ("Harmony below", -2)):

        harmony = harmony_line(
            piece.pitches, piece.durations, key,
            steps=steps, style=harmony_style, chart_text=piece.chart
        )

        # harmony_line still computes a note for every
        # position, unsung ones included - full information,
        # nothing hidden from the calculation itself. Only
        # the unsung positions are left out of what actually
        # reaches the mixer.
        all_notes += walk(
            harmony, piece.durations, LAYER_COLOURS[name], name,
            skip=unsung
        )

    if piece.chart and piece.chart.strip():

        bass = bass_line(piece.pitches, piece.durations, piece.chart)

        all_notes += walk(
            bass, piece.durations, LAYER_COLOURS["Bass"], "Bass",
            skip=unsung
        )

    return all_notes


def _continue_with_other_parts(own_phrases, part_label, phrases_by_part):
    """
    Your part's phrases, carried on by the other parts' once
    yours have finished.

    While your part is singing, its own phrases set the pages
    - nothing here touches them; a page break inside one of
    your phrases would cut you mid-line, and three staggered
    voices cannot all be whole on one page (checked: any page
    holding one voice's phrase whole cuts the others' - the
    only way round it is not to page at all). So exactly one
    voice's phrasing wins at a time, and while you sing it is
    yours.

    Once you have stopped, that objection is gone: every break
    any remaining voice makes becomes a page break, and the
    pages after yours are the UNION of the remaining parts'
    phrase boundaries - as fine as any of them cuts it. Each
    page is labelled and tagged with the part whose phrase
    begins there. An earlier version picked ONE remaining
    part's phrase list and dropped the others' - which needed
    a tie-break rule between them, and every rule tried
    (shorter first, part order) turned out to measure the
    wrong thing on a synthetic three-way stagger: preferring
    a part because its FIRST carried-on phrase was short
    could pick the COARSER overall phrasing. The union has no
    such choice to make.

    Nothing of yours is cut, nothing of anyone's is unshown,
    and there is no hole between your last page and the next.
    Ordinary single-tune songs have no other parts and pass
    straight through unchanged.
    """

    if not phrases_by_part or not own_phrases:
        return own_phrases

    finished_at = own_phrases[-1]["end"]

    # Every moment after yours where ANY remaining part starts
    # or ends a phrase, plus your own end (the first page's
    # start) - these are the only places a page may break.
    cuts = {finished_at}

    for name, theirs in phrases_by_part.items():

        if name == part_label:
            continue

        for phrase in theirs:

            if phrase["end"] <= finished_at:
                continue

            cuts.add(max(phrase["start"], finished_at))
            cuts.add(phrase["end"])

    cuts = sorted(cuts)

    tail = []

    for start, end in zip(cuts, cuts[1:]):

        # Which part's phrase begins here (or is going here,
        # for a stretch inside someone's phrase). Prefer one
        # that BEGINS at this cut - it named the break; fall
        # back to any part sounding through it, so a stretch
        # is never unlabelled. Part order breaks a genuine tie
        # (two parts beginning a phrase at the same instant),
        # the order the singer already sees everywhere else.
        owner = None
        owner_label = None

        for name in phrases_by_part:

            if name == part_label:
                continue

            for phrase in phrases_by_part[name]:

                # A phrase already over by this cut cannot own
                # it - without this, clipping every phrase's
                # start up to `finished_at` made all of them
                # "begin" there and the first in the list won,
                # labelling the tail with a line sung long ago
                # (a real bug: "Voice 2: 1. Row row row" over
                # what was in fact its "Life is but a dream").
                if phrase["end"] <= start + 1e-9:
                    continue

                begins_here = abs(max(phrase["start"], finished_at) - start) < 1e-9
                sounding = phrase["start"] <= start + 1e-9 and phrase["end"] > start + 1e-9

                if begins_here:
                    owner, owner_label = name, phrase["label"]
                    break

                if sounding and owner is None:
                    owner, owner_label = name, phrase["label"]

            if owner is not None and begins_here:
                break

        if owner is None:
            # A stretch no remaining part is singing through
            # (a rest all of them share). Not a page.
            continue

        tail.append({
            "start": start,
            "end": end,
            "label": f"{owner}: {owner_label}",
            # Whose phrase this is, so a panel that draws
            # words can fetch that part's rather than yours
            # (which has none here - you have finished).
            "part": owner
        })

    return own_phrases + tail


def _phrase_timeline(pitch_text, duration_text, key, bpm, lyric_text,
                      part_label=None, chart_text=None):
    """
    Where each phrase starts and ends, in seconds, with a
    label to click on.

    A phrase is a line of the lyrics - the same unit the
    retired phrase dropdown used, read the same way, via
    Piece.phrases(), and labelled the same way it was: the
    opening words of that line, so a phrase reads as
    something a person recognises rather than a number.

    Falls back to treating the whole piece as one phrase
    when there is no more than one - matching the dropdown,
    which showed only "Whole part" in that case.

    Phrases belong to whichever tune is yours: in a song
    with several tunes each has its own words and so its
    own lines to sing, and the strip should follow the one
    being sung rather than the first one written.
    """

    from piece import Piece, split_parts
    from music import MusicInputError, part_chosen
    from midi_import import join_syllables

    try:
        parts = Piece.read_parts(
            pitch_text, duration_text, lyric_text
        )

        piece = part_chosen(parts, part_label)

        sections = split_parts(pitch_text, duration_text, lyric_text)

    except MusicInputError:
        return []

    # The labels below are read off the lyric box's own
    # lines, so they have to come from this tune's section
    # of it rather than the whole box.
    for name, _, _, section_lyrics in sections:

        if name == part_label or (
            part_label is None and name == sections[0][0]
        ):
            lyric_text = section_lyrics
            break

    found = piece.phrases()

    if len(found) <= 1:
        return []

    # Gap pages exist only for an undivided song. In a song
    # with several tunes, one voice's rests are not silence
    # at all - another voice is singing there, and the
    # carried-on paging (_continue_with_other_parts) already
    # owns that time. Paging it "(rest)" here would claim it
    # twice and call a duet's answer silence.
    undivided = len(sections) == 1 and sections[0][0] is None

    per_beat = 60.0 / float(bpm)

    durations = [float(length) for length in piece.durations]

    lines = [
        line for line in (lyric_text or "").split("\n")
        if line.strip()
    ]

    from notes import is_rest
    from music import mark_unsung_holds

    if not undivided:

        # A song with several tunes pages exactly as it
        # always has: one page per lyric line, trimmed to
        # the last sung note, the gap after it left to the
        # carried-on paging. A page is the singing, not the
        # silence after it.
        phrases = []

        for position, (first, last) in enumerate(found):

            if position < len(lines):
                label = join_syllables(lines[position].split())
            else:
                label = " ".join(piece.pitches[first:first + 5])

            last_sung = last

            while last_sung > first and is_rest(piece.pitches[last_sung]):
                last_sung -= 1

            phrases.append({
                "start": sum(durations[:first]) * per_beat,
                "end": sum(durations[:last_sung + 1]) * per_beat,
                "label": f"{position + 1}. {label}"
            })

        return phrases

    # A line with no real word left after marking is not a
    # phrase anyone sings - it is unowned time (the imported
    # intro, an instrumental break written as held notes).
    # A SHORT all-hold line is different: a genuine melisma
    # carrying the previous line's word across a break, so
    # the marked tokens ("*" only past a real melisma's
    # length) are what decide, not the raw "_".
    marked_lines = [
        line for line in mark_unsung_holds(
            "\n".join(lines)
        ).split("\n")
    ] if lines else []

    def line_is_sung(index):
        if index >= len(marked_lines):
            return True
        tokens = marked_lines[index].split()
        return any(token != "*" for token in tokens)

    # Per-note: does this position sound but belong to no
    # singer ("*" after marking)? Rests are not unsung -
    # they are nothing at all - and a note past the lyric
    # tokens is treated as sung rather than guessed about.
    marked_tokens = iter(
        token
        for line in marked_lines
        for token in line.split()
    )

    note_unsung = []

    for pitch in piece.pitches:
        if is_rest(pitch):
            note_unsung.append(False)
        else:
            note_unsung.append(next(marked_tokens, None) == "*")

    def unowned(index):
        return is_rest(piece.pitches[index]) or note_unsung[index]

    starts = [0.0]
    for length in durations:
        starts.append(starts[-1] + length)

    def beat_at(index):
        return starts[index]

    # The real bar grid, for cutting gap pages where the
    # chart strip already draws lines. Without a chart the
    # song has no bars on screen at all, so a plain
    # four-beat bar stands in.
    from chords import read_chart

    bar_starts = []
    bar_len = 4.0

    if chart_text and chart_text.strip():
        try:
            _, chart_bars = read_chart(chart_text)
            bar_starts = [start for start, _ in chart_bars]
            if chart_bars:
                bar_len = float(chart_bars[0][1])
        except Exception:
            pass

    EPSILON = 1e-6
    PAGE_BARS = 4
    FOLD_BARS = 1

    # Sung phrases first, trimmed to their sung notes at
    # both ends; everything between them pools into gaps.
    sung = []

    for position, (first, last) in enumerate(found):

        if not line_is_sung(position):
            continue

        first_sung = first
        while first_sung < last and unowned(first_sung):
            first_sung += 1

        last_sung = last
        while last_sung > first_sung and unowned(last_sung):
            last_sung -= 1

        if position < len(lines):
            label = join_syllables(lines[position].split())
        else:
            label = " ".join(piece.pitches[first:first + 5])

        sung.append({
            "first": first_sung,
            "last": last_sung,
            "label": label,
        })

    if not sung:
        return []

    def gap_pages(gap_start, gap_end, first_note, last_note):
        """
        Greedy pages for a stretch nobody sings: fill each
        to PAGE_BARS before starting the next, cut on the
        real bar grid where one exists. Named for what is
        heard there - "(instrumental)" when notes sound,
        "(rest)" when it is true silence a singer counts
        through.
        """

        sounding = any(
            not is_rest(pitch)
            for pitch in piece.pitches[first_note:last_note]
        )
        label = "(instrumental)" if sounding else "(rest)"

        pages = []
        cursor = gap_start

        while gap_end - cursor > PAGE_BARS * bar_len + EPSILON:

            target = cursor + PAGE_BARS * bar_len
            cuts = [
                c for c in bar_starts
                if cursor + EPSILON < c <= target + EPSILON
            ]
            cut = max(cuts) if cuts else target

            pages.append((cursor, cut, label))
            cursor = cut

        pages.append((cursor, gap_end, label))
        return pages

    # Walk the sung phrases, deciding each gap's fate as it
    # is reached: folded forward when short, paged when long.
    built = []

    previous_end = 0.0
    previous_end_note = 0

    for entry in sung:

        phrase_start = beat_at(entry["first"])
        phrase_end = beat_at(entry["last"] + 1)

        gap = phrase_start - previous_end

        if gap > FOLD_BARS * bar_len + EPSILON:

            pages = gap_pages(
                previous_end, phrase_start,
                previous_end_note, entry["first"]
            )

            # A sliver left over after the full pages folds
            # forward, the same rule a short gap follows.
            tail_start, tail_end, tail_label = pages[-1]

            if tail_end - tail_start <= FOLD_BARS * bar_len + EPSILON:
                pages = pages[:-1]
                phrase_start = tail_start

            for page_start, page_end, page_label in pages:
                built.append((page_start, page_end, page_label))

        elif gap > EPSILON:
            phrase_start = previous_end

        built.append((phrase_start, phrase_end, entry["label"]))

        previous_end = phrase_end
        previous_end_note = entry["last"] + 1

    # An outro: unowned time after the last sung note, with
    # nothing ahead to fold into - paged when long, left
    # unowned when short, exactly as before this existed.
    song_end = beat_at(len(piece.pitches))

    if song_end - previous_end > FOLD_BARS * bar_len + EPSILON:
        for page_start, page_end, page_label in gap_pages(
            previous_end, song_end,
            previous_end_note, len(piece.pitches)
        ):
            built.append((page_start, page_end, page_label))

    return [
        {
            "start": start * per_beat,
            "end": end * per_beat,
            "label": f"{number + 1}. {label}",
        }
        for number, (start, end, label) in enumerate(built)
    ]


def mixer_data(
    pitch_text,
    duration_text,
    key,
    bpm=120,
    chart_text="",
    harmony_style="Thirds, chord-corrected",
    lyric_text="",
    phrase_label=None,
    part_label=None
):
    """
    The dictionary a MusicMixer component's value expects.

    loop_start and loop_end are left unset here: those are
    the browser's to fill in, and a freshly built mixer
    should open with nothing looped.

    `parts` and `part` carry a several-tune song's own
    division: what the tunes are called, and which one is
    yours. Both are sent every time - `parts` is empty for
    an undivided song, which is how the browser knows not
    to offer a chooser at all.
    """

    from music import part_names

    tunes = part_names(pitch_text, duration_text, lyric_text)

    # A name carried over from the previous song means
    # nothing if this song does not have it - and an
    # undivided song has no names at all, so a stale
    # "Voice 1" from the song before must not reach the
    # browser, whose Lyrics panel would look for words on
    # a tune this song does not contain and find none.
    if part_label not in tunes:
        part_label = tunes[0] if tunes else None

    sample_rate, tracks = separate_layers(
        pitch_text, duration_text, key, bpm, chart_text,
        harmony_style, lyric_text, phrase_label, part_label
    )

    layers = []

    # The tunes come first, in the order they are written,
    # then the derived layers in their long-standing order.
    # An undivided song has no tunes of its own and falls
    # straight through to LAYER_NAMES, which still starts
    # with "Melody" - so its fader list is unchanged.
    for index, name in enumerate(tunes):

        track = tracks.get(name)

        if track is None:
            continue

        layers.append({
            "name": name,
            "level": 1.0,
            "colour": part_colour(index),
            "wav": as_wav_data(track, sample_rate)
        })

    for name in LAYER_NAMES:

        if name in tunes:
            continue

        track = tracks.get(name)

        if track is None:
            continue

        layers.append({
            "name": name,
            "level": OPENING_LEVELS.get(name, 0.0),
            "colour": LAYER_COLOURS.get(name, "#37474f"),
            "wav": as_wav_data(track, sample_rate)
        })

    timeline = _timeline(
        pitch_text, duration_text, key, bpm, chart_text,
        lyric_text, phrase_label
    )

    notes = _note_timeline(
        pitch_text, duration_text, key, bpm, chart_text,
        harmony_style, lyric_text, phrase_label, part_label
    )

    # Every tune's phrases, by name, for showing several
    # singers' words side by side. Empty for an ordinary
    # song, which has no tunes to name.
    phrases_by_part = {
        name: _phrase_timeline(
            pitch_text, duration_text, key, bpm, lyric_text, name,
            chart_text
        )
        for name in tunes
    }

    own_phrases = _phrase_timeline(
        pitch_text, duration_text, key, bpm, lyric_text,
        part_label, chart_text
    )

    phrases = _continue_with_other_parts(
        own_phrases, part_label, phrases_by_part
    )

    diagrams = _diagrams(key, timeline)

    return {
        "layers": layers,
        "timeline": timeline,
        "notes": notes,
        "phrases": phrases,
        "phrases_by_part": phrases_by_part,
        "diagrams": diagrams,
        "bpm": float(bpm),
        "parts": tunes,
        "part": part_label,
        "loop_start": None,
        "loop_end": None
    }


def loop_region(mixer_value):
    """
    The stretch a person selected, in seconds - or None if
    nothing is looped.

    This is what a Compare handler reads once the mixer's
    value comes back from the browser: the loop a person
    chose by ear is what they should be judged against.
    """

    if not mixer_value:
        return None

    start = mixer_value.get("loop_start")
    end = mixer_value.get("loop_end")

    if start is None or end is None:
        return None

    return start, end


def part_selected(mixer_value):
    """
    Which tune the person is singing, as the mixer reports
    it - or None when there is no mixer yet, or the song
    has only one tune.

    The same shape loop_region has, and read at the same
    moment: the browser owns this choice, because switching
    tunes there must not rebuild anything.
    """

    if not mixer_value:
        return None

    return mixer_value.get("part")


def loop_notes(pitch_text, duration_text, lyric_text, key,
               chart_text, mixer_value, part_label=None):
    """
    The stretch of the music a selected loop covers, as a
    Piece - or None if nothing is usably selected.

    The reverse of the walk _note_timeline does: that walk
    turns each note's beat position into seconds; this reads
    seconds back and finds which notes they cover. Uses the
    bpm the mixer was built at, carried in mixer_value,
    rather than whatever the BPM box currently says - the
    loop's seconds were fixed at build time and mean nothing
    at a tempo chosen afterwards.

    A small tolerance absorbs float rounding across the
    beats-to-seconds-and-back trip, not genuine ambiguity
    about which notes were meant - it is far smaller than
    any real note.
    """

    from piece import Piece
    from music import part_chosen

    region = loop_region(mixer_value)

    if region is None:
        return None

    loop_start, loop_end = region
    bpm = mixer_value.get("bpm")

    if not bpm:
        return None

    # The loop's seconds are measured against whichever
    # tune is being sung, not against the first one written:
    # in a several-tune song the parts run the same length
    # but their notes fall in different places.
    piece = part_chosen(
        Piece.read_parts(
            pitch_text, duration_text, lyric_text, key, chart_text
        ),
        part_label
    )

    per_beat = 60.0 / float(bpm)
    starts = piece.starts()

    TOLERANCE = 0.05

    first = None
    last = None

    for index, beat_start in enumerate(starts):

        seconds = beat_start * per_beat

        if loop_start - TOLERANCE <= seconds < loop_end + TOLERANCE:

            if first is None:
                first = index

            last = index

    if first is None:
        return None

    return piece.slice(first, last)