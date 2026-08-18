# music.py

import numpy as np

from chords import chord_semitones, transpose_chart

from playback import (
    make_melody,
    make_accompaniment,
    keep_in_range,
    mix_tracks,
    make_count_in,
    add_metronome,
    COUNT_IN_BEATS
)

from key_detector import (
    describe_key,
    detect_key,
    plausible_keys
)
from harmony import (
    make_harmony,
    make_chord_harmony,
    make_bass,
    keys_containing,
    notes_outside,
    read_key,
    format_key,
    key_at,
    KeyError_,
    MAJOR_SCALES,
    RELATIVE_MINORS
)

from notes import (
    split_note, is_rest, REST, NOTE_SEMITONES,
    note_to_midi, midi_to_note
)

from compare import compare_sequence, summarise

from tuning_plot import (
    make_tuning_plot,
    make_performance_plot
)

from pitch_detector import (
    detect_single_note,
    detect_sequence,
    trace_performance,
    prepare_audio,
    trim_leading_silence
)

from instrument_detector import (
    detect_instrument
)


# How far out of tune a note may be before it is worth
# mentioning. Around 15 cents is roughly where a listener
# starts to notice on a sustained note.
TUNING_TOLERANCE_CENTS = 15


class MusicInputError(ValueError):
    """
    Something about the music the user typed does not work.

    The message is written to be shown to them directly, so
    it should say what is wrong and what would fix it.
    """


def check_note_names(pitches):
    """
    Make sure every pitch is a note name we understand.
    """

    for pitch in pitches:

        if is_rest(pitch):
            continue

        if len(pitch) < 2 or not pitch[-1].isdigit():
            raise MusicInputError(
                f"'{pitch}' is not a note. Notes look like "
                f"C4, F#4 or Bb3."
            )

        try:
            split_note(pitch)

        except ValueError:
            raise MusicInputError(
                f"'{pitch}' is not a note. Notes look like "
                f"C4, F#4 or Bb3."
            )


def check_bpm(bpm):
    """
    Make sure the tempo is a usable number.
    """

    try:
        bpm = float(bpm)

    except (TypeError, ValueError):
        raise MusicInputError(
            "The tempo must be a number."
        )

    if bpm <= 0:
        raise MusicInputError(
            "The tempo must be greater than zero."
        )

    return bpm


def describe_key_fit(pitches, durations=None, key="C"):
    """
    How well the chosen key suits the music.

    The key is the player's to choose, so this reports
    rather than refuses. Notes outside the key are still
    harmonised, at the nearest note in the scale, and are
    named here so the resulting interval is no surprise.

    `key` is either a single key name or a full timeline -
    a list of (beat, name) pairs - for a piece that
    genuinely modulates: each note is checked against
    whichever key was actually in force at its own beat.

    Returns a sentence, or None when everything fits.
    """

    outside = notes_outside(pitches, durations, key)

    if len(outside) == 0:
        return None

    named = ", ".join(outside)

    key_changes = [(0.0, key)] if isinstance(key, str) else key

    # A single sentence naming "the key" only makes sense
    # when there is one - a modulating piece checked each
    # note against whichever key was actually in force at
    # its own beat, not one key for the whole count, so the
    # sentence says that instead of naming just the opening
    # one and quietly misdescribing the rest.
    description = (
        f"{key_changes[0][1]} major" if len(key_changes) == 1
        else "the key in force at that point"
    )

    return (
        f"{len(outside)} notes fall outside {description} "
        f"({named}). They will be harmonised at the "
        f"nearest note in the scale."
    )


def describe_tuning(pitch):
    """
    Turn a Pitch into a short readable tuning comment.
    """

    if pitch.is_in_tune(TUNING_TOLERANCE_CENTS):
        return "in tune"

    cents = round(pitch.cents)

    if cents > 0:
        return f"{cents} cents sharp"

    return f"{abs(cents)} cents flat"


def describe_pitch(pitch):
    """
    Format one detected pitch for display.

    Notes that are close enough are shown as just a name,
    so that only the notes worth attention are annotated.
    """

    if pitch is None:
        return "?"

    if pitch.is_in_tune(TUNING_TOLERANCE_CENTS):
        return pitch.note

    return f"{pitch.note}({round(pitch.cents):+d})"


def read_beats(text):
    """
    Read one note length from the durations box.

    Lengths are written in beats. A plain number is the
    usual case, and a fraction such as 1/3 is there for
    triplets, which have no exact decimal: writing 0.3333
    is both uglier and slightly wrong.

        1      one beat
        0.5    half a beat
        1.5    a dotted beat
        1/3    one note of a triplet
        2/3    two thirds of a beat
    """

    text = text.strip()

    if "/" in text:

        top, _, bottom = text.partition("/")

        try:
            value = float(top) / float(bottom)

        except (ValueError, ZeroDivisionError):
            raise MusicInputError(
                f"'{text}' is not a length. Fractions look "
                f"like 1/3."
            )

    else:

        try:
            value = float(text)

        except ValueError:
            raise MusicInputError(
                f"'{text}' is not a number of beats."
            )

    if value <= 0:
        raise MusicInputError(
            "Every note must last longer than zero beats."
        )

    return value


def read_chords(chart_text, durations=None):
    """
    Read the chord chart, checked against the music.

    A chart and a melody are separate sequences over one
    clock, so they need not line up note for note, but they
    do have to last the same time. When they do not, one of
    them is wrong, and saying which bar the count reaches
    is more use than saying the totals differ.

    Returns (chords, bars), both empty when no chart is
    given, since chords are optional.
    """

    from chords import read_chart, ChartError

    if chart_text is None or chart_text.strip() == "":
        return [], []

    try:
        chords, bars = read_chart(chart_text)

    except ChartError as problem:
        raise MusicInputError(str(problem))

    if durations is None:
        return chords, bars

    music_beats = sum(durations)

    chart_length = 0.0

    if bars:
        last_start, last_length = bars[-1]
        chart_length = last_start + last_length

    # A chart is written in whole beats, and music does not
    # have to end on one: a phrase closing on the second
    # half of a beat still sits under a chord that lasts
    # the whole of it. So the chart may run past the end of
    # the music by up to a beat, and may not fall short of
    # it at all.
    if (
        chart_length < music_beats - 0.01
        or chart_length >= music_beats + 1
    ):

        raise MusicInputError(
            f"The chart covers {chart_length:g} beats in "
            f"{len(bars)} bars, but the music lasts "
            f"{music_beats:g} beats. They have to be the "
            f"same length."
        )

    return chords, bars


def sung_count(pitches):
    """
    How many of these entries are actually sung.
    """

    return len([
        pitch for pitch in pitches
        if not is_rest(pitch)
    ])


def lyric_line_breaks(lyric_text):
    """
    Which syllable each line of the lyrics begins on.

    A line of a song is a phrase. Nothing in a MIDI file
    says reliably where those fall - some files have no
    rests, some are not written to bars at all - but anyone
    who knows the song can see it at a glance, and typing
    it is a keystroke.

    So the phrase boundaries live in the lyrics box, as the
    line breaks a person would type anyway:

        There once was a ship that put to sea
        The name of the ship was the Bil- ly o' Tea

    Returns the syllable numbers where lines begin, not
    counting the first. Empty when there is one line or no
    lyrics, which means one phrase.
    """

    if not lyric_text:
        return []

    breaks = []

    counted = 0

    lines = lyric_text.split("\n")

    for position in range(len(lines)):

        syllables = lines[position].split()

        if not syllables:
            continue

        if counted:
            breaks.append(counted)

        counted += len(syllables)

    return breaks


def phrases_from_lyrics(pitches, durations, lyric_text):
    """
    Where each phrase begins and ends, from the lyrics.

    Returns a list of (first note, last note) pairs, one
    per line of the lyrics. With no lyrics, or one line,
    the whole thing is a single phrase.

    Syllables are counted against sung notes, so a rest
    between two lines belongs to the line it follows: the
    breath at the end of a phrase is part of that phrase,
    not the start of the next.
    """

    if not pitches:
        return []

    breaks = lyric_line_breaks(lyric_text)

    if not breaks:
        return [(0, len(pitches) - 1)]

    # Syllable numbers count only sung notes, while the
    # music counts rests too.
    sung_to_note = [
        position for position in range(len(pitches))
        if not is_rest(pitches[position])
    ]

    starts = [0]

    for syllable in breaks:

        if syllable < len(sung_to_note):
            starts.append(sung_to_note[syllable])

    phrases = []

    for position in range(len(starts)):

        first = starts[position]

        if position + 1 < len(starts):
            last = starts[position + 1] - 1

        else:
            last = len(pitches) - 1

        if last >= first:
            phrases.append((first, last))

    return phrases


def read_lyrics(lyric_text, note_count):
    """
    Turn a lyrics textbox into one syllable per note.

    The notation follows engraving convention, as used by
    MuseScore and printed music:

        Twin- kle twin- kle lit- tle star

    A trailing hyphen means the word continues on the next
    note. An underscore means the previous syllable is held
    through this note (a melisma), and is shown as nothing.

    An empty box means no lyrics, which is always allowed.
    """

    if lyric_text is None or lyric_text.split() == []:
        return None

    syllables = lyric_text.split()

    if len(syllables) != note_count:
        raise MusicInputError(
            f"There are {note_count} sung notes but "
            f"{len(syllables)} syllables. Each note needs "
            f"one syllable, or _ to hold the previous one. "
            f"Rests do not take a syllable."
        )

    return syllables


# The same marker read_lyrics/lyric_line_breaks already use
# for a held note - matched here by value rather than a
# shared import, the same way PHRASE_REST is defined
# separately in midi_import.py and musicxml_import.py rather
# than centralised for one literal.
HELD_SYLLABLE = "_"

# What an unconfirmed hold is marked as - visually distinct
# from both "_" (held, confirmed) and "-" (word continues),
# and not a character that would plausibly appear in real
# sung lyric text.
UNSUNG_HOLD = "*"

# A held note ("_") only reads as real singing if the run of
# them around it is short - a genuine melisma, checked
# against every real example this app has been tested
# against, never ran past 2 held notes in a row. A run past
# this is something else: an instrumental passage with no
# singing at all, which also shows up as a string of held
# notes, since every non-rest note needs some token.
# Deliberately generous - set with margin above the real
# ceiling, not tuned to a razor's edge, because the only
# failure mode of guessing too high is still treating a few
# instrumental notes as sung, same as today's baseline
# before this existed. Guessing too low would wrongly mark
# real singing as not sung, which this stays well clear of.
MAX_MELISMA_RUN = 3


def mark_unsung_holds(lyric_text, max_run=MAX_MELISMA_RUN):
    """
    Tell a real held note apart from an unlyriced gap.

    "_" already means two different things: a syllable
    genuinely held from the word before it, and a note with
    no lyric signal at all - most often an instrumental
    passage, which gets the same token because every sung
    note needs one. A run of "_" longer than a real melisma
    ever runs is marked "*" instead - still no word, but now
    saying plainly that nothing here is confirmed sung.

    This is a guess, not a fact the file states, and it is
    demoted the same way every other guess in this app is:
    written into the lyrics box where a keystroke corrects
    it, swapping "*" back to "_" or the reverse. Nothing
    downstream re-derives this after the box is edited - the
    box is what it says, same as lyric text always is.

    A run is judged as a whole, not truncated - nine
    consecutive held notes are marked "*" together, not the
    first three kept and the rest dropped. There is no
    principled place to cut a long run in half, and judging
    the whole run at once never wrongly excludes real
    singing part-way through an unusually long but genuine
    melisma.

    Line breaks (phrases) do not interrupt a run - a held
    stretch that happens to straddle a phrase boundary is
    still one run, counted on the notes alone.

    Only "_" tokens are ever touched. A real word, and the
    line structure itself, come back unchanged.
    """

    if not lyric_text:
        return lyric_text

    lines = lyric_text.split("\n")

    tokens = []
    owning_line = []

    for line_index, line in enumerate(lines):
        for token in line.split():
            tokens.append(token)
            owning_line.append(line_index)

    marked = list(tokens)

    run_start = None

    for position in range(len(tokens) + 1):

        held = position < len(tokens) and tokens[position] == HELD_SYLLABLE

        if held and run_start is None:
            run_start = position

        elif not held and run_start is not None:

            if position - run_start > max_run:

                for held_position in range(run_start, position):
                    marked[held_position] = UNSUNG_HOLD

            run_start = None

    rebuilt_lines = [[] for _ in lines]

    for token, line_index in zip(marked, owning_line):
        rebuilt_lines[line_index].append(token)

    return "\n".join(" ".join(line) for line in rebuilt_lines)


def read_music(pitch_text, duration_text):
    """
    Turn textbox input into Python lists.
    """

    pitches = pitch_text.split()
    duration_strings = duration_text.split()

    if len(pitches) == 0:
        raise MusicInputError(
            "Enter some notes first, such as C4 D4 E4."
        )

    check_note_names(pitches)

    durations = []

    for duration in duration_strings:
        durations.append(
            read_beats(duration)
        )

    if len(pitches) != len(durations):
        raise MusicInputError(
            f"There are {len(pitches)} notes but "
            f"{len(durations)} durations. "
            f"Each note needs one duration."
        )

    return pitches, durations



# The parts a piece can sound, in the order a mixer shows
# them. Named once here so the synthesis, the sliders and
# anything that plays them separately cannot drift apart.
LAYER_NAMES = [
    "Melody",
    "Harmony above",
    "Harmony below",
    "Bass",
    "Chords",
    "Metronome"
]


def separate_layers(
    pitch_text,
    duration_text,
    key,
    bpm=120,
    chart_text="",
    harmony_style="Thirds, chord-corrected",
    lyric_text="",
    phrase_label=None
):
    """
    Every part of the music, unmixed and at full level.

    play_music scales these by their levels and adds them
    together, which is what a finished recording needs. A
    mixer needs them apart: six sounds playing together,
    each with its own control, so a level can move while
    they are sounding instead of asking for the whole
    thing to be made again.

    Returns (sample_rate, layers) where layers is a
    dictionary keyed by LAYER_NAMES. A part the music
    cannot sound - bass or chords with no chart - is
    absent rather than silent, so a mixer can say why a
    fader does nothing.
    """

    piece = selected_piece(
        pitch_text, duration_text, lyric_text, key,
        chart_text, phrase_label
    )

    pitches = piece.pitches
    durations = piece.durations
    chart_text = piece.chart

    bpm = check_bpm(bpm)

    chords, bars = read_chords(chart_text, durations)

    layers = {}

    sample_rate, melody_track = make_melody(
        pitches, durations, bpm
    )

    layers["Melody"] = melody_track

    for name, steps in (
        ("Harmony above", 2),
        ("Harmony below", -2)
    ):

        harmony = harmony_line(
            pitches,
            durations,
            key,
            steps=steps,
            style=harmony_style,
            chart_text=chart_text
        )

        sample_rate, track = make_melody(harmony, durations, bpm)

        layers[name] = track

    if chords:

        sample_rate, bass_track = make_melody(
            bass_line(pitches, durations, chart_text),
            durations,
            bpm
        )

        layers["Bass"] = bass_track

        voiced = [
            (start, length, chord_semitones(name))
            for start, length, name in chords
        ]

        layers["Chords"] = make_accompaniment(
            voiced,
            bars,
            sum(durations),
            bpm,
            sample_rate
        )

    layers["Metronome"] = add_metronome(
        [0.0] * len(melody_track),
        sum(durations),
        bpm,
        sample_rate,
        bars=bars
    )

    return sample_rate, layers


def play_music(
    pitch_text,
    duration_text,
    key,
    melody_level=1.0,
    harmony_above_level=0.0,
    harmony_below_level=0.0,
    bpm=120,
    metronome_level=0.5,
    chart_text="",
    chords_level=0.0,
    harmony_style="Thirds, chord-corrected",
    bass_level=0.0,
    lyric_text="",
    phrase_label=None
):
    """
    Build the playback from independent layers, mixed.

    Each part has a level between nought and one, read at
    the moment of generating: nought is silence, anything
    above it is that part at that loudness. Both harmony
    lines exist at once - a third above the tune and a
    third below - each with its own level, which is how a
    quiet harmony can sit under a full melody instead of
    matching it or being absent.

    Everything at nought still clicks, so the result is
    never silence that looks like a failure.
    """

    sample_rate, parts = separate_layers(
        pitch_text,
        duration_text,
        key,
        bpm,
        chart_text,
        harmony_style,
        lyric_text,
        phrase_label
    )

    # Built once, above, and scaled here. The two used to
    # be one piece of code that made only the parts it was
    # going to play; separating them means a mixer and a
    # recording sound the same, because they are the same
    # layers.
    levels = {
        "Melody": melody_level,
        "Harmony above": harmony_above_level,
        "Harmony below": harmony_below_level,
        "Bass": bass_level,
        "Chords": chords_level
    }

    layers = []

    for name, level in levels.items():

        if level <= 0:
            continue

        track = parts.get(name)

        if track is None:

            # Asked for a part the music cannot sound. The
            # fader doing nothing in silence is worse than
            # being told why: both of these need a chart,
            # and the player is one box away from having
            # one.
            raise MusicInputError(
                "A bass part sings the root of each chord, "
                "so it needs a chord chart. Write one in "
                "the Chords box, such as | C . . . | F . C . |"
                if name == "Bass" else
                "There is no chord chart to play. Write one "
                "in the Chords box, such as | C . . . | F . C . |"
            )

        layers.append([sample * level for sample in track])

    total_samples = len(parts["Melody"])

    if len(layers) == 0:
        sound = [0.0] * total_samples

    elif len(layers) == 1:
        sound = layers[0]

    else:
        sound = layers[0]

        for extra in layers[1:]:
            sound = mix_tracks(sound, extra)

    # The metronome always clicks when there are no notes,
    # so turning everything down gives a click track for
    # practising to rather than silence.
    click_level = metronome_level

    if len(layers) == 0:
        click_level = max(click_level, 0.5)

    if click_level > 0:

        clicks = parts["Metronome"]

        # Added, not averaged in: mixing halves both sides
        # to stop them doubling, which would make the
        # failsafe click half as loud as it promises to
        # be. The limiter below already guards the sum.
        sound = [
            sample + click * click_level
            for sample, click in zip(sound, clicks)
        ]

    # Four layers can add up past what a speaker can play,
    # which sounds broken rather than loud.
    sound = keep_in_range(sound)

    audio_data = np.array(
        sound,
        dtype=np.float32
    )

    return sample_rate, audio_data


def show_harmony(pitch_text, key):
    """
    Return the generated harmony notes as text.
    """

    pitches = pitch_text.split()

    if len(pitches) == 0:
        raise MusicInputError(
            "Enter some notes first, such as C4 D4 E4."
        )

    check_note_names(pitches)

    harmony = make_harmony(
        pitches,
        key=key
    )

    return " ".join(harmony)


def analyse_single_note(audio):
    """
    Detect the main pitch in a recording.
    """

    pitch = detect_single_note(audio)

    if pitch is None:
        return "No clear pitch detected."

    return (
        f"Detected note: {pitch.note} "
        f"({describe_tuning(pitch)})"
    )


def analyse_sequence(
    audio,
    duration_text,
    bpm
):
    """
    Detect a sequence using the expected note durations.
    """

    duration_strings = duration_text.split()

    durations = []

    for duration in duration_strings:
        durations.append(read_beats(duration))

    pitches = detect_sequence(
        audio,
        durations,
        float(bpm)
    )

    display_notes = []

    for pitch in pitches:
        display_notes.append(
            describe_pitch(pitch)
        )

    return " ".join(display_notes)


def analyse_instrument(audio):
    """
    Format the instrument detector's top predictions.
    """

    results = detect_instrument(audio)

    if len(results) == 0:
        return "No audio provided."

    lines = []

    for result in results:

        label = result["label"]

        confidence = round(
            result["score"] * 100,
            1
        )

        lines.append(
            f"{label}: {confidence}%"
        )

    return "\n".join(lines)


def describe_comparison(comparison):
    """
    Describe one compared note in words.

    The wording follows what a listener would notice: small
    errors are not worth mentioning, and a note that lands
    nearer a different note is named as that note instead.
    """

    if not comparison.was_detected:
        return f"{comparison.target}: nothing detected"

    label = comparison.target

    if comparison.expected != comparison.target:
        label = f"{comparison.target} (as {comparison.expected})"

    cents = comparison.cents_from_target
    direction = "sharp" if cents > 0 else "flat"

    if abs(cents) <= 10:
        return f"{label}: in tune"

    if not comparison.is_target_note:
        return (
            f"{label}: heard {comparison.heard}, "
            f"{abs(round(cents))} cents {direction}"
        )

    if abs(cents) <= 25:
        return (
            f"{label}: slightly {direction} "
            f"({round(cents):+d})"
        )

    return (
        f"{label}: clearly {direction} "
        f"({round(cents):+d})"
    )


def describe_summary(summary):
    """
    One line describing how the performance went overall.
    """

    if summary["detected"] == 0:
        return "No notes were detected in that recording."

    average = round(summary["average_cents_off"])

    return (
        f"{summary['on_target']} of {summary['total']} notes "
        f"on the right pitch. "
        f"Average {average} cents from target."
    )


# The shift options offered in the interface, and the number
# of semitones each one means. A shift is stored in semitones
# so that other intervals can be added later without changing
# anything that uses it.
OCTAVE_CHOICES = {
    "Same octave": 0,
    "One octave down": -12,
    "One octave up": 12
}


def read_octave_choice(choice):
    """
    Turn the chosen option into a number of semitones.
    """

    if choice is None:
        return 0

    if choice not in OCTAVE_CHOICES:
        raise MusicInputError(
            f"'{choice}' is not one of the octave options."
        )

    return OCTAVE_CHOICES[choice]


def describe_shift(semitones):
    """
    Say what a shift means in words a musician would use.
    """

    if semitones % 12 == 0:

        octaves = abs(semitones) // 12
        direction = "below" if semitones < 0 else "above"

        if octaves == 1:
            return f"an octave {direction}"

        return f"{octaves} octaves {direction}"

    direction = "below" if semitones < 0 else "above"

    return f"{abs(semitones)} semitones {direction}"


def check_transpose(transpose):
    """
    Make sure the shift is a sensible number of semitones.
    """

    try:
        transpose = int(transpose)

    except (TypeError, ValueError):
        raise MusicInputError(
            "The shift must be a whole number of semitones."
        )

    if abs(transpose) > 36:
        raise MusicInputError(
            "The shift must be within three octaves."
        )

    return transpose


# Which line of the music a performance is judged against.
PART_CHOICES = [
    "Melody", "Harmony above", "Harmony below", "Bass"
]


def part_steps(part):
    """
    The scale steps a harmony part sits from the tune.

    Two steps of the scale is a third. Below is the
    default, which is where a harmony most often sits, and
    what the plain name "Harmony" meant before there were
    two.
    """

    return {
        "Harmony above": 2,
        "Harmony below": -2
    }.get(part, -2)


# How the harmony line chooses its notes.
#
# Corrected thirds lead, because with no chart they are
# parallel thirds anyway, and with one they are what a
# harmony singer actually does: shadow the tune, and bend
# where the third would clash with the chord.
#
# Parallel thirds stay because they trust only the key. A
# mistyped chart makes correction repair notes that were
# never wrong, and this is the strategy that cannot be
# misled that way.
#
# Chord tones are a different sound rather than a better
# one: the line follows the harmony instead of shadowing
# the tune, which is an arranged inner voice rather than a
# duet partner.
HARMONY_STYLES = [
    "Thirds, chord-corrected",
    "Parallel thirds",
    "Chord tones"
]


# The intervals a harmony line can be built at, as scale
# positions relative to the melody. More will join these:
# sixths, octaves, and anything else a step count reaches.
HARMONY_CHOICES = {
    "Third below": -2,
    "Third above": 2
}


def read_harmony_choice(choice):
    """
    Turn the chosen harmony interval into scale steps.
    """

    if choice is None:
        return -2

    if choice not in HARMONY_CHOICES:
        raise MusicInputError(
            f"'{choice}' is not one of the harmony options."
        )

    return HARMONY_CHOICES[choice]


def analyse_performance(
    audio,
    pitch_text,
    duration_text,
    bpm,
    transpose=0,
    lyric_text="",
    part="Melody",
    key="C",
    chart_text="",
    harmony_style="Thirds, chord-corrected",
    phrase_label=None,
    second_opinion_on=False,
    mixer_value=None
):
    """
    Compare a recording against the target music.

    part decides which line is being performed: the melody
    as written, or the harmony built from it. Someone
    singing the harmony part is judged against the harmony
    notes, not marked wrong against the melody.

    mixer_value is the live mixer's own value, if it has one:
    a loop selected there - by clicking bars or a phrase in
    the mixer - takes over from the phrase dropdown, since
    it is a more exact statement of what was just sung
    against. No loop selected there, or no mixer built yet,
    and phrase_label decides it exactly as before.

    Returns a written summary and two charts.
    """

    if audio is None:
        raise MusicInputError(
            "Record or upload a performance first."
        )

    from mixer_data import loop_notes

    looped = loop_notes(
        pitch_text, duration_text, lyric_text, key,
        chart_text, mixer_value
    )

    judged_on_loop = looped is not None

    piece = looped if judged_on_loop else selected_piece(
        pitch_text, duration_text, lyric_text, key,
        chart_text, phrase_label
    )

    pitches = piece.pitches
    durations = piece.durations
    chart_text = piece.chart
    lyric_text = piece.lyrics or ""

    if part.startswith("Harmony") or part == "Bass":
        pitches = part_notes(
            pitches,
            part,
            key,
            part_steps(part),
            durations,
            harmony_style,
            chart_text
        )

    elif part != "Melody":
        raise MusicInputError(
            f"'{part}' is not a part that can be performed."
        )

    bpm = check_bpm(bpm)

    if isinstance(transpose, str):
        transpose = read_octave_choice(transpose)

    transpose = check_transpose(transpose)

    detected = detect_sequence(
        audio,
        durations,
        bpm
    )

    comparisons = compare_sequence(
        pitches,
        detected,
        transpose
    )

    lines = [
        describe_summary(summarise(comparisons))
    ]

    if judged_on_loop:
        lines.append(
            "Judged against the stretch selected in the mixer."
        )

    if part != "Melody":
        lines.append(
            f"Judged against the {part.lower()} part."
        )

    if transpose != 0:
        lines.append(
            f"Scored {describe_shift(transpose)} "
            f"the written music."
        )

    lines.append("")

    for comparison in comparisons:

        if comparison.is_rest:
            continue

        lines.append(
            describe_comparison(comparison)
        )

    lyrics = read_lyrics(
        lyric_text,
        sung_count(pitches)
    )

    trace = trace_performance(audio)

    # A second detector, when asked for. It changes nothing
    # about the judging: it says where another method heard
    # something different, which is worth knowing on a
    # microphone that loses the bottom of a low voice, and
    # worth collecting before either detector is trusted
    # over the other.
    if second_opinion_on:

        # Aliased: this module has its own
        # describe_comparison for note comparisons, and an
        # unaliased import would shadow it for the whole
        # function, including the loop above.
        from pitch_witness import (
            second_opinion,
            describe_comparison as describe_second_opinion
        )

        sample_rate, sound = audio

        sound = prepare_audio(sound)
        sound = trim_leading_silence(sound)

        times, midi = trace if trace else (None, None)

        lines.append("")
        lines.append(
            describe_second_opinion(
                second_opinion(sound, sample_rate, midi)
                if midi is not None else None
            )
        )

    chords, bars = read_chords(chart_text, durations)

    performance_plot = make_performance_plot(
        pitches,
        durations,
        bpm,
        trace,
        transpose,
        lyrics,
        chords=chords,
        bars=bars,
        key=key
    )

    return (
        "\n".join(lines),
        performance_plot,
        make_tuning_plot(comparisons)
    )


GUIDE_CHOICES = [
    "Clicks",
    "Your part",
    "The other part",
    "No guide"
]


def harmony_line(
    pitches,
    durations,
    key,
    steps=-2,
    style="Thirds, chord-corrected",
    chart_text=""
):
    """
    Build the harmony in the chosen style.

    Styles that read the chords take the chart; with no
    chart, every style comes out as parallel thirds, so
    the choice is always safe to make.

    `key` is the key box's own raw text - a single name, or
    a whole timeline for a piece that genuinely modulates -
    read here the same way Piece.read and transpose_music
    read it, so each note harmonises against whichever key
    was actually in force at its own beat rather than one
    key for the whole piece.
    """

    try:
        key_changes = read_key(key)

    except KeyError_ as problem:
        raise MusicInputError(str(problem))

    if style == "Parallel thirds" or not chart_text.strip():
        return make_harmony(pitches, durations, key_changes, steps)

    chords, bars = read_chords(chart_text, durations)

    voiced = [
        (start, length, chord_semitones(name))
        for start, length, name in chords
    ]

    return make_chord_harmony(
        pitches,
        durations,
        voiced,
        key=key_changes,
        steps=steps,
        style=style
    )


def part_notes(pitches, part, key, harmony_steps=-2,
               durations=None, style="Thirds, chord-corrected",
               chart_text=""):
    """
    The notes belonging to a part of the music.
    """

    if durations is None:
        durations = [1.0] * len(pitches)

    if part.startswith("Harmony"):

        if part != "Harmony":
            harmony_steps = part_steps(part)

        return harmony_line(
            pitches,
            durations,
            key,
            steps=harmony_steps,
            style=style,
            chart_text=chart_text
        )

    if part == "Bass":

        return bass_line(pitches, durations, chart_text)

    return pitches


def bass_line(pitches, durations, chart_text):
    """
    The bass part, which needs the chords to exist at all.

    A bass sings the root of the harmony, so without a
    chart there is nothing for it to sing.
    """

    if not chart_text or not chart_text.strip():
        raise MusicInputError(
            "A bass part sings the root of each chord, so "
            "it needs a chord chart. Write one in the "
            "Chords box, such as | C . . . | F . C . |"
        )

    chords, bars = read_chords(chart_text, durations)

    voiced = [
        (start, length, chord_semitones(name))
        for start, length, name in chords
    ]

    return make_bass(pitches, durations, voiced)


def make_practice_guide(
    pitch_text,
    duration_text,
    bpm,
    guide_choice,
    part="Melody",
    key="C",
    chart_text="",
    harmony_style="Thirds, chord-corrected",
    mixer_value=None
):
    """
    The audio that plays while a performance is recorded.

    Starts with the count-in, so however long the app takes
    to begin playing after recording starts, the player
    still gets a clear run of clicks before beat one. That
    delay lands harmlessly inside the count-in.

    The guide knows which part is being performed. Your
    part plays the line being sung, for learning it. The
    other part plays the opposite line, the way harmony is
    usually practised: singing against the melody.

    mixer_value is the live mixer's own value: a loop
    selected there shortens the guide to just that stretch,
    the same rule analyse_performance follows for judging -
    otherwise the whole piece plays, as before.
    """

    if guide_choice == "No guide":
        return None

    pitches, durations = read_music(
        pitch_text,
        duration_text
    )

    from mixer_data import loop_notes

    looped = loop_notes(
        pitch_text, duration_text, "", key, chart_text, mixer_value
    )

    if looped is not None:
        pitches = looped.pitches
        durations = looped.durations
        chart_text = looped.chart

    bpm = check_bpm(bpm)

    if guide_choice == "Clicks":

        sample_rate = 8000

        total_seconds = sum(durations) * 60 / bpm

        sound = [0.0] * int(total_seconds * sample_rate)

    elif guide_choice == "Your part":

        sample_rate, sound = make_melody(
            part_notes(
                pitches, part, key,
                part_steps(part),
                durations, harmony_style, chart_text
            ),
            durations,
            bpm
        )

    elif guide_choice == "The other part":

        # With more than two parts there is no single
        # other one, so this means the tune: what a
        # harmony or bass singer needs in their ears. A
        # melody singer hears the harmony below instead,
        # which is the same exercise the other way round.
        other = (
            "Harmony below" if part == "Melody" else "Melody"
        )

        sample_rate, sound = make_melody(
            part_notes(
                pitches, other, key,
                part_steps(other),
                durations, harmony_style, chart_text
            ),
            durations,
            bpm
        )

    else:
        raise MusicInputError(
            f"'{guide_choice}' is not a guide option."
        )

    chords, bars = read_chords(chart_text, durations)

    sound = add_metronome(
        sound,
        sum(durations),
        bpm,
        sample_rate,
        bars=bars
    )

    sound = make_count_in(bpm, sample_rate) + list(sound)

    return sample_rate, np.array(sound, dtype=np.float32)


def show_target_music(
    pitch_text,
    duration_text,
    bpm,
    lyric_text="",
    key="C",
    harmony_above_level=0.0,
    harmony_below_level=0.0,
    chart_text="",
    harmony_style="Thirds, chord-corrected",
    bass_level=0.0,
    chart_notes=None,
    phrase_label=None
):
    """
    Draw the target music as a score-like picture.

    The same picture the comparison draws, without a
    performance on it: something to study before singing.
    When the harmony is switched on it appears as a second
    voice, the way a duet is printed.
    """

    piece = selected_piece(
        pitch_text, duration_text, lyric_text, key,
        chart_text, phrase_label
    )

    pitches = piece.pitches
    durations = piece.durations
    chart_text = piece.chart

    bpm = check_bpm(bpm)

    lyrics = read_lyrics(piece.lyrics or "", piece.sung())

    # Audible parts appear on the picture; the level only
    # decides whether, not how they are drawn. Each line is
    # named rather than numbered, because the picture
    # colours them apart and has to know which is which.
    voices = {}

    for name, steps, level in (
        ("harmony_above", 2, harmony_above_level),
        ("harmony_below", -2, harmony_below_level)
    ):

        if level <= 0:
            continue

        voices[name] = harmony_line(
            pitches,
            durations,
            key,
            steps=steps,
            style=harmony_style,
            chart_text=chart_text
        )

    bass = None

    if bass_level > 0:
        bass = bass_line(pitches, durations, chart_text)

    chords, bars = read_chords(chart_text, durations)

    # What the chart cannot say, printed under each
    # symbol: the note a chord is played over, and a name
    # that fits the same notes equally well.
    chord_asides = None

    if chords and chart_notes:

        from chord_detector import asides_for

        chord_asides = asides_for(chart_notes, chords)

    return make_performance_plot(
        pitches,
        durations,
        bpm,
        trace=None,
        lyrics=lyrics,
        title="The target music",
        harmony_above=voices.get("harmony_above"),
        harmony_below=voices.get("harmony_below"),
        chords=chords,
        bars=bars,
        bass=bass,
        key=key,
        chord_asides=chord_asides
    )



# One key per semitone, which is what makes transposing
# unambiguous: raising F by one lands on F#, not Gb,
# because F# is the key this app names for that sound.
KEY_BY_SEMITONE = {
    NOTE_SEMITONES[key] % 12: key
    for key in MAJOR_SCALES
}


def semitones_between(from_key, to_key):
    """
    The shortest way from one key to another.

    Shortest, because F to G is up two rather than down
    ten: a singer asking for G wants the nearest G, and
    the octave buttons are there for anyone who wants the
    far one.
    """

    for name in (from_key, to_key):
        if name not in MAJOR_SCALES:
            raise MusicInputError(
                f"'{name}' is not a key this app knows."
            )

    distance = (
        NOTE_SEMITONES[to_key] - NOTE_SEMITONES[from_key]
    ) % 12

    return distance - 12 if distance > 6 else distance


def transpose_music(pitch_text, duration_text, key, chart_text,
                    chart_notes, semitones):
    """
    Move the music, and everything that describes it.

    The notes, the key and the chart travel together, and
    so does the hidden polyphony the picture and Suggest
    chords read: it lives in pitch, so left behind it
    would describe the key the music used to be in.

    `key` is the key box's own raw text - a single name, or
    a whole timeline ("G, Ab from beat 156") for a piece
    that genuinely modulates. Every key in the timeline
    moves by the same interval and respells in its own new
    dialect; each note respells against whichever key was
    actually in force at its own beat, not one key for the
    whole piece - which needs `duration_text` alongside the
    pitches, the same pairing Piece.read already needs, to
    know where in the piece each note actually sits.

    This is one edit of the boxes and nothing else. No
    memory of where the music started is kept: after the
    edit, this is the music. Transposing back is exact,
    which is a better way to return than a remembered
    original that goes stale the moment anything is typed.

    Durations, lyrics, phrasing and tempo are untouched -
    transposing changes how high the music sits, not how
    it goes.
    """

    semitones = check_transpose(semitones)

    try:
        key_changes = read_key(key)

    except KeyError_ as problem:
        raise MusicInputError(str(problem))

    for _, name in key_changes:

        if name not in MAJOR_SCALES:
            raise MusicInputError(
                f"'{name}' is not a key this app knows."
            )

    pitches, durations = read_music(pitch_text, duration_text)

    # Every key in the timeline moves by the same interval
    # and respells in its own new dialect - the beats never
    # move, since transposing changes pitch, not time.
    new_key_changes = [
        (
            beat,
            KEY_BY_SEMITONE[
                (NOTE_SEMITONES[name] + semitones) % 12
            ]
        )
        for beat, name in key_changes
    ]

    new_key = new_key_changes[0][1]

    # The numbers first, then the check, then the names.
    # A note pushed past the ends of the keyboard cannot be
    # named at all, so naming before checking fails with a
    # complaint about a note nobody asked for rather than
    # about the shift that made it.
    numbers = [
        None if is_rest(pitch) else note_to_midi(pitch) + semitones
        for pitch in pitches
    ]

    for number in numbers:

        if number is None:
            continue

        if number < 12 or number > 120:
            raise MusicInputError(
                "That would move the music off the "
                "keyboard. Try a smaller shift."
            )

    position = 0.0

    moved = []

    for number, length in zip(numbers, durations):

        if number is None:
            moved.append(REST)

        else:
            moved.append(
                midi_to_note(
                    number, key_at(new_key_changes, position)
                )
            )

        position += float(length)

    new_chart = transpose_chart(chart_text, semitones, new_key_changes)

    new_notes = chart_notes

    if chart_notes:
        new_notes = [
            (start, length, number + semitones)
            for start, length, number in chart_notes
        ]

    return (
        " ".join(moved),
        format_key(new_key_changes),
        new_chart,
        new_notes
    )


def describe_transpose(old_key, new_key, semitones, pitch_text):
    """
    What the transpose did, in the words that matter.

    The range is said out loud because that is the fact a
    singer is deciding on: not which key it is now, but
    whether the top note is still reachable.
    """

    pitches = [
        pitch for pitch in pitch_text.split()
        if not is_rest(pitch)
    ]

    direction = "up" if semitones > 0 else "down"

    step = abs(semitones)

    line = (
        f"{old_key} to {new_key}, {direction} "
        f"{step} semitone{'s' if step != 1 else ''}"
    )

    if pitches:

        numbers = [note_to_midi(pitch) for pitch in pitches]

        line += (
            f". The part now runs "
            f"{midi_to_note(min(numbers), new_key)} to "
            f"{midi_to_note(max(numbers), new_key)}"
        )

    return line + "."


def key_setting_for(key_name):
    """
    The key setting that suits a detected key.

    A major key is itself. A minor key is sung with the
    notes of its relative major, which is the setting the
    harmony is built from.
    """

    tonic, _, kind = key_name.partition(" ")

    if kind == "major":
        return tonic if tonic in MAJOR_SCALES else None

    for major, minor in RELATIVE_MINORS.items():
        if minor == tonic:
            return major

    return None


def suggest_chords(chart_notes, pitch_text, duration_text,
                   key="C"):
    """
    Read the chords again from the music that was imported.

    Only imported music has chords to find: a melody typed
    into the boxes is one line, and one line does not say
    what the harmony is. So this works on the notes the
    import kept, and says so plainly when there are none.
    """

    from chord_detector import chart_from_notes, explain_empty_chart

    pitches, durations = read_music(pitch_text, duration_text)

    total = sum(durations)

    if chart_notes:

        from midi_import import spelling_key

        chart = chart_from_notes(
            chart_notes,
            total,
            4,
            key=spelling_key(chart_notes)
        )

        if chart:
            return chart

    # No harmony to read, so fall back to what the melody
    # implies. A weaker answer, and worth having: a tune on
    # its own does not state its harmony, but it does
    # narrow it, and a suggested chart is somewhere to
    # start editing from.
    return suggest_chords_for_melody(pitches, durations, key)


def suggest_chords_for_melody(
    pitches,
    durations,
    key="C"
):
    """
    Chords that would fit a melody, as a starting point.
    """

    from chord_detector import suggest_chart_from_melody

    if sum(durations) < 4:
        raise MusicInputError(
            "There is not enough music here to suggest "
            "chords for. A bar is the least that can be "
            "harmonised."
        )

    chart = suggest_chart_from_melody(
        pitches,
        durations,
        key,
        minor=sounds_minor(pitches, durations)
    )

    if not chart:
        raise MusicInputError(
            "No chords could be suggested for this music."
        )

    return chart


def sounds_minor(pitches, durations):
    """
    Whether a melody sounds minor rather than major.

    A minor key uses the same seven chords as its relative
    major and hears a different one as home, so which it is
    decides where every cadence falls.
    """

    from key_detector import detect_key

    sung = [pitch for pitch in pitches if not is_rest(pitch)]

    lengths = [
        durations[position]
        for position in range(len(pitches))
        if not is_rest(pitches[position])
    ]

    if not sung:
        return False

    best, score = detect_key(sung, lengths)[0]

    return best.endswith("minor")


def suggest_key(pitch_text, duration_text, key=None):
    """
    Name the keys this music might be in.

    The strongest match comes first, with the others in
    order. Nothing is chosen automatically: a short melody
    often genuinely suits several keys, and which one to
    sing in is the player's decision.

    `key` is the key box's own current text, optional and
    read-only here - this never overwrites the box, it only
    checks what is already in it. Detection reads one whole-
    piece profile and returns one best guess; a key box that
    already states a real change (read from the score itself,
    not guessed) is more informative than that guess can ever
    be, so the report says so up front rather than silently
    proposing a single key as if nothing more were known.
    Invariant 5: detection reads, suggestion proposes, and a
    proposal should not quietly replace a read.
    """

    pitches, durations = read_music(
        pitch_text,
        duration_text
    )

    lines = []

    if key is not None:

        try:
            key_changes = read_key(key)

        except KeyError_:
            key_changes = [(0.0, "C")]

        if len(key_changes) > 1:

            described = ", ".join(
                f"{name} from beat {beat:g}"
                if position > 0 else name
                for position, (beat, name) in enumerate(key_changes)
            )

            lines.append(
                f"The key box already states a change this "
                f"score prints ({described}) - a single "
                f"guess below cannot know about that, and "
                f"is worth less than what is already there. "
                f"Shown for interest; keeping the box as it "
                f"is is very likely the better choice."
            )

            lines.append("")

    scored = plausible_keys(pitches, durations)

    lines.append(describe_key(pitches, durations))

    lines.append("")

    if len(scored) == 1:
        lines.append("Nothing else comes close.")

    else:
        lines.append("Also possible:")

        for name, score in scored:
            lines.append(f"  {name}  ({score:.2f})")

    # Which key setting each candidate corresponds to. A
    # minor key is sung with the notes of its relative
    # major, so that is what the dropdown wants.
    best_name = scored[0][0]

    setting = key_setting_for(best_name)

    if setting:
        lines.append("")
        lines.append(
            f"For harmony, set the key to "
            f"{setting} major / {RELATIVE_MINORS[setting]} "
            f"minor."
        )

    # A short melody often touches only a handful of
    # pitches, and those pitches sit inside several keys.
    # Naming only the likeliest would hide settings that
    # work just as well.
    workable = keys_containing(pitches)

    others = [
        major for major in workable
        if major != setting
    ]

    if others:
        named = ", ".join(
            f"{major} major / {RELATIVE_MINORS[major]} minor"
            for major in others
        )

        lines.append(
            f"These notes also fit {named}."
        )

    return "\n".join(lines)


def list_midi_tracks(file_path):
    """
    Describe the tracks in an uploaded MIDI file.

    Returns the labels, ready for a dropdown, and the
    number of the track chosen by default.
    """

    from midi_import import describe_parts, MidiImportError

    if file_path is None:
        raise MusicInputError(
            "Choose a MIDI file first."
        )

    try:
        described = describe_parts(file_path)

    except MidiImportError as problem:
        raise MusicInputError(str(problem))

    # The identifier is carried in the label so that the
    # dropdown needs no state of its own, and so that a
    # player can see which part of the file they are
    # looking at.
    return [
        f"{identifier}  {text}"
        for identifier, text in described
    ]


# The dropdown entry meaning no phrase in particular: the
# part as it stands in the boxes.
WHOLE_PART = "Whole part"


# The same, for choosing which part of a file to import.
WHOLE_TRACK = "Whole track"


def list_phrases(pitch_text, duration_text, lyric_text):
    """
    The phrases the music in the boxes divides into.

    Read from the boxes rather than from the file, because
    the boxes are what the player has been correcting. A
    line break added to the lyrics adds a phrase here the
    moment it is typed.
    """

    from piece import Piece

    try:
        piece = Piece.read(pitch_text, duration_text, lyric_text)

    except MusicInputError:
        return [WHOLE_PART]

    found = piece.phrases()

    if len(found) <= 1:
        return [WHOLE_PART]

    labels = [WHOLE_PART]

    lines = [
        line for line in (lyric_text or "").split("\n")
        if line.strip()
    ]

    for position in range(len(found)):

        first, last = found[position]

        if position < len(lines):

            from midi_import import join_syllables

            opening = join_syllables(lines[position].split())

        else:
            opening = " ".join(piece.pitches[first:first + 5])

        labels.append(
            f"Phrase {position + 1}: {opening}"
        )

    return labels


def phrase_chosen(label):
    """
    Which phrase a dropdown label refers to, or None for
    the whole part.
    """

    if label is None or label == WHOLE_PART:
        return None

    try:
        return int(str(label).split()[1].rstrip(":")) - 1

    except (IndexError, ValueError):
        return None


def selected_piece(
    pitch_text,
    duration_text,
    lyric_text="",
    key="C",
    chart_text="",
    phrase_label=None
):
    """
    The music being worked on: the whole part, or one
    phrase of it.

    Everything the app does to a stretch of music goes
    through here, so that the notes, the words under them
    and the chords over them are always cut to the same
    place.
    """

    from piece import Piece

    piece = Piece.read(
        pitch_text, duration_text, lyric_text, key, chart_text
    )

    number = phrase_chosen(phrase_label)

    if number is None:
        return piece

    return piece.phrase(number)




def list_midi_phrases(file_path, track_label=None):
    """
    Describe the phrases in a track, for a dropdown.

    The whole track comes first, so a short piece can be
    practised in one go.
    """

    from midi_import import describe_phrases, MidiImportError

    if file_path is None:
        raise MusicInputError(
            "Choose a MIDI file first."
        )

    try:
        track, channel = track_number_from(track_label)

        described = describe_phrases(
            file_path,
            track,
            channel
        )

    except MidiImportError as problem:
        raise MusicInputError(str(problem))

    return [WHOLE_TRACK] + [label for _, label in described]



def phrase_number_from(label):
    """
    Read the phrase number back out of a dropdown label.

    Phrases are numbered from one in the interface and
    from zero in the code.
    """

    if label is None or label == WHOLE_TRACK:
        return None

    try:
        return int(label.split()[1]) - 1

    except (IndexError, ValueError):
        return None


def track_number_from(label):
    """
    Read the track and channel back out of a label.

    Returns (track, channel). Labels from before parts were
    separated by channel say only a track number, which
    still reads correctly with no channel.
    """

    if label is None:
        return None, None

    from midi_import import read_part_choice

    first = str(label).split()[0] if str(label).split() else ""

    track, channel = read_part_choice(first)

    if track is not None:
        return track, channel

    # An older label, or one written by hand.
    try:
        return int(str(label).split()[1]), None

    except (IndexError, ValueError):
        return None, None


def is_score_file(file_path):
    """
    Whether a path is a score rather than a performance.
    """

    if not file_path:
        return False

    return str(file_path).lower().endswith(
        (".mxl", ".musicxml", ".xml")
    )


def list_score_parts(file_path):
    """
    The parts of a score, named as the score names them.
    """

    from musicxml_import import parts_in

    return parts_in(file_path)


def score_verses(file_path, part_label=None):
    """
    Which verses a score's part carries.
    """

    from musicxml_import import verses_in

    return verses_in(file_path, part_label)


def import_score_file(file_path, part_label=None, verse=1):
    """
    Fill the music boxes from a score.

    The same eight things the MIDI import returns, so
    everything above this is unaffected by which kind of
    file arrived. What differs is how much had to be
    worked out: a score states its lengths, its metre and
    its words, so none of the timing repair applies.
    """

    from musicxml_import import import_musicxml

    if file_path is None:
        raise MusicInputError(
            "Choose a score file first."
        )

    try:
        return import_musicxml(file_path, part_label, verse)

    except MusicInputError:
        raise

    except Exception as problem:
        raise MusicInputError(
            f"That score could not be read: {problem}"
        )


def import_music_file(file_path, part_label=None, verse=1):
    """
    Fill the boxes from whichever kind of file arrived.

    The extension decides. Both paths end in the same
    eight values, so nothing above here needs to know
    which one ran.
    """

    if is_score_file(file_path):
        return import_score_file(file_path, part_label, verse)

    return import_midi_file(file_path, part_label)


def list_music_parts(file_path):
    """
    The parts of whichever kind of file arrived.
    """

    if is_score_file(file_path):
        return list_score_parts(file_path)

    return list_midi_tracks(file_path)


def import_midi_file(
    file_path,
    track_label=None
):
    """
    Fill the music boxes from an uploaded MIDI file.

    Returns pitch, duration and lyric text, the file's
    tempo, and a line of feedback.

    Neither the key nor the melody track is guessed at.
    A choral file holds one track per voice, and the
    highest is as often a piano part as the tune, so the
    tracks are listed and the player chooses. The feedback
    names the keys the notes would allow harmony in.
    """

    from midi_import import import_midi, MidiImportError

    if file_path is None:
        raise MusicInputError(
            "Choose a MIDI file first."
        )

    try:
        (
            pitch_text,
            duration_text,
            lyric_text,
            bpm,
            chart_text,
            chart_notes
        ) = (
            import_midi(
                file_path,
                track_number=track_number_from(track_label)[0],
                channel=track_number_from(track_label)[1]
            )
        )

    except MidiImportError as problem:
        raise MusicInputError(str(problem))

    note_count = len(pitch_text.split())

    if track_label is None:
        source = "every track together"

    else:
        track, channel = track_number_from(track_label)

        source = f"track {track}"

        if channel is not None:
            source = str(track_label).split("  ", 1)[-1]
            source = source.split(",")[0]

    lines = [
        f"Imported {note_count} notes from {source} "
        f"at {bpm} BPM."
    ]

    # The key is heard in the whole texture, not in one
    # line of it. The other voices and the accompaniment
    # are exactly what tells a listener whether a piece is
    # in a major key or its relative minor, so detection
    # reads the file entire, whichever track was chosen
    # to sing.
    from midi_import import read_all_notes

    all_pitches, all_durations = read_all_notes(file_path)

    lines.append(
        describe_key(all_pitches, all_durations)
    )

    # Which keys hold every note, if any do. Harmony works
    # in any key now, so this is a recommendation and not
    # a restriction: a key that contains the lot gives the
    # tidiest harmony line.
    workable = keys_containing(pitch_text.split())

    if len(workable) == 1:
        lines.append(
            f"Every note fits {workable[0]} major."
        )

    elif len(workable) > 1:
        options = " or ".join(workable)
        lines.append(
            f"Every note fits {options} major."
        )

    else:
        lines.append(
            "No single key holds every note, which is "
            "ordinary in real music. Harmony still works: "
            "notes outside the chosen key are sung at the "
            "nearest note in the scale."
        )

    if lyric_text:

        held = lyric_text.split().count("_")

        if held:
            lines.append(
                f"Lyrics were found, with {held} notes "
                f"holding the syllable before them."
            )

        else:
            lines.append("Lyrics were found and loaded.")

    else:
        lines.append(
            "This track has no lyrics, so the lyric box "
            "is left empty."
        )

    # The key setting the detected key calls for, so that
    # harmony, the chord spelling and the pitch axis all
    # start from the right place. Everything else the
    # import fills is set from the file; leaving this one
    # behind means the music arrives in the wrong key
    # until someone notices.
    detected = detect_key(all_pitches, all_durations)[0][0]

    key_setting = key_setting_for(detected)

    if chart_text:

        lines.append(
            "The chords were read from every voice "
            "sounding together, and can be edited."
        )

        # What the chart itself has no way to say: which
        # chords are played over another note, where a
        # second name fits equally well, and where an
        # independent reader would disagree.
        from chord_detector import (
            describe_detection,
            second_opinion,
            midi_reader_opinion
        )
        from chords import read_chart

        chords, bars = read_chart(chart_text)

        aside = describe_detection(chart_notes, chords)

        if aside:
            lines.append(aside)

        for opinion in (
            second_opinion(chart_notes, chords),
            midi_reader_opinion(chart_notes, chords)
        ):
            if opinion:
                lines.append(opinion)

    return (
        pitch_text,
        duration_text,
        lyric_text,
        bpm,
        " ".join(lines),
        chart_text,
        chart_notes,
        key_setting
    )