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


class TestBarGrouping:
    def test_a_bar_with_two_chord_changes_is_one_box(
        self, page: Page, mixer_url: str
    ):
        # Twinkle's own chart (loaded via "Load a different
        # song") has a genuine multi-chord bar: bar 2 is F
        # then C. Before the bar-grouped rewrite this would
        # have shown as two separate boxes, both claiming to
        # be sequential bars - here it must be exactly one
        # box, holding both chord names.
        build_mixer(page, mixer_url)

        page.get_by_role("button", name="Load a different song").click()
        expect(bar(page, 1)).to_be_visible(timeout=15000)

        second_bar = bar(page, 2)

        expect(second_bar).to_contain_text("F")
        expect(second_bar).to_contain_text("C")

        # Exactly one box claims to be bar 2 - not a second
        # box further along the strip also labelled "2".
        expect(page.locator('[data-bar="2"]')).to_have_count(1)

    def test_an_instrumental_intro_bar_is_present_and_numbered(
        self, page: Page, mixer_url: str
    ):
        # The original symptom: an intro bar with nothing
        # sung in it used to be invisible on the strip
        # entirely, swallowed into whichever chord-run box
        # happened to hold its chord. Bar 1 here has no
        # words at all; it must still get its own numbered
        # box, not be skipped or merged into bar 2.
        build_mixer(page, mixer_url)

        page.get_by_role("button", name="Load a wordless intro").click()
        expect(bar(page, 1)).to_be_visible(timeout=15000)

        first_bar = bar(page, 1)

        expect(first_bar).to_contain_text("Em")
        expect(first_bar.locator(".words")).to_have_text("")

        second_bar = bar(page, 2)

        expect(second_bar).to_contain_text("here we go now")


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

    def test_mixer_is_a_sheet_that_opens_from_the_mix_button(
        self, page: Page, mixer_url: str
    ):
        """
        The faders live in a sheet over the page, closed by
        default, opened from the Mix button beside the
        lyrics. Located by the dialog role and the fader's
        own label rather than "the first range input" - the
        earlier version of this test did that, and the first
        range input on the page is Transport's Volume
        slider, not a fader, so it was checking the wrong
        control.
        """
        build_mixer(page, mixer_url)

        sheet = page.get_by_role("dialog", name="Mixer")
        expect(sheet).to_have_count(0)

        page.get_by_role("button", name="Open the mixer").click()
        expect(sheet).to_be_visible()
        expect(sheet.get_by_text("Melody", exact=True)).to_be_visible()
        expect(sheet.locator("input[type=range]")).to_have_count(6)

        page.keyboard.press("Escape")
        expect(sheet).to_have_count(0)

        page.get_by_role("button", name="Open the mixer").click()
        expect(sheet).to_be_visible()
        page.get_by_role("button", name="Close mixer").click()
        expect(sheet).to_have_count(0)

    def test_mixer_toggle_hides_and_shows_the_mix_button(
        self, page: Page, mixer_url: str
    ):
        build_mixer(page, mixer_url)

        mix_button = page.get_by_role("button", name="Open the mixer")
        expect(mix_button).to_be_visible()

        page.get_by_label("Mixer", exact=True).uncheck()
        expect(mix_button).to_have_count(0)

        page.get_by_label("Mixer", exact=True).check()
        expect(mix_button).to_be_visible()


class TestInstrumentPreview:
    def test_preview_row_shows_the_chosen_number_of_upcoming_chords(
        self, page: Page, mixer_url: str
    ):
        """
        Two upcoming chords by default, drawn under the current
        one, each named; the count control changes how many;
        off removes the row entirely. Piano is on by default
        so its row is the one checked.
        """
        build_mixer(page, mixer_url)
        bar(page, 1).click()

        row = page.locator('[data-preview-row="Piano"]')
        expect(row).to_be_visible()
        expect(row.locator(".preview-chord")).to_have_count(2)
        expect(row.locator(".preview-name").first).not_to_have_text("")

        page.get_by_role("radiogroup", name="Chords to preview").get_by_label(
            "3", exact=True
        ).check()
        expect(row.locator(".preview-chord")).to_have_count(3)

        page.get_by_role("radiogroup", name="Chords to preview").get_by_label(
            "off", exact=True
        ).check()
        expect(row).to_have_count(0)

    def test_preview_row_matches_the_main_diagrams_width(
        self, page: Page, mixer_url: str
    ):
        # The row totals the main diagram's own measured
        # width rather than a fixed fraction of it - at 2
        # upcoming chords each preview is roughly half that
        # width (minus the gap between them), not a constant
        # ratio picked independent of how many are showing.
        build_mixer(page, mixer_url)
        bar(page, 1).click()

        current = page.locator(".instrument-card").first.locator(
            ".diagram-stack"
        ).first
        row = page.locator('[data-preview-row="Piano"]')

        current_w = current.bounding_box()["width"]
        row_w = row.bounding_box()["width"]
        assert abs(row_w - current_w) < 4, (current_w, row_w)

    def test_one_preview_matches_the_main_diagram_full_size(
        self, page: Page, mixer_url: str
    ):
        # At 1 upcoming chord the single preview should be
        # the same size as the main diagram, not a smaller
        # copy - reviving the original full-size "Next chord"
        # idea deliberately, now without the opacity that made
        # it read as broken.
        build_mixer(page, mixer_url)
        bar(page, 1).click()
        page.get_by_role("radiogroup", name="Chords to preview").get_by_label(
            "1", exact=True
        ).check()

        current = page.locator(".instrument-card").first.locator(
            ".diagram-stack"
        ).first
        preview = page.locator('[data-preview-row="Piano"] .diagram-stack').first

        current_box = current.bounding_box()
        preview_box = preview.bounding_box()
        assert abs(current_box["width"] - preview_box["width"]) < 2
        assert abs(current_box["height"] - preview_box["height"]) < 2

    def test_scale_buttons_resize_one_instrument_only(
        self, page: Page, mixer_url: str
    ):
        # Discrete +/- buttons, not a range slider - easier to
        # hit from a couch or with a remote than dragging a
        # thumb precisely. 10% per click, so five clicks is a
        # clearly-visible 1.5x rather than a token nudge.
        build_mixer(page, mixer_url)
        bar(page, 1).click()

        piano = page.locator(".instrument-card").filter(has_text="Piano").locator("svg").first
        guitar = page.locator(".instrument-card").filter(has_text="Guitar").locator("svg").first
        piano_before = piano.bounding_box()["height"]
        guitar_before = guitar.bounding_box()["height"]

        enlarge_piano = page.get_by_label("Enlarge Piano")
        for _ in range(5):
            enlarge_piano.click()

        assert piano.bounding_box()["height"] > piano_before * 1.4
        assert abs(guitar.bounding_box()["height"] - guitar_before) < 1

    def test_scale_reset_button_returns_to_100_percent(
        self, page: Page, mixer_url: str
    ):
        build_mixer(page, mixer_url)
        bar(page, 1).click()

        piano = page.locator(".instrument-card").filter(has_text="Piano").locator("svg").first
        piano_before = piano.bounding_box()["height"]
        reset_button = page.get_by_label("Reset Piano size to 100%")

        # Not clickable at the default - there is nothing to
        # reset yet, and a live control that silently does
        # nothing when pressed is worse than one that is
        # visibly disabled until it means something.
        expect(reset_button).to_be_disabled()

        page.get_by_label("Enlarge Piano").click()
        page.get_by_label("Enlarge Piano").click()
        expect(reset_button).to_be_enabled()
        assert piano.bounding_box()["height"] > piano_before * 1.1

        reset_button.click()
        expect(reset_button).to_be_disabled()
        assert abs(piano.bounding_box()["height"] - piano_before) < 1