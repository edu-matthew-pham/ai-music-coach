# debug.py

"""
Optional detail about what the detector actually did.

The app shows a player what they need to know. This shows
what the code did to work that out, which is a different
thing and is only useful when something has gone wrong.

Turn it on by setting an environment variable before
starting the app:

    MUSIC_DEBUG=1 python main.py

Nothing here is shown in the interface. It all goes to the
terminal the app was started from.
"""

import os
import sys


def is_on():
    """
    Whether debug output has been switched on.

    Read every time rather than once at import, so it can
    be changed from a test without restarting anything.
    """

    setting = os.environ.get("MUSIC_DEBUG", "")

    return setting.strip().lower() in ("1", "true", "yes", "on")


def say(message):
    """
    Print one line of debug output, if it is switched on.
    """

    if not is_on():
        return

    print(message, file=sys.stderr)


def describe_window(
    position,
    start_time,
    end_time,
    listened_samples,
    sample_rate,
    voiced_frames,
    total_frames,
    frequency,
    confidence
):
    """
    Report what happened in one note's listening window.

    The two things worth watching are where the window
    landed, and how much of it held a steady pitch. A window
    that has slipped off the note shows up as a low voiced
    count, or as a frequency belonging to the note before.
    """

    if not is_on():
        return

    listened_seconds = listened_samples / sample_rate

    if total_frames == 0:
        voiced_share = 0.0

    else:
        voiced_share = voiced_frames / total_frames

    if frequency is None:
        heard = "nothing"

    else:
        heard = f"{frequency:7.2f} Hz"

    say(
        f"  note {position + 1:>2}  "
        f"window {start_time:5.2f}s to {end_time:5.2f}s  "
        f"listened {listened_seconds:4.2f}s  "
        f"voiced {voiced_share:5.0%}  "
        f"confidence {confidence:4.2f}  "
        f"heard {heard}"
    )


def describe_recording(
    total_samples,
    sample_rate,
    trimmed_samples,
    expected_seconds
):
    """
    Report the shape of the recording as a whole.

    A recording much shorter than the music expects is the
    usual reason the last few notes come back empty.
    """

    if not is_on():
        return

    say("")
    say("--- performance ---")

    say(
        f"  recorded {total_samples / sample_rate:.2f}s "
        f"at {sample_rate} Hz"
    )

    removed = (total_samples - trimmed_samples) / sample_rate

    say(
        f"  trimmed {removed:.2f}s of silence from the start"
    )

    say(
        f"  music expects {expected_seconds:.2f}s"
    )

    if trimmed_samples / sample_rate < expected_seconds * 0.9:
        say(
            "  recording is short: the last notes will "
            "have little or nothing to listen to"
        )
