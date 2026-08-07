# main.py

import gradio as gr

from music import (
    play_music,
    show_harmony,
    analyse_single_note,
    analyse_sequence,
    analyse_instrument,
    load_twinkle_phrase
)


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

    playback_mode = gr.Radio(
        [
            "Melody",
            "Harmony",
            "Melody + Harmony"
        ],
        value="Melody",
        label="Playback Mode",
        info="Choose a mode, then generate the audio below."
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

    harmony_output = gr.Textbox(
        label="Harmony Notes"
    )

    # -----------------------------------------------------
    # PERFORMANCE
    # -----------------------------------------------------

    gr.Markdown(
        "## Record a Performance"
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
    # EVENTS
    # -----------------------------------------------------

    example_button.click(
        fn=load_twinkle_phrase,
        outputs=[
            pitch_input,
            duration_input
        ]
    )

    generate_button.click(
        fn=play_music,
        inputs=[
            pitch_input,
            duration_input,
            key_input,
            playback_mode,
            bpm_input
        ],
        outputs=generated_audio
    )

    harmony_button.click(
        fn=show_harmony,
        inputs=[
            pitch_input,
            key_input
        ],
        outputs=harmony_output
    )

    detect_note_button.click(
        fn=analyse_single_note,
        inputs=recorded_audio,
        outputs=note_output
    )

    detect_sequence_button.click(
        fn=analyse_sequence,
        inputs=[
            recorded_audio,
            duration_input,
            bpm_input
        ],
        outputs=sequence_output
    )

    detect_instrument_button.click(
        fn=analyse_instrument,
        inputs=recorded_audio,
        outputs=instrument_output
    )


if __name__ == "__main__":
    demo.launch()