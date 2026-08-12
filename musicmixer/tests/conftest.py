# conftest.py
#
# The fixture every test in this folder shares: the real
# demo app, running as a real subprocess, exactly the way
# it has been run by hand all session. Nothing here is a
# mock or a stub - if this passes, the actual thing works,
# not a simulation of it.

import os
import queue
import re
import subprocess
import sys
import threading
from pathlib import Path

import pytest

DEMO = Path(__file__).resolve().parents[1] / "demo" / "app.py"

PORT_LINE = re.compile(r"http://127\.0\.0\.1:(\d+)")


def _pump_lines(pipe, out_queue):
    """
    Runs in a background thread. readline() blocks, which is
    fine here - it is only the main thread's queue.get() that
    needs an honest timeout, since a timeout wrapped around a
    blocking call only fires between calls, not during one.
    That was the bug in the first version of this fixture: the
    while-loop's deadline check never got a chance to run
    because a single readline() call never returned.
    """

    for line in iter(pipe.readline, ""):
        out_queue.put(line)
    out_queue.put(None)


@pytest.fixture(scope="session")
def mixer_url():
    """
    The real demo app, running for the length of the test
    session. One process serves every test in this folder,
    since starting it fresh per test would mean paying the
    audio-buffer decode cost repeatedly for no benefit - the
    tests are about interaction, not about isolating server
    state between them.

    The port is read from Gradio's own startup line rather
    than assumed from an environment variable, since whether
    launch() honours one wasn't checked against the real
    source - reading what it actually printed is the only
    way to be sure rather than guessing.
    """

    env = os.environ.copy()
    # A child process's stdout is block-buffered when it is
    # not a real terminal, which is exactly this case - its
    # print() calls can sit in a buffer well past when they
    # were written, so a reader waiting on them waits far
    # longer than the output actually took. This forces the
    # child to flush every line as it is printed.
    env["PYTHONUNBUFFERED"] = "1"

    process = subprocess.Popen(
        [sys.executable, str(DEMO)],
        cwd=str(DEMO.parent),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    lines: "queue.Queue[str | None]" = queue.Queue()
    pump = threading.Thread(
        target=_pump_lines, args=(process.stdout, lines), daemon=True
    )
    pump.start()

    port = None
    seen = []

    try:
        while True:
            try:
                # The real timeout: queue.get() actually
                # returns control after this long even if
                # nothing was ever put on the queue, unlike
                # readline() on its own.
                line = lines.get(timeout=30)

            except queue.Empty:
                raise RuntimeError(
                    "demo app printed nothing recognisable within 30s.\n"
                    "Output seen so far:\n" + "".join(seen) +
                    f"\nRun `python {DEMO}` by hand to see the rest."
                )

            if line is None:
                raise RuntimeError(
                    "demo app exited before it started serving.\n"
                    "Output seen:\n" + "".join(seen)
                )

            seen.append(line)
            match = PORT_LINE.search(line)

            if match:
                port = int(match.group(1))
                break

        yield f"http://127.0.0.1:{port}"

    finally:
        process.terminate()

        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

        # Drain whatever else is on the queue so a failure
        # message has the full picture, not just the start.
        remaining = []
        while True:
            try:
                item = lines.get_nowait()
            except queue.Empty:
                break
            if item is not None:
                remaining.append(item)

        if remaining:
            print("\n--- demo app output (after startup) ---\n" + "".join(remaining))