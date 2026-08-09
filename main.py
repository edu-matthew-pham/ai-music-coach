# main.py

import os

import gradio as gr

from harmony import MAJOR_SCALES, key_choices
from help_text import HELP_TEXT
from music import (
    MusicInputError,
    suggest_key,
    describe_key_fit,
    OCTAVE_CHOICES,
    PART_CHOICES,
    GUIDE_CHOICES,
    HARMONY_CHOICES,
    HARMONY_STYLES,
    make_practice_guide,
    show_target_music,
    load_wellerman_phrase,
    import_midi_file,
    list_midi_tracks,
    list_midi_phrases,
    play_music,
    show_harmony,
    analyse_single_note,
    analyse_sequence,
    analyse_instrument,
    analyse_performance,
    load_twinkle_phrase
)


def guard(function):
    """
    Turn our own input errors into Gradio messages.

    music.py raises MusicInputError with wording meant for
    the person using the app. Gradio only shows a message
    properly if it is a gr.Error, so it is converted here
    rather than making music.py know about the interface.
    """

    def wrapped(*arguments):

        try:
            return function(*arguments)

        except MusicInputError as problem:
            raise gr.Error(str(problem))

    return wrapped


with gr.Blocks(
    title="AI Music Coach"
) as demo:

    gr.Markdown(
        "# AI Music Coach"
    )

    gr.Markdown(
        "Test the music, audio and ML systems "
        "before connecting them into the full coach."
    )

    # -----------------------------------------------------
    # TARGET MUSIC
    # -----------------------------------------------------

    gr.Markdown(
        "## Target Music"
    )

    with gr.Accordion("How to use this", open=False):
        gr.Markdown(HELP_TEXT)

    pitch_input = gr.Textbox(
        label="Pitches",
        value="C4 C4 G4 G4 A4 A4 G4",
        info="Notes like C4, F#4 or Bb3. Write a rest as R."
    )

    duration_input = gr.Textbox(
        label="Durations (beats)",
        value="1 1 1 1 1 1 2",
        info="One length per note, as a fraction of a beat. "
             "1 is a beat, 1/2 an eighth note, 3/2 a dotted "
             "beat, 1/3 a triplet. Decimals work too."
    )

    chart_input = gr.Textbox(
        label="Chords (optional)",
        value="",
        info="A chart in bars of beats, as in "
             "| Dm . Bb . | F . . . |  Each token is one "
             "beat and a dot holds the chord on. The bars "
             "set the metre, so | C . . | is three four."
    )

    lyric_input = gr.Textbox(
        label="Lyrics (optional)",
        value="Twin- kle twin- kle lit- tle star",
        info="One syllable per note. A trailing hyphen "
             "joins a word across notes, _ holds a "
             "syllable through another note."
    )

    with gr.Row():

        key_input = gr.Dropdown(
            key_choices(),
            value="C",
            label="Key",
            info="A key signature belongs to a major key "
                 "and its relative minor equally. Notes "
                 "outside it are harmonised at the "
                 "nearest scale note."
        )

        bpm_input = gr.Number(
            value=120,
            label="BPM"
        )

    detect_key_button = gr.Button(
        "Detect key"
    )

    key_report = gr.Textbox(
        label="Key",
        interactive=False,
        visible=False,
        lines=8
    )

    with gr.Row():

        example_button = gr.Button(
            "Load Twinkle Phrase"
        )

        wellerman_button = gr.Button(
            "Load Wellerman Phrase"
        )

    midi_upload = gr.File(
        label="Or import a MIDI file",
        file_types=[".mid", ".midi"],
        type="filepath"
    )

    track_input = gr.Dropdown(
        [],
        label="Which track to import",
        info="Choral and band files hold one track per "
             "part. Pick the line you want to practise.",
        visible=False
    )

    phrase_input = gr.Dropdown(
        [],
        label="Which phrase to practise",
        info="A long piece is divided where the music "
             "rests. Pick a phrase, or take the whole "
             "track at once.",
        visible=False
    )

    import_feedback = gr.Textbox(
        label="Import",
        interactive=False,
        visible=False
    )

    # -----------------------------------------------------
    # PLAYBACK
    # -----------------------------------------------------

    gr.Markdown(
        "## Playback and Harmony"
    )

    with gr.Row():

        melody_input = gr.Checkbox(
            value=True,
            label="Melody"
        )

        harmony_input = gr.Checkbox(
            value=False,
            label="Harmony"
        )

        harmony_choice_input = gr.Dropdown(
            list(HARMONY_CHOICES),
            value="Third below",
            label="Harmony interval"
        )

        harmony_style_input = gr.Dropdown(
            HARMONY_STYLES,
            value="Thirds, chord-corrected",
            label="Harmony style",
            info="Corrected thirds shadow the tune and "
                 "bend where the third would clash. Chord "
                 "tones follow the chords instead. With "
                 "no chart, all of them are plain thirds."
        )

        bass_input = gr.Checkbox(
            value=False,
            label="Bass",
            info="The root of each chord, held. Needs a "
                 "chord chart."
        )

        chords_input = gr.Checkbox(
            value=False,
            label="Chords",
            info="Plays the chart, strummed, below the "
                 "melody."
        )

        metronome_input = gr.Checkbox(
            value=True,
            label="Metronome",
            info="Clicks under the music. Always on when "
                 "no notes are playing."
        )

    with gr.Row():

        generate_button = gr.Button(
            "Generate Playback"
        )

        harmony_button = gr.Button(
            "Show Harmony Notes"
        )

    generated_audio = gr.Audio(
        label="Generated Music"
    )

    target_plot = gr.Plot(
        label="Target Music"
    )

    harmony_output = gr.Textbox(
        label="Harmony Notes"
    )

    # -----------------------------------------------------
    # PERFORMANCE
    # -----------------------------------------------------

    gr.Markdown(
        "## Record a Performance"
    )

    gr.Markdown(
        "Press record and the guide starts by itself: "
        "four count-in clicks, then come in on the beat. "
        "Wear headphones to keep the guide out of the "
        "recording."
    )

    part_input = gr.Radio(
        PART_CHOICES,
        value="Melody",
        label="Part you are performing",
        info="Sets what the guide plays and what your "
             "recording is judged against. The bass part "
             "sings the root of each chord, so it needs a "
             "chord chart."
    )

    guide_choice = gr.Radio(
        GUIDE_CHOICES,
        value="Clicks",
        label="Guide while recording",
        info="Clicks keeps the recording clean. The other "
             "part plays the opposite line, for practising "
             "harmony against the melody."
    )

    guide_audio = gr.Audio(
        label="Guide",
        autoplay=True,
        interactive=False
    )

    recorded_audio = gr.Audio(
        sources=[
            "microphone",
            "upload"
        ],
        type="numpy",
        label="Performance"
    )

    # -----------------------------------------------------
    # DETECTORS
    # -----------------------------------------------------

    gr.Markdown(
        "## Test the Detectors"
    )

    with gr.Row():

        detect_note_button = gr.Button(
            "Detect One Note"
        )

        detect_sequence_button = gr.Button(
            "Detect Sequence"
        )

        detect_instrument_button = gr.Button(
            "Detect Instrument"
        )

    note_output = gr.Textbox(
        label="Pitch Detection"
    )

    sequence_output = gr.Textbox(
        label="Sequence Detection"
    )

    instrument_output = gr.Textbox(
        label="Instrument Detection",
        lines=4
    )

    # -----------------------------------------------------
    # COACHING
    # -----------------------------------------------------

    gr.Markdown(
        "## Compare Your Performance"
    )

    gr.Markdown(
        "Play the target music above, record yourself "
        "playing it, then compare the two."
    )

    octave_input = gr.Dropdown(
        list(OCTAVE_CHOICES),
        value="Same octave",
        label="Octave",
        info="Pick the octave you actually played in. "
             "Singers often sit an octave below the "
             "written music."
    )

    compare_button = gr.Button(
        "Compare Performance",
        variant="primary"
    )

    performance_plot = gr.Plot(
        label="Performance"
    )

    tuning_plot = gr.Plot(
        label="Tuning"
    )

    feedback_output = gr.Textbox(
        label="Feedback",
        lines=10
    )

    # -----------------------------------------------------
    # EVENTS
    # -----------------------------------------------------

    def show_key_report(pitch_text, duration_text):
        return gr.update(
            value=suggest_key(pitch_text, duration_text),
            visible=True
        )

    detect_key_button.click(
        fn=guard(show_key_report),
        inputs=[pitch_input, duration_input],
        outputs=key_report
    )

    def clear_import():
        """
        Put the import controls away.

        An example is a whole piece of music in itself, so
        the track and phrase of whatever was imported
        before no longer mean anything and must not be
        left on screen describing music that has gone.
        """

        return (
            None,
            gr.update(choices=[], value=None, visible=False),
            gr.update(choices=[], value=None, visible=False),
            gr.update(value="", visible=False)
        )

    def load_example(loader):
        """
        Load a built in phrase, clearing any import.
        """

        def loaded():
            return loader() + clear_import()

        return loaded

    example_outputs = [
        pitch_input,
        duration_input,
        lyric_input,
        key_input,
        chart_input,
        midi_upload,
        track_input,
        phrase_input,
        import_feedback
    ]

    example_button.click(
        fn=load_example(load_twinkle_phrase),
        outputs=example_outputs
    )

    wellerman_button.click(
        fn=load_example(load_wellerman_phrase),
        outputs=example_outputs
    )

    # An imported file brings no chords, so the chart is
    # cleared rather than left describing music that has
    # been replaced.
    music_outputs = [
        pitch_input,
        duration_input,
        lyric_input,
        bpm_input,
        import_feedback,
        chart_input
    ]

    def unchanged(count):
        """
        Leave every output exactly as it is.

        Clearing a dropdown fires its change event, so
        these handlers are called when there is no file
        and nothing to do. That is ordinary, not an error
        worth throwing in someone's face.
        """

        return tuple(gr.update() for _ in range(count))

    def import_track(file_path, track_label):
        """
        Import a track, and offer the phrases it holds.

        A whole piece is more than anyone practises at
        once, so it arrives divided where the music rests,
        with the first phrase loaded.
        """

        if file_path is None:
            return unchanged(len(music_outputs) + 1)

        phrases = list_midi_phrases(file_path, track_label)

        # Take the whole track when it is short enough to
        # be one phrase anyway, otherwise start with the
        # first phrase.
        chosen = phrases[0] if len(phrases) == 2 else phrases[1]

        pitches, durations, lyrics, bpm, feedback = (
            import_midi_file(file_path, track_label, chosen)
        )

        return (
            pitches,
            durations,
            lyrics,
            bpm,
            gr.update(value=feedback, visible=True),
            chart,
            gr.update(
                choices=phrases,
                value=chosen,
                visible=len(phrases) > 2
            )
        )

    def import_and_show(file_path):
        """
        Import a file, offering its tracks and phrases.
        """

        if file_path is None:
            return unchanged(len(music_outputs) + 2)

        tracks = list_midi_tracks(file_path)

        results = import_track(file_path, tracks[0])

        return results + (
            gr.update(
                choices=tracks,
                value=tracks[0],
                visible=len(tracks) > 1
            ),
        )

    def reimport_phrase(file_path, track_label, phrase_label):

        if file_path is None or phrase_label is None:
            return unchanged(len(music_outputs))

        pitches, durations, lyrics, bpm, feedback, chart = (
            import_midi_file(
                file_path, track_label, phrase_label
            )
        )

        return (
            pitches,
            durations,
            lyrics,
            bpm,
            gr.update(value=feedback, visible=True),
            chart
        )

    midi_upload.upload(
        fn=guard(import_and_show),
        inputs=midi_upload,
        outputs=music_outputs + [phrase_input, track_input]
    )

    track_input.change(
        fn=guard(import_track),
        inputs=[midi_upload, track_input],
        outputs=music_outputs + [phrase_input]
    )

    phrase_input.change(
        fn=guard(reimport_phrase),
        inputs=[midi_upload, track_input, phrase_input],
        outputs=music_outputs
    )

    generate_button.click(
        fn=guard(play_music),
        inputs=[
            pitch_input,
            duration_input,
            key_input,
            melody_input,
            harmony_input,
            bpm_input,
            metronome_input,
            harmony_choice_input,
            chart_input,
            chords_input,
            harmony_style_input,
            bass_input
        ],
        outputs=generated_audio
    ).then(
        fn=guard(show_target_music),
        inputs=[
            pitch_input,
            duration_input,
            bpm_input,
            lyric_input,
            key_input,
            harmony_input,
            harmony_choice_input,
            chart_input,
            harmony_style_input,
            bass_input
        ],
        outputs=target_plot
    )

    harmony_button.click(
        fn=guard(show_harmony),
        inputs=[
            pitch_input,
            key_input
        ],
        outputs=harmony_output
    )

    # Clearing before setting forces a fresh change on the
    # guide player every time, so recording again replays
    # the guide rather than sitting silent on old audio.
    recorded_audio.start_recording(
        fn=lambda: None,
        outputs=guide_audio
    ).then(
        fn=guard(make_practice_guide),
        inputs=[
            pitch_input,
            duration_input,
            bpm_input,
            guide_choice,
            part_input,
            key_input,
            harmony_choice_input,
            chart_input,
            harmony_style_input
        ],
        outputs=guide_audio
    )

    detect_note_button.click(
        fn=guard(analyse_single_note),
        inputs=recorded_audio,
        outputs=note_output
    )

    detect_sequence_button.click(
        fn=guard(analyse_sequence),
        inputs=[
            recorded_audio,
            duration_input,
            bpm_input
        ],
        outputs=sequence_output
    )

    detect_instrument_button.click(
        fn=guard(analyse_instrument),
        inputs=recorded_audio,
        outputs=instrument_output
    )

    compare_button.click(
        fn=guard(analyse_performance),
        inputs=[
            recorded_audio,
            pitch_input,
            duration_input,
            bpm_input,
            octave_input,
            lyric_input,
            part_input,
            key_input,
            harmony_choice_input,
            chart_input,
            harmony_style_input
        ],
        outputs=[
            feedback_output,
            performance_plot,
            tuning_plot
        ]
    )


if __name__ == "__main__":

    # Hosting reads the port from the environment and
    # expects the server on every interface, not just
    # localhost. Both fall back to the local defaults, so
    # running it on your own machine is unchanged.
    port = int(os.environ.get("PORT", 7860))

    demo.launch(
        server_name="0.0.0.0",
        server_port=port
    )