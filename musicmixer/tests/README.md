# Running the mixer's end-to-end tests

## One-time setup

```bash
pip install pytest-playwright
playwright install chromium
```

## Running

From the `musicmixer` folder, with the component already
built and installed (`gradio cc build` / `pip install -e .`
as usual - these tests run the real, built demo app, not a
mock of it):

```bash
pytest tests/test_mixer_e2e.py -v
```

Add `--headed` to watch the browser while it runs, which is
worth doing the first time to see it's actually clicking the
right things rather than just trusting green dots:

```bash
pytest tests/test_mixer_e2e.py -v --headed
```

## What's covered, and what deliberately isn't

Covered: clicking selects and highlights a bar; shift-click
completes a range, correctly whether the second bar is later
or earlier than the first; clicking outside an existing range
clears it; clicking inside one scrubs without changing it;
Clear selection removes it; the Repeat checkbox only appears
once a range exists; the Chart and Mixer panel toggles hide
and show their own panels without affecting each other.

Not covered, deliberately: whether the audio actually sounds
right. Playwright can't assert that, and mocking the Web
Audio API to manufacture coverage would be a lot of brittle
test code protecting against very little. That stays a
by-ear check, the same way it's been checked all session.

## If a test fails

The fixture in `conftest.py` launches the real `demo/app.py`
as a subprocess and captures its output - a failure's
traceback will include what the server printed, which is
usually enough to tell whether it's the browser interaction
or the server itself that broke.

If `mixer_url` times out waiting for a port: run
`python demo/app.py` by hand first and check it starts
cleanly - the fixture assumes it will, same as every manual
test this session did.

## Not yet verified

These tests were written but not run against a live browser -
there's no way to launch one from where they were written.
The first real run is the one that actually confirms the
selectors match what Gradio renders (in particular, that its
shadow DOM is open enough for Playwright's locators to pierce
it, which is normally the case but hasn't been checked against
this specific setup). Treat the first `pytest` run the way
every other change this session was treated: as the thing
that tells you whether it's right, not the writing of it.
