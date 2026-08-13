# main.py

import os

import gradio as gr

from harmony import key_choices
from gradio_musicmixer import MusicMixer
from lyric_merge import merge_lyrics
from mixer_data import mixer_data
from help_text import HELP_TEXT
from music import (
    MusicInputError,
    import_music_file,
    list_music_parts,
    transpose_music,
    describe_transpose,
    semitones_between,
    suggest_key,
    suggest_chords,
    describe_key_fit,
    OCTAVE_CHOICES,
    PART_CHOICES,
    GUIDE_CHOICES,
    HARMONY_STYLES,
    make_practice_guide,
    load_wellerman_phrase,
    import_midi_file,
    list_midi_tracks,
    list_midi_phrases,
    list_phrases,
    phrase_chosen,
    selected_piece,
    phrase_number_from,
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
/*
 * A sticky bar only sticks if nothing above it in the page
 * clips its scrolling. Gradio's wrappers set overflow on
 * several ancestors, and any one of them silently turns
 * position: sticky back into position: relative - no error,
 * the bar simply scrolls away. So the chain is cleared
 * first, then the bar is stuck.
 */
.gradio-container,
.gradio-container .main,
.gradio-container .wrap,
.gradio-container .contain,
.gradio-container > .wrap > .contain,
#component-0,
#anchor-nav-wrap {
    overflow: visible !important;
}

/*
 * Stuck on the component Gradio wraps the markup in, not on
 * the markup: styling the inner div leaves Gradio's own
 * block scrolling away with the bar inside it.
 */
#anchor-nav-wrap {
    position: -webkit-sticky !important;
    position: sticky !important;
    top: 0;
    z-index: 1000;
    background: var(--body-background-fill);
    border-bottom: 1px solid var(--border-color-primary);
    padding: 10px 0 8px;
    margin-bottom: 4px;
}
.anchor-nav a {
    margin-right: 24px;
    font-weight: 600;
    text-decoration: none;
    white-space: nowrap;
}
.anchor-nav a:hover {
    text-decoration: underline;
}

/*
 * A section jumped to should land below the bar rather than
 * under it.
 */
#song, #arrange, #practice, #playback {
    scroll-margin-top: 64px;
}

/*
 * Full screen is a CSS trick, not the browser's real
 * Fullscreen API: requestFullscreen() needs a container that
 * allows it, which an iframe embed (a Space, for instance)
 * may not grant, and there is no way to ask for that
 * permission from inside the page itself. Covering the whole
 * viewport with position: fixed works the same way from the
 * player's side and needs nothing granted from outside.
 *
 * Targets the mixer widget's own bordered box, not the whole
 * Playback section - the heading and the blurb above the
 * buttons are read once, not something worth taking screen
 * space away from the mixer every time this is pressed.
 */
#mixer-widget.fullscreen-mode {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 9999;
    background: var(--body-background-fill);
    overflow-y: auto;
    padding: 24px;
    margin: 0;
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
        elem_id="anchor-nav-wrap",
        value='<div class="anchor-nav">'
        + anchor_link("Song", "song")
        + anchor_link("Arrange", "arrange")
        + anchor_link("Playback", "playback")
        + anchor_link("Practice", "practice")
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
                label="Or import a file",
                file_types=[".mid", ".midi", ".mxl", ".musicxml", ".xml"],
                type="filepath"
            )

            # A score (.mxl from notation software) is the
            # better import where one exists: it states its
            # lengths, metre, key and words, so none of the
            # timing repair a performance needs has to run.
            gr.Markdown(
                "A MIDI performance, or a score exported "
                "from notation software (.mxl). A score "
                "carries its own written lengths and its "
                "words, so less has to be guessed at."
            )

            track_input = gr.Dropdown(
                [],
                label="Which part to import",
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

            with gr.Accordion("Edit the boxes directly", open=False):

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

                with gr.Accordion(
                    "Correct the lyrics from the words",
                    open=False
                ):

                    gr.Markdown(
                        "An imported file's lyrics are whatever "
                        "was typed into it: capitals, words split "
                        "at odd places, the arranger's name among "
                        "the words. Paste the words as written and "
                        "they are corrected in place.\n\n"
                        "Only the spelling changes. Nothing moves, "
                        "and the number of syllables stays the "
                        "same, so every word keeps the note it was "
                        "sung on. A line that does not match is "
                        "left as it was and named in the report.\n\n"
                        "The line breaks come from the paste too: "
                        "where the words are written as phrases, "
                        "that is better phrasing than the import "
                        "guessed. Press Update phrases afterwards."
                    )

                    pasted_lyrics = gr.Textbox(
                        label="The words, one line per phrase",
                        lines=6,
                        placeholder="Twinkle twinkle little star\n"
                                    "How I wonder what you are"
                    )

                    correct_lyrics_button = gr.Button(
                        "Correct lyrics",
                        size="sm"
                    )

                    lyric_report = gr.Markdown()

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

                # Transposing sits beside the key because it is
                # the other half of the same question: the key
                # box says how the music is written, this says
                # how high it sits. Changing the key respells;
                # transposing moves the sound.
                with gr.Row():

                    transpose_target = gr.Dropdown(
                        key_choices(),
                        value="C",
                        label="Transpose to",
                        info="Moves the notes, the key and the "
                             "chords together, by the shortest "
                             "way round."
                    )

                    transpose_button = gr.Button(
                        "Transpose",
                        size="sm"
                    )

                    octave_down_button = gr.Button(
                        "Octave down",
                        size="sm"
                    )

                    octave_up_button = gr.Button(
                        "Octave up",
                        size="sm"
                    )

                transpose_feedback = gr.Markdown()

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

                    next_button = gr.Button(
                        "Next phrase \u25b6"
                    )

        # -------------------------------------------------
        # PLAYBACK: hear the parts mixed together
        # -------------------------------------------------

        with gr.Column(elem_id="playback"):

            gr.Markdown("## Playback")

            gr.Markdown(
                "The parts sent separately and mixed in "
                "the browser, so a level can move while "
                "they are sounding. Nothing is made "
                "again when a fader moves - only its "
                "loudness changes.\n\n"
                "Built from the boxes when the button is "
                "pressed, for the whole piece. Edit "
                "anything above and press again.\n\n"
                "Has its own phrase list, to jump "
                "straight to any phrase's exact start "
                "and end, and its own chord strip along "
                "the top: click a bar to jump there, "
                "shift-click a second bar to loop that "
                "stretch."
            )

            with gr.Row():

                open_mixer_button = gr.Button(
                    "Generate Playback",
                    size="sm"
                )

                fullscreen_button = gr.Button(
                    "\u26f6 Full screen",
                    elem_id="playback-fullscreen-toggle",
                    size="sm"
                )

            mixer_output = MusicMixer(
                show_label=False, elem_id="mixer-widget"
            )

        # -------------------------------------------------
        # PRACTICE: sing it and see how it went
        # -------------------------------------------------

        with gr.Column(elem_id="practice"):

            gr.Markdown("## Practice")

            with gr.Accordion("Recording and comparing", open=False):

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

                second_opinion_input = gr.Checkbox(
                    value=False,
                    label="Second opinion on pitch",
                    info="Runs a second detector alongside the "
                         "first and says where they differ. "
                         "Useful on a microphone that loses the "
                         "bottom of a low voice. Needs crepe "
                         "installed; slower when on."
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

    def build_mixer(pitch_text, duration_text, key, bpm,
                    chart_text, harmony_style, lyric_text):
        """
        Build the live mixer for the whole piece.

        The mixer has its own phrase list, reached from
        Piece.phrases() directly, and jumps to a phrase's
        exact start and end in seconds. Handing it one
        phrase's worth of music instead of the whole part
        would mean its phrase list still showed the whole
        song's phrases but the audio underneath only ever
        covered one of them - clicking any other phrase
        would jump outside what had actually been sent.
        Always building the whole part is what the Wellerman
        demo does too, for the same reason.
        """

        return mixer_data(
            pitch_text, duration_text, key, bpm, chart_text,
            harmony_style, lyric_text, phrase_label="Whole part"
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

    correct_lyrics_button.click(
        fn=guard(merge_lyrics),
        inputs=[lyric_input, pasted_lyrics],
        outputs=[lyric_input, lyric_report]
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
        ) = import_music_file(file_path, track_label)

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

        tracks = list_music_parts(file_path)

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

    open_mixer_button.click(
        fn=guard(build_mixer),
        inputs=[
            pitch_input,
            duration_input,
            key_input,
            bpm_input,
            chart_input,
            harmony_style_input,
            lyric_input
        ],
        outputs=mixer_output
    )

    # Purely visual, so no Python round trip: the class does
    # everything, and the fixed-position CSS rule above does
    # the rest. Targets the mixer widget's own box, not the
    # whole Playback column, so the heading and blurb are not
    # dragged into the fullscreen view along with it. Escape
    # exits from anywhere, not just a second click on the
    # button, which is what a full-screen toggle is expected
    # to do - the listener is attached once and guarded
    # against being attached again, since this wiring runs
    # again on the page's own event bindings but the window
    # itself persists across that.
    fullscreen_button.click(
        fn=None,
        js="""
        () => {
            const widget = document.getElementById('mixer-widget');
            const active = widget.classList.toggle('fullscreen-mode');
            document.body.style.overflow = active ? 'hidden' : '';

            if (!window.__playbackFullscreenEscape) {
                window.__playbackFullscreenEscape = (event) => {
                    if (event.key === 'Escape') {
                        document.getElementById('mixer-widget')
                            .classList.remove('fullscreen-mode');
                        document.body.style.overflow = '';
                    }
                };
                window.addEventListener(
                    'keydown', window.__playbackFullscreenEscape
                );
            }
        }
        """
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

    def transposed(pitch_text, key, chart_text, chart_notes,
                   semitones):
        """
        Move the music and say what moved.

        Everything downstream reads the boxes when its own
        button is pressed, so writing them here is the
        whole of it: playback, the picture, the guide and
        the judging all follow without being told. The
        hidden polyphony is handed back too, because it
        lives in pitch rather than in a box and would
        otherwise describe the key the music has left.
        """

        pitches, new_key, chart, notes = transpose_music(
            pitch_text, key, chart_text, chart_notes, semitones
        )

        return (
            pitches,
            new_key,
            chart,
            notes,
            describe_transpose(key, new_key, semitones, pitches),
            # The dropdown follows the music, so pressing
            # again from where it landed is the obvious
            # next gesture.
            new_key
        )

    def transpose_to(pitch_text, key, chart_text, chart_notes,
                     target):
        """
        Transpose to a chosen key, the shortest way round.
        """

        semitones = semitones_between(key, target)

        if semitones == 0:
            return (
                gr.update(), gr.update(), gr.update(),
                gr.update(),
                f"Already in {key}.",
                gr.update()
            )

        return transposed(
            pitch_text, key, chart_text, chart_notes, semitones
        )

    def transpose_octave(step):
        """
        Move by a whole octave, which leaves the key alone.
        """

        def moved(pitch_text, key, chart_text, chart_notes):
            return transposed(
                pitch_text, key, chart_text, chart_notes,
                12 * step
            )

        return moved

    transpose_outputs = [
        pitch_input,
        key_input,
        chart_input,
        chart_notes_state,
        transpose_feedback,
        transpose_target
    ]

    transpose_button.click(
        fn=guard(transpose_to),
        inputs=[
            pitch_input,
            key_input,
            chart_input,
            chart_notes_state,
            transpose_target
        ],
        outputs=transpose_outputs
    )

    for button, step in (
        (octave_down_button, -1),
        (octave_up_button, 1)
    ):

        button.click(
            fn=guard(transpose_octave(step)),
            inputs=[
                pitch_input,
                key_input,
                chart_input,
                chart_notes_state
            ],
            outputs=transpose_outputs
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
            harmony_style_input,
            mixer_output
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
            phrase_input,
            second_opinion_input,
            mixer_output
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