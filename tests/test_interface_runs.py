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
