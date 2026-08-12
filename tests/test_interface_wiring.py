"""
The interface's handlers must return what they are wired to.

Gradio checks this only when a control is used, so a
mismatch hides until someone presses the right button in
the right order and gets a stack trace instead of music.
Adding an output to a list and forgetting one of the
handlers that feeds it is an easy mistake, and this is the
only place it can be caught early.
"""

import ast
import os

import pytest


INTERFACE = os.path.join(
    os.path.dirname(__file__), "..", "main.py"
)


def parsed_interface():
    with open(INTERFACE) as source:
        return ast.parse(source.read())


def find_function(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node

    return None


def returned_counts(function):
    """
    How many values each return statement gives back.

    A return of a single value counts as one; a tuple
    counts its elements. Anything built by concatenation
    is skipped, since its length cannot be read here.
    """

    counts = []

    for node in ast.walk(function):

        if not isinstance(node, ast.Return):
            continue

        if node.value is None:
            continue

        if isinstance(node.value, ast.Tuple):
            counts.append(len(node.value.elts))

    return counts


# Each handler, and how many outputs it is wired to.
HANDLERS = {
    "import_and_show": 10,
    "import_track": 9
}


@pytest.mark.parametrize(
    "name,expected",
    sorted(HANDLERS.items())
)
def test_handlers_return_what_they_are_wired_to(name, expected):
    tree = parsed_interface()

    function = find_function(tree, name)

    assert function is not None, f"{name} is missing"

    for count in returned_counts(function):
        assert count == expected, (
            f"{name} returns {count} values but is wired "
            f"to {expected} outputs"
        )


# How many values each music function hands back. The
# interface has to unpack exactly this many, and a mistake
# here is invisible until someone presses the control.
RETURN_COUNTS = {
    "import_midi_file": 8,
    "list_midi_tracks": 1,
    "list_midi_phrases": 1
}


def test_handlers_unpack_what_the_music_layer_returns():
    """
    Returning the right number of values is only half of
    it: the handler also has to take apart what it is
    given. Adding a value to a music function and missing
    one of the places that unpacks it leaves an error
    waiting for whoever presses that button.
    """

    from music import import_midi_file

    tree = parsed_interface()

    for node in ast.walk(tree):

        if not isinstance(node, ast.Assign):
            continue

        call = node.value

        if not isinstance(call, ast.Call):
            continue

        name = getattr(call.func, "id", None)

        if name not in RETURN_COUNTS:
            continue

        for target in node.targets:

            if isinstance(target, ast.Tuple):

                assert len(target.elts) == RETURN_COUNTS[name], (
                    f"{name} returns {RETURN_COUNTS[name]} "
                    f"values but is unpacked into "
                    f"{len(target.elts)}"
                )


def test_the_return_counts_are_right():
    """
    The counts above are only useful while they match what
    the music layer actually does.
    """

    import inspect

    import music

    source = inspect.getsource(music.import_midi_file)

    # The final return of import_midi_file.
    tree = ast.parse(source)

    returns = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Return)
        and isinstance(node.value, ast.Tuple)
    ]

    assert returns

    for node in returns:
        assert len(node.value.elts) == RETURN_COUNTS["import_midi_file"]


def test_the_music_outputs_list_is_the_length_expected():
    """
    The counts above are only right while the list of
    music outputs is the length they assume.
    """

    tree = parsed_interface()

    for node in ast.walk(tree):

        if not isinstance(node, ast.Assign):
            continue

        for target in node.targets:

            if (
                isinstance(target, ast.Name)
                and target.id == "music_outputs"
            ):
                assert len(node.value.elts) == 8

                return

    pytest.fail("music_outputs was not found")


def test_every_handler_is_given_as_many_inputs_as_it_takes():
    """
    A function wired to fewer inputs than it has parameters
    runs perfectly well: the missing ones take their
    defaults, and the feature they control quietly does
    nothing.

    That is how the phrase selection came to be ignored by
    playback. The arguments were added to the function and
    to two of the three places that call it, and the third
    kept working, kept passing its tests, and kept playing
    the whole part when a phrase had been chosen. Nothing
    failed, which is what made it hard to see.
    """

    import inspect

    import music

    tree = parsed_interface()

    # Input lists shared between wirings are assigned to a
    # name first. The name hides the count, so the lists
    # are gathered here and looked through.
    named_lists = {}

    for node in ast.walk(tree):

        if not isinstance(node, ast.Assign):
            continue

        if not isinstance(node.value, ast.List):
            continue

        for target in node.targets:

            if isinstance(target, ast.Name):
                named_lists[target.id] = len(node.value.elts)

    checked = 0

    for node in ast.walk(tree):

        if not isinstance(node, ast.Call):
            continue

        # An event wiring: something.click(fn=..., inputs=...)
        handler = None
        inputs = None

        for keyword in node.keywords:

            if keyword.arg == "fn":
                handler = keyword.value

            elif keyword.arg == "inputs":
                inputs = keyword.value

        if handler is None or inputs is None:
            continue

        # Unwrap guard(...) around the handler.
        if isinstance(handler, ast.Call):

            if not handler.args:
                continue

            handler = handler.args[0]

        name = getattr(handler, "id", None)

        if name is None or not hasattr(music, name):
            continue

        function = getattr(music, name)

        if not callable(function):
            continue

        # How many the interface sends.
        if isinstance(inputs, ast.List):
            sent = len(inputs.elts)

        elif (
            isinstance(inputs, ast.Name)
            and inputs.id in named_lists
        ):
            sent = named_lists[inputs.id]

        else:
            sent = 1

        signature = inspect.signature(function)

        takes = len(signature.parameters)

        required = len([
            parameter
            for parameter in signature.parameters.values()
            if parameter.default is inspect.Parameter.empty
        ])

        checked += 1

        assert sent >= required, (
            f"{name} needs {required} inputs but is wired "
            f"to {sent}"
        )

        assert sent == takes, (
            f"{name} takes {takes} arguments but is wired "
            f"to {sent}: the last {takes - sent} would "
            f"silently keep their defaults"
        )

    # A floor on the scanner itself, not a target: enough
    # handlers checked here to know the AST walk is actually
    # matching something, rather than silently checking
    # zero. Three now that Generate Playback (play_music,
    # show_target_music) is retired - suggest_chords,
    # make_practice_guide and analyse_performance remain.
    assert checked >= 3