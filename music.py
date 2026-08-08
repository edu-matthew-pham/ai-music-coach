# music.py

import numpy as np

from playback import (
    make_melody,
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


def sung_count(pitches):
    """
    How many of these entries are actually sung.
    """

    return len([
        pitch for pitch in pitches
        if not is_rest(pitch)
    ])


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
    harmony_choice="Third below"
):
    """
    Build the playback from independent layers.

    Melody, harmony and metronome are separate tracks,
    each switched on or off, mixed together at the end.
    Everything off still clicks, so the result is never
    silence that looks like a failure.
    """

    pitches, durations = read_music(
        pitch_text,
        duration_text
    )

    bpm = check_bpm(bpm)

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

        harmony = make_harmony(
            pitches,
            key=key,
            steps=read_harmony_choice(harmony_choice)
        )

        sample_rate, harmony_track = make_melody(
            harmony,
            durations,
            bpm
        )

        layers.append(harmony_track)

    if len(layers) == 0:
        sound = [0.0] * total_samples

    elif len(layers) == 1:
        sound = layers[0]

    else:
        sound = mix_tracks(layers[0], layers[1])

    # The metronome always clicks when there are no notes,
    # so switching everything off gives a click track for
    # practising to rather than silence.
    if metronome or len(layers) == 0:
        sound = add_metronome(
            sound,
            sum(durations),
            bpm,
            sample_rate
        )

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
PART_CHOICES = ["Melody", "Harmony"]


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
    harmony_choice="Third below"
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

    pitches, durations = read_music(
        pitch_text,
        duration_text
    )

    if part == "Harmony":
        pitches = make_harmony(
            pitches,
            key=key,
            steps=read_harmony_choice(harmony_choice)
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

    if part == "Harmony":
        lines.append(
            "Judged against the harmony part."
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

    performance_plot = make_performance_plot(
        pitches,
        durations,
        bpm,
        trace,
        transpose,
        lyrics
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


def part_notes(pitches, part, key, harmony_steps=-2):
    """
    The notes belonging to a part of the music.
    """

    if part == "Harmony":
        return make_harmony(
            pitches,
            key=key,
            steps=harmony_steps
        )

    return pitches


def make_practice_guide(
    pitch_text,
    duration_text,
    bpm,
    guide_choice,
    part="Melody",
    key="C",
    harmony_choice="Third below"
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
                read_harmony_choice(harmony_choice)
            ),
            durations,
            bpm
        )

    elif guide_choice == "The other part":

        other = "Harmony" if part == "Melody" else "Melody"

        sample_rate, sound = make_melody(
            part_notes(
                pitches, other, key,
                read_harmony_choice(harmony_choice)
            ),
            durations,
            bpm
        )

    else:
        raise MusicInputError(
            f"'{guide_choice}' is not a guide option."
        )

    sound = add_metronome(
        sound,
        sum(durations),
        bpm,
        sample_rate
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
    harmony_choice="Third below"
):
    """
    Draw the target music as a score-like picture.

    The same picture the comparison draws, without a
    performance on it: something to study before singing.
    When the harmony is switched on it appears as a second
    voice, the way a duet is printed.
    """

    pitches, durations = read_music(
        pitch_text,
        duration_text
    )

    bpm = check_bpm(bpm)

    lyrics = read_lyrics(
        lyric_text,
        sung_count(pitches)
    )

    harmony = None

    if harmony_on:
        harmony = make_harmony(
            pitches,
            key=key,
            steps=read_harmony_choice(harmony_choice)
        )

    return make_performance_plot(
        pitches,
        durations,
        bpm,
        trace=None,
        lyrics=lyrics,
        title="The target music",
        harmony=harmony
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

    from midi_import import describe_tracks, MidiImportError

    if file_path is None:
        raise MusicInputError(
            "Choose a MIDI file first."
        )

    try:
        described = describe_tracks(file_path)

    except MidiImportError as problem:
        raise MusicInputError(str(problem))

    return [label for _, label in described]


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
        described = describe_phrases(
            file_path,
            track_number_from(track_label)
        )

    except MidiImportError as problem:
        raise MusicInputError(str(problem))

    return [WHOLE_TRACK] + [label for _, label in described]


# The dropdown entry meaning no phrase in particular.
WHOLE_TRACK = "Whole track"


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
    Read the track number back out of a dropdown label.
    """

    if label is None:
        return None

    try:
        return int(label.split()[1])

    except (IndexError, ValueError):
        return None


def import_midi_file(
    file_path,
    track_label=None,
    phrase_label=None
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
        pitch_text, duration_text, lyric_text, bpm = (
            import_midi(
                file_path,
                track_number=track_number_from(track_label),
                phrase_number=phrase_number_from(phrase_label)
            )
        )

    except MidiImportError as problem:
        raise MusicInputError(str(problem))

    note_count = len(pitch_text.split())

    if track_label is None:
        source = "every track together"

    else:
        source = f"track {track_number_from(track_label)}"

    phrase_number = phrase_number_from(phrase_label)

    if phrase_number is not None:
        source += f", phrase {phrase_number + 1}"

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

    return (
        pitch_text,
        duration_text,
        lyric_text,
        bpm,
        " ".join(lines)
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

    return pitches, durations, lyrics, "C"


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
        "A3 D4 D4 D4 D4 F4 A4 A4 A4 R"
    )

    durations = (
        "1/2 1/2 1/4 1/4 1/2 1/2 1/2 1/2 1 3/2"
    )

    lyrics = (
        "There once was a ship that put to sea"
    )

    return pitches, durations, lyrics, "F"