# main.py

import gradio as gr

from music import (
    MusicInputError,
    OCTAVE_CHOICES,
    make_practice_guide,
    show_target_music,
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

    pitch_input = gr.Textbox(
        label="Pitches",
        value="C4 C4 G4 G4 A4 A4 G4"
    )

    duration_input = gr.Textbox(
        label="Durations (beats)",
        value="1 1 1 1 1 1 2"
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
            ["C", "G", "D", "F"],
            value="C",
            label="Key"
        )

        bpm_input = gr.Number(
            value=120,
            label="BPM"
        )

    example_button = gr.Button(
        "Load Twinkle Phrase"
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
            label="Harmony",
            info="A third below, in the chosen key."
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

    guide_choice = gr.Radio(
        [
            "Clicks",
            "Melody",
            "No guide"
        ],
        value="Clicks",
        label="Guide while recording",
        info="Clicks keeps the recording clean. Melody "
             "plays the tune to sing along with."
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

    example_button.click(
        fn=load_twinkle_phrase,
        outputs=[
            pitch_input,
            duration_input,
            lyric_input
        ]
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
            metronome_input
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
            harmony_input
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

    recorded_audio.start_recording(
        fn=guard(make_practice_guide),
        inputs=[
            pitch_input,
            duration_input,
            bpm_input,
            guide_choice
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
            lyric_input
        ],
        outputs=[
            feedback_output,
            performance_plot,
            tuning_plot
        ]
    )


if __name__ == "__main__":
    demo.launch()