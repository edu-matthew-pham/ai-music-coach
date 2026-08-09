# music.py

import numpy as np

from chords import chord_semitones
from piece import Piece
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
    MAJOR_SCALES,
    RELATIVE_MINORS
)

from notes import split_note, is_rest, REST

from compare import compare_sequence, summarise

from tuning_plot import (
    make_tuning_plot,
    make_performance_plot
)

from pitch_detector import (
    detect_single_note,
    detect_sequence,
    trace_performance
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


def describe_key_fit(pitches, key):
    """
    How well the chosen key suits the music.

    The key is the player's to choose, so this reports
    rather than refuses. Notes outside the key are still
    harmonised, at the nearest note in the scale, and are
    named here so the resulting interval is no surprise.

    Returns a sentence, or None when everything fits.
    """

    outside = notes_outside(pitches, key)

    if len(outside) == 0:
        return None

    named = ", ".join(outside)

    return (
        f"{len(outside)} notes fall outside {key} major "
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


def play_music(
    pitch_text,
    duration_text,
    key,
    melody_on=True,
    harmony_on=False,
    bpm=120,
    metronome=True,
    harmony_choice="Third below",
    chart_text="",
    chords_on=False,
    harmony_style="Thirds, chord-corrected",
    bass_on=False,
    lyric_text="",
    phrase_label=None
):
    """
    Build the playback from independent layers.

    Melody, harmony and metronome are separate tracks,
    each switched on or off, mixed together at the end.
    Everything off still clicks, so the result is never
    silence that looks like a failure.
    """

    piece = selected_piece(
        pitch_text, duration_text, lyric_text, key,
        chart_text, phrase_label
    )

    pitches = piece.pitches
    durations = piece.durations
    chart_text = piece.chart

    bpm = check_bpm(bpm)

    # Read now so a mistake in the chart is reported when
    # the music is generated, rather than later when
    # something tries to use it. The bars also tell the
    # metronome where the downbeats are.
    chords, bars = read_chords(chart_text, durations)

    sample_rate = 8000

    total_seconds = sum(durations) * 60 / bpm
    total_samples = int(total_seconds * sample_rate)

    layers = []

    if melody_on:

        sample_rate, melody_track = make_melody(
            pitches,
            durations,
            bpm
        )

        layers.append(melody_track)

    if harmony_on:

        harmony = harmony_line(
            pitches,
            durations,
            key,
            steps=read_harmony_choice(harmony_choice),
            style=harmony_style,
            chart_text=chart_text
        )

        sample_rate, harmony_track = make_melody(
            harmony,
            durations,
            bpm
        )

        layers.append(harmony_track)

    if bass_on:

        sample_rate, bass_track = make_melody(
            bass_line(pitches, durations, chart_text),
            durations,
            bpm
        )

        layers.append(bass_track)

    if chords_on and chords:

        voiced = [
            (start, length, chord_semitones(name))
            for start, length, name in chords
        ]

        layers.append(
            make_accompaniment(
                voiced,
                bars,
                sum(durations),
                bpm,
                sample_rate
            )
        )

    if len(layers) == 0:
        sound = [0.0] * total_samples

    elif len(layers) == 1:
        sound = layers[0]

    else:
        sound = layers[0]

        for extra in layers[1:]:
            sound = mix_tracks(sound, extra)

    # The metronome always clicks when there are no notes,
    # so switching everything off gives a click track for
    # practising to rather than silence.
    if metronome or len(layers) == 0:
        sound = add_metronome(
            sound,
            sum(durations),
            bpm,
            sample_rate,
            bars=bars
        )

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
PART_CHOICES = ["Melody", "Harmony", "Bass"]


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
    harmony_choice="Third below",
    chart_text="",
    harmony_style="Thirds, chord-corrected",
    phrase_label=None
):
    """
    Compare a recording against the target music.

    part decides which line is being performed: the melody
    as written, or the harmony built from it. Someone
    singing the harmony part is judged against the harmony
    notes, not marked wrong against the melody.

    Returns a written summary and two charts.
    """

    if audio is None:
        raise MusicInputError(
            "Record or upload a performance first."
        )

    piece = selected_piece(
        pitch_text, duration_text, lyric_text, key,
        chart_text, phrase_label
    )

    pitches = piece.pitches
    durations = piece.durations
    chart_text = piece.chart
    lyric_text = piece.lyrics or ""

    if part in ("Harmony", "Bass"):
        pitches = part_notes(
            pitches,
            part,
            key,
            read_harmony_choice(harmony_choice),
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
    """

    if style == "Parallel thirds" or not chart_text.strip():
        return make_harmony(pitches, key=key, steps=steps)

    chords, bars = read_chords(chart_text, durations)

    voiced = [
        (start, length, chord_semitones(name))
        for start, length, name in chords
    ]

    return make_chord_harmony(
        pitches,
        durations,
        voiced,
        key=key,
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

    if part == "Harmony":

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
    harmony_choice="Third below",
    chart_text="",
    harmony_style="Thirds, chord-corrected"
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
    """

    if guide_choice == "No guide":
        return None

    pitches, durations = read_music(
        pitch_text,
        duration_text
    )

    bpm = check_bpm(bpm)

    if guide_choice == "Clicks":

        sample_rate = 8000

        total_seconds = sum(durations) * 60 / bpm

        sound = [0.0] * int(total_seconds * sample_rate)

    elif guide_choice == "Your part":

        sample_rate, sound = make_melody(
            part_notes(
                pitches, part, key,
                read_harmony_choice(harmony_choice),
                durations, harmony_style, chart_text
            ),
            durations,
            bpm
        )

    elif guide_choice == "The other part":

        # With more than two parts there is no single
        # other one, so this means the tune: what a
        # harmony or bass singer needs in their ears. A
        # melody singer hears the harmony instead, which
        # is the same exercise the other way round.
        other = "Harmony" if part == "Melody" else "Melody"

        sample_rate, sound = make_melody(
            part_notes(
                pitches, other, key,
                read_harmony_choice(harmony_choice),
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
    harmony_on=False,
    harmony_choice="Third below",
    chart_text="",
    harmony_style="Thirds, chord-corrected",
    bass_on=False,
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

    harmony = None

    if harmony_on:
        harmony = harmony_line(
            pitches,
            durations,
            key,
            steps=read_harmony_choice(harmony_choice),
            style=harmony_style,
            chart_text=chart_text
        )

    bass = None

    if bass_on:
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
        harmony=harmony,
        chords=chords,
        bars=bars,
        bass=bass,
        key=key,
        chord_asides=chord_asides
    )


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
                   key="C", harmony_key=None):
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
    return suggest_chords_for_melody(
        pitches, durations, key, harmony_key
    )


def suggest_chords_for_melody(
    pitches,
    durations,
    key="C",
    harmony_key=None
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

    setting = harmony_key or key

    chart = suggest_chart_from_melody(
        pitches,
        durations,
        setting,
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


def suggest_key(pitch_text, duration_text):
    """
    Name the keys this music might be in.

    The strongest match comes first, with the others in
    order. Nothing is chosen automatically: a short melody
    often genuinely suits several keys, and which one to
    sing in is the player's decision.
    """

    pitches, durations = read_music(
        pitch_text,
        duration_text
    )

    scored = plausible_keys(pitches, durations)

    lines = [describe_key(pitches, durations)]

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


def phrase_key(track_label, phrase_label):
    """
    How a phrase is remembered.

    Lyrics typed for a phrase belong to that phrase of that
    part, and not to the same number in another part: the
    third phrase of the bass line is a different stretch of
    music from the third of the tune.
    """

    return f"{track_label}|{phrase_label}"


def remember_lyrics(saved, track_label, phrase_label, lyric_text):
    """
    Keep lyrics typed for a phrase, so its name can show
    them and so they come back when it is chosen again.
    """

    kept = dict(saved or {})

    if not track_label or not phrase_label:
        return kept

    key = phrase_key(track_label, phrase_label)

    if lyric_text and lyric_text.strip():
        kept[key] = lyric_text.strip()

    else:
        kept.pop(key, None)

    return kept


def list_midi_phrases(file_path, track_label=None, saved=None):
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

    return [WHOLE_TRACK] + [
        with_saved_lyrics(label, track_label, saved)
        for _, label in described
    ]


def with_saved_lyrics(label, track_label, saved):
    """
    Put any lyrics typed for a phrase into its name.

    A phrase the player has written words for is named by
    those words, because they are what the player will
    recognise: their own working text rather than the
    notes, and their own corrections rather than whatever
    the file happened to carry.
    """

    if not saved:
        return label

    words = saved.get(phrase_key(track_label, label))

    if not words:
        return label

    from midi_import import join_syllables

    opening = join_syllables(words.split())

    if not opening:
        return label

    head, marker, tail = label.partition("): ")

    if not marker:
        return label

    return f"{head}): {opening}"


# The dropdown entry meaning no phrase in particular.
WHOLE_TRACK = "Whole track"

WHOLE_PART = "Whole part"


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


def load_twinkle_phrase():
    """
    The opening phrase of Twinkle Twinkle Little Star.
    """

    # Two bars of four beats. The last note is shortened
    # to make room for the breath rather than the rest
    # being added on top, which would leave the phrase a
    # beat longer than the music it came from.
    pitches = (
        "C4 C4 G4 G4 A4 A4 G4 R"
    )

    durations = (
        "1 1 1 1 1 1 3/2 1/2"
    )

    lyrics = (
        "Twin- kle twin- kle lit- tle star"
    )

    # Two bars of four. The tune sits on C until the
    # rising sixth, which the F chord underneath is what
    # makes that moment sound like an arrival.
    chart = (
        "| C . . . | F . C . |"
    )

    return pitches, durations, lyrics, "C", chart


def load_wellerman_phrase():
    """
    The opening phrase of the Wellerman, a traditional sea
    shanty in the public domain.

    The tune sits in D minor, which shares its notes with
    F major, so the harmony machinery works in key F.
    """

    # Pitches follow the traditional verse: pickup on the
    # dominant, repeated tonics, the third on "ship", then
    # the dominant above. The line ends with a rest, which
    # is where a singer breathes before the next line.
    pitches = (
        "A3 D4 D4 D4 D4 F4 A4 A4 A4"
    )

    # Eight beats: two bars of four. Checked against a
    # published arrangement, which writes the same rhythm
    # with these note values and runs the line straight on
    # without a rest, the next line arriving on the bar.
    durations = (
        "1 1 1/2 1/2 1 1 1 1 1"
    )

    lyrics = (
        "There once was a ship that put to sea"
    )

    # The whole line sits on the tonic minor, which is
    # part of why a crowd can join in without knowing the
    # song: there is nothing to follow but the tune.
    chart = (
        "| Dm . . . | Dm . . . |"
    )

    return pitches, durations, lyrics, "F", chart