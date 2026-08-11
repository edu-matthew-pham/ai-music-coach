"""
The interface handlers actually run.

Everything else about main.py is checked by reading it:
how many values a handler returns, how many outputs it is
wired to. That catches a great deal and it did not catch
this - a handler calling a function nobody had imported,
which reads perfectly well and fails the moment anyone
presses the button.

The only way to find that is to run it. These tests build
the interface and call its handlers the way Gradio would,
so a name that does not exist is found here rather than by
someone using the app.
"""

import os

import pytest


def interface_handlers():
    """
    Build the interface and hand back its inner functions.

    The handlers are defined inside the Blocks context, so
    they are reached through the objects that hold them
    rather than imported.
    """

    import main

    return main


def test_the_interface_can_be_built():
    """
    Importing main.py builds the whole interface. A name
    used at the top level of it that does not exist is
    found immediately.
    """

    import main

    assert main.demo is not None


def test_every_name_a_handler_uses_exists():
    """
    A handler that calls something nobody imported reads
    perfectly well and fails only when the button is
    pressed. Checking the names against what the module
    actually has finds it without pressing anything.
    """

    import ast

    import main

    source = open(main.__file__).read()

    tree = ast.parse(source)

    import builtins

    # Everything the module can see.
    available = set(dir(main)) | set(dir(builtins))

    # Names bound anywhere inside the module, including
    # inside the interface, which dir() does not show.
    for node in ast.walk(tree):

        if isinstance(node, ast.Name) and isinstance(
            node.ctx, ast.Store
        ):
            available.add(node.id)

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):

            available.add(node.name)

            for argument in node.args.args:
                available.add(argument.arg)

            for argument in node.args.kwonlyargs:
                available.add(argument.arg)

            if node.args.vararg:
                available.add(node.args.vararg.arg)

            if node.args.kwarg:
                available.add(node.args.kwarg.arg)

        elif isinstance(node, ast.ExceptHandler) and node.name:
            available.add(node.name)

        elif isinstance(node, (ast.Import, ast.ImportFrom)):

            for alias in node.names:
                available.add(alias.asname or alias.name.split(".")[0])

    missing = set()

    for node in ast.walk(tree):

        if isinstance(node, ast.Name) and isinstance(
            node.ctx, ast.Load
        ):
            if node.id not in available:
                missing.add(node.id)

    assert not missing, f"used but never defined: {sorted(missing)}"


@pytest.mark.parametrize("name", [
    "d_ML_10791.mid",
    "o-holy-night-satb.mid"
])
def test_importing_a_file_through_the_interface(name):
    """
    The import path end to end, as pressing the button
    would run it: choose a file, take the first part, fill
    the boxes, offer the phrases.
    """

    from music import (
        list_midi_tracks,
        import_midi_file,
        list_phrases
    )

    path = os.path.join(
        os.path.dirname(__file__), "fixtures", "midi", name
    )

    if not os.path.exists(path):
        pytest.skip(f"{name} is not present")

    tracks = list_midi_tracks(path)

    assert tracks

    imported = import_midi_file(path, tracks[0])

    pitches, durations, lyrics = imported[0], imported[1], imported[2]

    phrases = list_phrases(pitches, durations, lyrics)

    # There is always something to choose, and choosing it
    # gives back music.
    assert phrases

    from music import selected_piece

    piece = selected_piece(
        pitches, durations, lyrics,
        imported[7], imported[5], phrases[-1]
    )

    assert len(piece) > 0


def test_loading_an_example_says_what_arrived():
    """
    Pressing an example button must not be silent: the
    feedback line says what landed, the way an import
    does, and the phrase dropdown is filled from the
    lyrics rather than cleared.
    """

    import main

    outputs = main.load_example(
        "the Wellerman", main.load_wellerman
    )()

    assert len(outputs) == 10

    feedback = outputs[9]

    assert feedback["visible"]
    assert "Wellerman" in feedback["value"]
    assert "phrase" in feedback["value"]
    assert "key F" in feedback["value"]


def test_the_instrument_diagram_follows_the_key_box():
    """
    The diagram is drawn from the key box each time, so a
    key changed anywhere - typed, detected, or filled by an
    import - redraws it. Holding the key it was last drawn
    for would leave a picture of a key nobody is in.
    """

    import main

    in_f = main.show_instruments("F", ["Piano"])
    in_d = main.show_instruments("D", ["Piano"])

    assert "F major" in in_f
    assert "Bb" in in_f

    assert "D major" in in_d
    assert "F#" in in_d

    assert in_f != in_d


def test_every_instrument_offered_can_be_drawn():
    """
    The dropdown and the module must agree: an option that
    cannot be drawn is a blank section with no explanation.
    """

    import main

    for instrument in main.INSTRUMENTS:
        assert "<svg" in main.show_instruments("C", [instrument])

    # And all of them together, which is what the toggles
    # allow: four pictures, each named.
    everything = main.show_instruments("C", main.INSTRUMENTS)

    assert everything.count("<svg") == len(main.INSTRUMENTS)

    for instrument in main.INSTRUMENTS:
        assert instrument in everything


def test_choosing_nothing_says_so_rather_than_going_blank():
    """
    Every box unticked is a legitimate choice, not a fault:
    the section says what to do instead of showing an empty
    space that looks broken.
    """

    import main

    shown = main.show_instruments("C", [])

    assert "<svg" not in shown
    assert "instrument" in shown.lower()


def test_transposing_writes_every_box_the_music_lives_in():
    """
    Transposing is one edit of the boxes. Everything
    downstream reads them when its own button is pressed,
    so the pitches, the key, the chart and the hidden
    polyphony have to travel together - and the target
    dropdown follows the music, so pressing again from
    where it landed is the obvious next gesture.
    """

    import main

    out = main.transpose_to(
        "C4 E4 G4", "C", "| C . Am . |", [(0.0, 1.0, 60)], "D"
    )

    pitches, key, chart, notes, said, target = out

    assert pitches == "D4 F#4 A4"
    assert key == "D"
    assert chart == "| D . Bm . |"
    assert notes == [(0.0, 1.0, 62)]
    assert target == "D"
    assert "C to D" in said


def test_transposing_to_the_key_it_is_in_changes_nothing():
    """
    Pressing Transpose on the key already showing is a
    reasonable thing to do by accident, and must not shift
    the music by an octave or rewrite anything.
    """

    import main

    out = main.transpose_to("C4", "C", "| C . . . |", None, "C")

    assert "Already in C" in out[4]


def test_the_octave_buttons_leave_the_key_alone():
    import main

    down = main.transpose_octave(-1)

    pitches, key, chart, notes, said, target = down(
        "C4 E4", "C", "| C . . . |", None
    )

    assert pitches == "C3 E3"
    assert key == "C"
    assert chart == "| C . . . |"
    assert "down 12" in said


def test_correcting_lyrics_writes_the_box_and_reports():
    """
    The paste corrects the lyrics box in place. Everything
    downstream reads that box, so the corrected words
    travel to the phrases, the picture and the judging
    without being told - and the count is unchanged, so
    they still fit the notes.
    """

    import main

    fixed, report = main.merge_lyrics(
        "TWIN KLE TWIN KLE LIT TLE STAR",
        "Twin- kle twin- kle lit- tle star"
    )

    assert len(fixed.split()) == 7
    assert fixed == "Twin- kle twin- kle lit- tle star"
    assert "Corrected 1" in report