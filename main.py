# main.py

import os

import gradio as gr

from harmony import key_choices
from instrument_diagrams import INSTRUMENTS, show_instruments
from help_text import HELP_TEXT
from music import (
    MusicInputError,
    suggest_key,
    suggest_chords,
    describe_key_fit,
    OCTAVE_CHOICES,
    PART_CHOICES,
    GUIDE_CHOICES,
    HARMONY_STYLES,
    make_practice_guide,
    show_target_music,
    load_wellerman_phrase,
    import_midi_file,
    list_midi_tracks,
    list_midi_phrases,
    list_phrases,
    phrase_chosen,
    selected_piece,
    phrase_number_from,
    play_music,
    analyse_performance,
    load_twinkle,
    load_wellerman
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


ANCHOR_CSS = """
.anchor-nav {
    position: sticky;
    top: 0;
    z-index: 100;
    background: var(--body-background-fill);
    border-bottom: 1px solid var(--border-color-primary);
    padding: 8px 0;
}
.anchor-nav a {
    margin-right: 24px;
    font-weight: 600;
    text-decoration: none;
}
"""


def anchor_link(label, target):
    """
    A navigation link that scrolls to a section.

    Plain anchors and a scroll call together, so it works
    whether or not the page honours fragment links.
    """

    return (
        f'<a href="#{target}" onclick="'
        f"document.getElementById('{target}')"
        f".scrollIntoView({{behavior: 'smooth'}}); "
        f'return false;">{label}</a>'
    )


with gr.Blocks(
    title="AI Music Coach"
) as demo:

    gr.Markdown(
        "# AI Music Coach"
    )

    gr.Markdown(
        "Load a piece of music, get its reading right by "
        "ear, then practise singing it and see how you did."
    )

    # chart_notes is the imported polyphony, kept for the
    # plot asides and Suggest chords. KNOWN HAZARD, logged
    # in DESIGN.md: it is filled by import only, so heavy
    # edits to the boxes leave it describing music that has
    # changed, with no staleness signal. Anything newly
    # wired to it inherits that.
    chart_notes_state = gr.State(None)

    gr.HTML(
        '<div class="anchor-nav">'
        + anchor_link("Song", "song")
        + anchor_link("Arrange", "arrange")
        + anchor_link("Practice", "practice")
        + anchor_link("Instruments", "instruments")
        + "</div>"
    )

    with gr.Column():

        # -------------------------------------------------
        # SONG: get music into the boxes
        # -------------------------------------------------

        with gr.Column(elem_id="song"):

            gr.Markdown("## Song")

            with gr.Accordion("How to use this", open=False):
                gr.Markdown(HELP_TEXT)

            gr.Markdown(
                "Load an example, or import a MIDI file. "
                "Either fills the music boxes on the "
                "Arrange tab, where everything can be "
                "edited afterwards."
            )

            with gr.Row():

                example_button = gr.Button(
                    "Load Twinkle"
                )

                wellerman_button = gr.Button(
                    "Load Wellerman"
                )

            midi_upload = gr.File(
                label="Or import a MIDI file",
                file_types=[".mid", ".midi"],
                type="filepath"
            )

            track_input = gr.Dropdown(
                [],
                label="Which track to import",
                info="Choral and band files hold one track "
                     "per part. Pick the line you want to "
                     "practise.",
                visible=False
            )

            import_feedback = gr.Textbox(
                label="Import",
                interactive=False,
                visible=False
            )

        # -------------------------------------------------
        # ARRANGE: get the reading right, by eye and ear
        # -------------------------------------------------

        with gr.Column(elem_id="arrange"):

            gr.Markdown("## Arrange")

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

            lyric_input = gr.Textbox(
                label="Lyrics (optional)",
                value="Twin- kle twin- kle lit- tle star",
                lines=5,
                max_lines=20,
                info="One syllable per note. A trailing hyphen "
                     "joins a word across notes, _ holds a "
                     "syllable through another note. Each line is "
                     "a phrase: press Enter to divide one, "
                     "Backspace to join two."
            )

            with gr.Row():

                update_phrases_button = gr.Button(
                    "Update phrases",
                    size="sm"
                )

                phrase_input = gr.Dropdown(
                    [],
                    label="Which phrase to practise",
                    info="Each line of the lyrics is a phrase. "
                         "Press Enter in the lyrics to add one, "
                         "or Backspace to join two.",
                    visible=False
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

            detect_chords_button = gr.Button(
                "Suggest chords",
                size="sm"
            )

            chart_input = gr.Textbox(
                label="Chords (optional)",
                value="",
                info="A chart in bars of beats, as in "
                     "| Dm . Bb . | F . . . |  Each token is one "
                     "beat and a dot holds the chord on. The bars "
                     "set the metre, so | C . . | is three four."
            )

            gr.Markdown(
                "### Hear the reading"
            )

            gr.Markdown(
                "Each part has its own level. Nought is "
                "silent; a quiet harmony can sit under a "
                "full melody. Levels are read when the "
                "playback is generated."
            )

            with gr.Row():

                melody_input = gr.Slider(
                    0, 1, value=1.0, step=0.05,
                    label="Melody"
                )

                harmony_above_input = gr.Slider(
                    0, 1, value=0.0, step=0.05,
                    label="Harmony above"
                )

                harmony_below_input = gr.Slider(
                    0, 1, value=0.0, step=0.05,
                    label="Harmony below"
                )

                bass_input = gr.Slider(
                    0, 1, value=0.0, step=0.05,
                    label="Bass",
                    info="The root of each chord, held. "
                         "Needs a chord chart."
                )

                chords_input = gr.Slider(
                    0, 1, value=0.0, step=0.05,
                    label="Chords",
                    info="The chart, strummed, below the "
                         "melody."
                )

                metronome_input = gr.Slider(
                    0, 1, value=0.5, step=0.05,
                    label="Metronome",
                    info="Clicks under the music. Always "
                         "audible when no parts are."
                )

            harmony_style_input = gr.Dropdown(
                HARMONY_STYLES,
                value="Thirds, chord-corrected",
                label="Harmony style",
                info="Both harmony lines are built this way. "
                     "Corrected thirds shadow the tune and "
                     "bend where the third would clash. Chord "
                     "tones follow the chords instead. With "
                     "no chart, all of them are plain thirds."
            )

            # Show Harmony Notes was removed here. It showed
            # plain thirds whatever the style or chart, so it
            # displayed something different from what played.
            # The want behind it was real, and bigger than
            # the button: letting the player edit the
            # generated harmony, bass, or chord voicings by
            # hand - the music editor direction. Parked, not
            # rejected; if it returns, the lines become
            # editable boxes like the chart, not a display.
            with gr.Row():

                previous_button = gr.Button(
                    "\u25c0 Previous phrase"
                )

                generate_button = gr.Button(
                    "Generate Playback",
                    variant="primary"
                )

                next_button = gr.Button(
                    "Next phrase \u25b6"
                )

            generated_audio = gr.Audio(
                label="Generated Music"
            )

            target_plot = gr.Plot(
                label="Target Music"
            )

        # -------------------------------------------------
        # PRACTICE: sing it and see how it went
        # -------------------------------------------------

        with gr.Column(elem_id="practice"):

            gr.Markdown("## Practice")

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

        # -------------------------------------------------
        # INSTRUMENTS: where the key sits under the hands
        # -------------------------------------------------

        with gr.Column(elem_id="instruments"):

            gr.Markdown("## Instruments")

            gr.Markdown(
                "Where the notes of the key sit on an "
                "instrument, for working a line out by "
                "hand. This follows the key box above: "
                "change the key and the picture follows."
            )

            # Several at once rather than one from a list:
            # the violin's two positions read together are
            # what show the shift, and a singer often wants
            # the piano beside whatever they are holding.
            instrument_input = gr.CheckboxGroup(
                INSTRUMENTS,
                value=[INSTRUMENTS[0]],
                label="Show",
                info="Any number at once. The violin "
                     "charts read in fingers and show one "
                     "hand position each."
            )

            instrument_diagram = gr.HTML()

    # -----------------------------------------------------
    # EVENTS
    # -----------------------------------------------------

    def show_key_report(pitch_text, duration_text):
        return gr.update(
            value=suggest_key(pitch_text, duration_text),
            visible=True
        )

    def phrases_now(pitch_text, duration_text, lyric_text,
                    chosen):
        """
        Rebuild the phrase list from the boxes.

        A line break added to the lyrics adds a phrase the
        moment it is typed, so the list follows the words
        rather than the file.
        """

        labels = list_phrases(pitch_text, duration_text, lyric_text)

        # What stays chosen is the phrase number, not the
        # label.
        #
        # The labels carry the words, so editing the lyrics
        # rewrites every one of them. Looking for the old
        # label among the new ones finds nothing and falls
        # back to the whole part, which then plays the
        # entire song: the correction appears to have made
        # things worse, when all that happened is the name
        # changed underneath it.
        number = phrase_chosen(chosen)

        if number is None:

            # Nothing in particular was chosen, so offer
            # the first phrase rather than the whole part.
            chosen = labels[1] if len(labels) > 1 else labels[0]

        elif number + 1 < len(labels):
            chosen = labels[number + 1]

        else:
            # Joining lines can leave the chosen phrase
            # numbered past the end.
            chosen = labels[-1]

        # And music divided for the first time needs the
        # dropdown to appear, having had nothing to show
        # until now.
        return gr.update(
            choices=labels,
            value=chosen,
            visible=len(labels) > 1
        )

    update_phrases_button.click(
        fn=phrases_now,
        inputs=[
            pitch_input,
            duration_input,
            lyric_input,
            phrase_input
        ],
        outputs=phrase_input
    )

    detect_chords_button.click(
        fn=guard(suggest_chords),
        inputs=[
            chart_notes_state,
            pitch_input,
            duration_input,
            key_input
        ],
        outputs=chart_input
    )

    detect_key_button.click(
        fn=guard(show_key_report),
        inputs=[pitch_input, duration_input],
        outputs=key_report
    )

    def load_example(name, loader):
        """
        Load a built in piece, saying what arrived.

        An example is a whole piece of music in itself, so
        the track of whatever was imported before no longer
        means anything and is put away. The phrase list and
        the feedback line are filled exactly as an import
        fills them: silence here made loading look like
        nothing had happened.
        """

        def loaded():

            (
                pitches, durations, lyrics, key, chart, tempo
            ) = loader()

            labels = list_phrases(pitches, durations, lyrics)

            count = len(labels) - 1 if len(labels) > 1 else 1

            sung = len([n for n in pitches.split() if n != "R"])

            feedback = (
                f"Loaded {name}: "
                f"{sung} notes in key {key}, "
                f"{count} phrase{'s' if count != 1 else ''}"
                f"{', chart filled' if chart.strip() else ''}, "
                f"at {tempo} BPM."
            )

            return (
                pitches,
                durations,
                lyrics,
                key,
                chart,
                tempo,
                None,
                gr.update(choices=[], value=None, visible=False),
                gr.update(
                    choices=labels,
                    value=labels[1] if len(labels) > 1 else labels[0],
                    visible=len(labels) > 1
                ),
                gr.update(value=feedback, visible=True)
            )

        return loaded

    example_outputs = [
        pitch_input,
        duration_input,
        lyric_input,
        key_input,
        chart_input,
        bpm_input,
        midi_upload,
        track_input,
        phrase_input,
        import_feedback
    ]

    example_button.click(
        fn=load_example("Twinkle Twinkle", load_twinkle),
        outputs=example_outputs
    )

    wellerman_button.click(
        fn=load_example("the Wellerman", load_wellerman),
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
        chart_input,
        key_input,
        chart_notes_state
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
        Import a part, whole.

        The boxes hold all of it, with the phrasing written
        into the lyrics as line breaks. The dropdown below
        is a view on that: choosing a phrase cuts to it
        without reloading anything, and pressing Enter in
        the lyrics changes where the phrases fall.
        """

        if file_path is None:
            return unchanged(len(music_outputs) + 1)

        (
            pitches,
            durations,
            lyrics,
            bpm,
            feedback,
            chart,
            chart_notes,
            key
        ) = import_midi_file(file_path, track_label)

        phrases = list_phrases(pitches, durations, lyrics)

        return (
            pitches,
            durations,
            lyrics,
            bpm,
            gr.update(value=feedback, visible=True),
            chart,
            key,
            chart_notes,
            gr.update(
                choices=phrases,
                # The first phrase, not the whole part.
                # A whole song is more than anyone
                # practises at once, and landing on it
                # makes the phrase list look like it does
                # nothing: playback runs the entire piece
                # however the lyrics are divided.
                value=phrases[1] if len(phrases) > 1 else phrases[0],
                visible=len(phrases) > 1
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

    # Choosing a phrase changes nothing in the boxes. It
    # is a view on the music already there, and the
    # handlers below cut to it when they run. Reloading the
    # file here is what made phrasing unfixable: the
    # dropdown was the only way to see a phrase and the
    # file was the only thing that decided them.

    play_inputs = [
        pitch_input,
        duration_input,
        key_input,
        melody_input,
        harmony_above_input,
        harmony_below_input,
        bpm_input,
        metronome_input,
        chart_input,
        chords_input,
        harmony_style_input,
        bass_input,
        lyric_input,
        phrase_input
    ]

    plot_inputs = [
        pitch_input,
        duration_input,
        bpm_input,
        lyric_input,
        key_input,
        harmony_above_input,
        harmony_below_input,
        chart_input,
        harmony_style_input,
        bass_input,
        chart_notes_state,
        phrase_input
    ]

    generate_button.click(
        fn=guard(play_music),
        inputs=play_inputs,
        outputs=generated_audio
    ).then(
        fn=guard(show_target_music),
        inputs=plot_inputs,
        outputs=target_plot
    )

    def cycle_phrase(step):
        """
        Move the phrase choice on by a step, wrapping.

        The dropdown stays the one home of the selection:
        this only chooses, and the playback that follows
        reads the boxes as any generate does. Labels are
        rebuilt first, so a lyric edited since the last
        press cannot strand the choice on a name that no
        longer exists.
        """

        def moved(pitch_text, duration_text, lyric_text,
                  chosen):

            labels = list_phrases(
                pitch_text, duration_text, lyric_text
            )

            # Only the numbered phrases are cycled; the
            # whole part is reached from the dropdown.
            count = len(labels) - 1

            if count < 1:
                return gr.update()

            number = phrase_chosen(chosen)

            if number is None:
                number = 0 if step > 0 else count - 1

            else:
                number = (number + step) % count

            return gr.update(
                choices=labels,
                value=labels[number + 1],
                visible=len(labels) > 1
            )

        return moved

    # The diagram reads the key box each time it is drawn,
    # so a key changed anywhere - typed, detected, or filled
    # by an import - redraws it rather than leaving a
    # picture of the key that used to be chosen.
    for control in (key_input, instrument_input):

        control.change(
            fn=show_instruments,
            inputs=[key_input, instrument_input],
            outputs=instrument_diagram
        )

    # And once when the page opens, so the section is never
    # an empty box waiting to be poked.
    demo.load(
        fn=show_instruments,
        inputs=[key_input, instrument_input],
        outputs=instrument_diagram
    )

    for button, step in (
        (previous_button, -1),
        (next_button, 1)
    ):

        button.click(
            fn=cycle_phrase(step),
            inputs=[
                pitch_input,
                duration_input,
                lyric_input,
                phrase_input
            ],
            outputs=phrase_input
        ).then(
            fn=guard(play_music),
            inputs=play_inputs,
            outputs=generated_audio
        ).then(
            fn=guard(show_target_music),
            inputs=plot_inputs,
            outputs=target_plot
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
            chart_input,
            harmony_style_input
        ],
        outputs=guide_audio
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
            chart_input,
            harmony_style_input,
            phrase_input
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
        server_port=port,
        css=ANCHOR_CSS
    )