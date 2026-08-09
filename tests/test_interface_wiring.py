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
    "import_and_show": 8,
    "import_track": 7,
    "reimport_phrase": 6
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
                assert len(node.value.elts) == 6

                return

    pytest.fail("music_outputs was not found")
