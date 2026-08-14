# test_mixer_e2e.py
#
# What these check: the interactions that were hand-tested,
# click by click, over the course of building this
# component - encoded once so a future change can't quietly
# break one of them without anyone noticing until much
# later. They are not a test of audio: Playwright cannot
# assert "this sounds right," and mocking the Web Audio API
# to fake coverage would protect against very little for a
# lot of brittle test code.
#
# The demo's readout Markdown is what most assertions read
# from. Its Python side (app.py:report) only ever says one
# of two things - "Nothing looped yet..." or "Looping X to
# Y (...)" - which makes it a clean, honest signal: it only
# changes when Python actually receives a new value, so an
# unchanged readout after a click is direct proof that
# click correctly did *not* round-trip to Python (a scrub),
# and a changed one proves it did.

import re

import pytest
from playwright.sync_api import Page, expect

LOOPING = re.compile(r"Looping ([\d.]+)s to ([\d.]+)s")
NOTHING_LOOPED = "Nothing looped yet"


def build_mixer(page: Page, url: str) -> None:
    page.goto(url)
    page.get_by_role("button", name="Build the mixer").click()
    expect(page.locator('[data-bar="1"]')).to_be_visible(timeout=15000)


def bar(page: Page, number: int):
    return page.locator(f'[data-bar="{number}"]')


def readout_text(page: Page) -> str:
    return page.locator("text=/Nothing looped|Looping/").first.inner_text()


class TestSelection:
    def test_clicking_a_bar_highlights_it(self, page: Page, mixer_url: str):
        build_mixer(page, mixer_url)

        bar(page, 3).click()

        expect(bar(page, 3)).to_have_class(re.compile(r"\bplaying\b"))

    def test_shift_click_completes_a_range_forward(self, page: Page, mixer_url: str):
        build_mixer(page, mixer_url)

        bar(page, 2).click()
        bar(page, 6).click(modifiers=["Shift"])

        match = LOOPING.search(readout_text(page))
        assert match, "expected a completed range in the readout"

        start, end = float(match.group(1)), float(match.group(2))
        assert start == pytest.approx(1.0, abs=0.1)
        assert end == pytest.approx(6.0, abs=0.1)

    def test_shift_click_completes_a_range_backward(self, page: Page, mixer_url: str):
        # The same range, selected in the opposite order -
        # this is the case that was silently broken before
        # the anchor-based fix: clicking a later bar first
        # collapsed the range to a fraction of a second
        # instead of spanning both bars.
        build_mixer(page, mixer_url)

        bar(page, 6).click()
        bar(page, 2).click(modifiers=["Shift"])

        match = LOOPING.search(readout_text(page))
        assert match, "expected a completed range in the readout"

        start, end = float(match.group(1)), float(match.group(2))
        assert start == pytest.approx(1.0, abs=0.1)
        assert end == pytest.approx(6.0, abs=0.1)

    def test_clicking_outside_the_range_clears_it(self, page: Page, mixer_url: str):
        build_mixer(page, mixer_url)

        bar(page, 2).click()
        bar(page, 6).click(modifiers=["Shift"])
        assert LOOPING.search(readout_text(page)), "range should be set up first"

        bar(page, 12).click()

        expect(page.locator(f"text={NOTHING_LOOPED}")).to_be_visible()

    def test_clicking_inside_the_range_does_not_change_it(
        self, page: Page, mixer_url: str
    ):
        build_mixer(page, mixer_url)

        bar(page, 2).click()
        bar(page, 6).click(modifiers=["Shift"])
        before = readout_text(page)

        bar(page, 4).click()

        # No round trip should have happened for a scrub -
        # the readout is Python's own text, so it can only
        # differ if Python was actually called again.
        after = readout_text(page)
        assert after == before

    def test_clear_selection_removes_the_range(self, page: Page, mixer_url: str):
        build_mixer(page, mixer_url)

        bar(page, 2).click()
        bar(page, 6).click(modifiers=["Shift"])
        assert LOOPING.search(readout_text(page))

        page.get_by_role("button", name="Clear selection").click()

        expect(page.locator(f"text={NOTHING_LOOPED}")).to_be_visible()


class TestSongChange:
    def test_a_loop_in_one_song_does_not_survive_a_different_song(
        self, page: Page, mixer_url: str
    ):
        # The bug: a loop is seconds into a specific song's
        # timeline. Loading a different song used to leave the
        # old loop sitting there in the engine, meaning nothing
        # until Play was next pressed, at which point it would
        # loop the wrong stretch of the new song - or a stretch
        # past its end entirely.
        build_mixer(page, mixer_url)

        bar(page, 2).click()
        bar(page, 6).click(modifiers=["Shift"])

        # Confirm the loop is really set before switching songs
        # - otherwise this test would pass even if nothing
        # about the fix worked.
        expect(page.locator(".bar.looped").first).to_be_visible()

        page.get_by_role("button", name="Load a different song").click()

        # The new song's own bar 1 arriving is the sign that the
        # remount has actually happened with new music, not just
        # that the click registered.
        expect(bar(page, 1)).to_be_visible(timeout=15000)

        # No bar should carry a loop from a song that is no
        # longer loaded, and the strip's own note should read
        # exactly as it would if nothing had ever been selected.
        expect(page.locator(".bar.looped")).to_have_count(0)
        expect(
            page.locator("text=Click a bar to select where Play starts")
        ).to_be_visible()


class TestToggles:
    def test_repeat_only_appears_once_a_range_exists(self, page: Page, mixer_url: str):
        build_mixer(page, mixer_url)

        expect(page.get_by_label("Repeat")).to_have_count(0)

        bar(page, 2).click()
        bar(page, 6).click(modifiers=["Shift"])

        expect(page.get_by_label("Repeat")).to_be_visible()

    def test_chart_toggle_hides_and_shows_the_strip(self, page: Page, mixer_url: str):
        build_mixer(page, mixer_url)

        expect(bar(page, 1)).to_be_visible()

        page.get_by_label("Chart").uncheck()
        expect(bar(page, 1)).not_to_be_visible()

        page.get_by_label("Chart").check()
        expect(bar(page, 1)).to_be_visible()

    def test_mixer_toggle_hides_and_shows_the_faders(self, page: Page, mixer_url: str):
        build_mixer(page, mixer_url)

        melody_fader = page.locator("input[type=range]").first
        expect(melody_fader).to_be_visible()

        page.get_by_label("Mixer", exact=True).uncheck()
        expect(melody_fader).not_to_be_visible()

        page.get_by_label("Mixer", exact=True).check()
        expect(melody_fader).to_be_visible()