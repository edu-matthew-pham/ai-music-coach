# midi_import.py

"""
Read a MIDI file into the app's three textboxes.

A MIDI file is already the app's data model: pitches with
start times and lengths, plus a tempo. This module reads a
melody line out of one and turns it into the pitch,
duration and lyric text the rest of the app runs on.

What it deliberately does not attempt: polyphony. When two
notes sound at once, the highest is kept, on the grounds
that the melody usually sits on top. Files exported from
notation software, one voice per track, import cleanly.
Dense piano arrangements will come out as their top line.
"""

import mido

from notes import midi_to_note


class MidiImportError(ValueError):
    """
    Something about the file stops it importing.

    The message is written to be shown to the person who
    chose the file.
    """


# The note lengths the app works in, as fractions of a
# beat. Real performances land between the cracks, so an
# imported length snaps to the nearest of these.
BEAT_FRACTIONS = [
    0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0
]


def snap_to_beat(beats):
    """
    Round a duration to the nearest musical note length.
    """

    best = BEAT_FRACTIONS[0]

    for fraction in BEAT_FRACTIONS:
        if abs(beats - fraction) < abs(beats - best):
            best = fraction

    return best


def read_notes(midi_file):
    """
    Collect every note in the file with its absolute start
    time and length, in beats.

    Returns a list of (start_beats, length_beats, midi_number)
    and the first tempo found, as beats per minute.
    """

    ticks_per_beat = midi_file.ticks_per_beat

    bpm = None

    notes = []

    for track in midi_file.tracks:

        time_ticks = 0
        sounding = {}

        for message in track:

            time_ticks += message.time

            if message.type == "set_tempo" and bpm is None:
                bpm = round(mido.tempo2bpm(message.tempo))

            elif message.type == "note_on" and message.velocity > 0:
                sounding[message.note] = time_ticks

            elif message.type in ("note_off", "note_on"):

                # A note_on with zero velocity is the other
                # accepted way of ending a note.
                started = sounding.pop(message.note, None)

                if started is None:
                    continue

                start_beats = started / ticks_per_beat
                length_beats = (
                    time_ticks - started
                ) / ticks_per_beat

                if length_beats > 0:
                    notes.append(
                        (start_beats, length_beats, message.note)
                    )

    if bpm is None:
        bpm = 120

    return notes, bpm


def keep_melody(notes):
    """
    Reduce overlapping notes to a single line.

    Notes are grouped by start time, and where several
    start together, the highest wins. A note swallowed
    entirely by a longer, higher one is dropped.
    """

    notes = sorted(notes)

    melody = []

    for start, length, midi_number in notes:

        if melody:

            last_start, last_length, last_midi = melody[-1]

            same_start = abs(start - last_start) < 0.05

            if same_start:

                if midi_number > last_midi:
                    melody[-1] = (start, length, midi_number)

                continue

            # Trim the previous note if this one interrupts.
            if start < last_start + last_length:
                melody[-1] = (
                    last_start,
                    start - last_start,
                    last_midi
                )

        melody.append((start, length, midi_number))

    return melody


def import_midi(path, maximum_notes=64):
    """
    Turn a MIDI file into pitch, duration and lyric text.

    Returns (pitch_text, duration_text, lyric_text, bpm).
    Lyrics come back when the file carries them aligned to
    notes, as karaoke files do, and empty otherwise.
    """

    try:
        midi_file = mido.MidiFile(path)

    except Exception:
        raise MidiImportError(
            "That file could not be read as MIDI."
        )

    notes, bpm = read_notes(midi_file)

    if len(notes) == 0:
        raise MidiImportError(
            "No notes were found in that file."
        )

    melody = keep_melody(notes)

    if len(melody) > maximum_notes:
        melody = melody[:maximum_notes]

    pitches = []
    durations = []

    for start, length, midi_number in melody:

        pitches.append(
            midi_to_note(midi_number)
        )

        durations.append(
            snap_to_beat(length)
        )

    def show(value):
        if value == int(value):
            return str(int(value))
        return str(value)

    pitch_text = " ".join(pitches)

    duration_text = " ".join(
        show(value) for value in durations
    )

    lyric_text = read_lyric_text(midi_file, len(melody))

    return pitch_text, duration_text, lyric_text, bpm


def read_lyric_text(midi_file, note_count):
    """
    Collect karaoke-style lyrics when the file has them.

    MIDI lyrics arrive one syllable per event. Only a file
    whose syllable count matches its melody imports them;
    anything else returns empty rather than guessing at
    the alignment.
    """

    syllables = []

    for track in midi_file.tracks:
        for message in track:
            if message.type == "lyrics":
                text = message.text.strip()
                if text:
                    syllables.append(text)

    if len(syllables) != note_count:
        return ""

    return " ".join(syllables)
