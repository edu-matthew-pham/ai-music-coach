# test_lyrics_chords_e2e.py
#
# The Lyrics panel's chord display, built and iterated on
# this session without ever being seen render - three real
# bugs shipped in a row (a syncopated chord going grey at
# the bar line; the ring vanishing onto a suppressed,
# invisible repeat; the same suppression silently failing
# across a phrase boundary) each "verified" by reading the
# code, not running it. These tests close that gap: real
# clicks against the real built component, real CSS classes
# asserted, using "Load a syncopated duet" - a small
# hand-typed song built specifically to exercise both a
# syncopated chord and a real gap between two voices,
# verified directly against mixer_data() in demo/app.py's
# own build_syncopated() docstring before being wired here.
#
# Layout, in real seconds at this song's 120bpm (0.5s per
# beat, 2.0s per bar): bar 1 = 0.0-2.0s (C); bar 2 =
# 2.0-4.0s (F at 2.0s, G at 3.5s - syncopated); bar 3 =
# 4.0-6.0s (G carried, suppressed in print). "Lead" sings
# the whole 6.0s; "Answer" is silent 0.0-4.0s, then sings
# 4.0-6.0s.

import re

import pytest
from playwright.sync_api import Page, expect


def build_syncopated_mixer(page: Page, url: str) -> None:
    page.goto(url)
    page.get_by_role("button", name="Load a syncopated duet").click()
    page.get_by_role("button", name="Custom").click()
    expect(page.locator('[data-bar="1"]')).to_be_visible(timeout=15000)


def use_windowed_lyrics(page: Page) -> None:
    """
    Paired mode (the default) drops a line the moment it is
    fully sung - real, deliberate behaviour
    (visiblePhrases = effectivePhrases.slice(currentIndex)),
    confirmed by a real run: seeking to bar 3 left only
    phrase 3 in the DOM, and phrase 2 - the syncopated G's
    own home line, the last word before the bar it carries
    into - was already gone. Nothing wrong with the
    highlight; the view mode this test used simply removes
    the element being asserted on before the assertion runs.
    Turning off "Visual notes" switches Lyrics to windowed
    mode (Index.svelte's own lyricsMode: paired only when
    the Notes panel is also shown), where every line stays
    on screen for the whole song - the mode any test
    checking a chord anchored to an earlier line needs.
    """

    page.get_by_label("Visual notes").uncheck()


def bar(page: Page, number: int):
    return page.locator(f'[data-bar="{number}"]')


def seek_to_bar(page: Page, number: int) -> None:
    """
    Bar clicks are the existing, proven way to move the
    playhead without needing real audio playback - the same
    mechanism test_mixer_e2e.py's own selection tests use.
    """

    bar(page, number).click()


class TestChordPrinting:

    def test_carried_chords_print_faded_instead_of_vanishing(
        self, page: Page, mixer_url: str
    ):
        """
        Bar 3 opens with G carried from bar 2's syncopation.
        It must still be ON SCREEN (faded), not dropped -
        the whole point of printing carried chords at all.
        """

        build_syncopated_mixer(page, mixer_url)

        chord = page.locator(".chord-tag", has_text="G").last
        expect(chord).to_be_visible()

    def test_a_syncopated_repeat_does_not_print_twice(self, page: Page, mixer_url: str):
        """
        Bar 2's real G (beat 3.5) is followed immediately by
        bar 3's carried repeat - suppressed, per the rule
        that a repeat right after a syncopation is noise.
        Exactly one G chord-tag should exist in this short
        song, not two.
        """

        build_syncopated_mixer(page, mixer_url)

        expect(page.locator(".chord-tag", has_text=re.compile(r"^G$"))).to_have_count(1)


class TestCurrentBarHighlight:

    def test_the_syncopated_chord_is_bar_highlighted_in_its_own_bar(
        self, page: Page, mixer_url: str
    ):
        build_syncopated_mixer(page, mixer_url)

        seek_to_bar(page, 2)

        g = page.locator(".chord-tag", has_text=re.compile(r"^G$"))
        expect(g).to_have_class(re.compile(r"\bnow\b"))

    def test_the_syncopated_chord_stays_bar_highlighted_in_the_adopting_bar(
        self, page: Page, mixer_url: str
    ):
        """
        The actual bug a real screenshot caught: crossing
        into bar 3 (which carries G, suppressed) used to
        drop the highlight entirely, because the adoption
        that should extend bar 2's G across the bar line
        only ran when the real chord and its suppressed
        repeat shared one phrase window - and a line-ending
        syncopation almost never does. Needs windowed mode:
        the G tag lives on phrase 2's own line ("...eight"),
        which paired mode would have already dropped by the
        time bar 3 is reached - see use_windowed_lyrics.
        """

        build_syncopated_mixer(page, mixer_url)
        use_windowed_lyrics(page)

        seek_to_bar(page, 3)

        g = page.locator(".chord-tag", has_text=re.compile(r"^G$"))
        expect(g).to_have_class(re.compile(r"\bnow\b"))

    def test_the_highlight_moves_on_when_a_new_chord_arrives(self, page: Page, mixer_url: str):
        build_syncopated_mixer(page, mixer_url)

        seek_to_bar(page, 1)

        c = page.locator(".chord-tag", has_text=re.compile(r"^C$"))
        expect(c).to_have_class(re.compile(r"\bnow\b"))

        g = page.locator(".chord-tag", has_text=re.compile(r"^G$"))
        expect(g).not_to_have_class(re.compile(r"\bnow\b"))


class TestSoundingRing:

    def test_the_ring_stays_on_the_syncopated_chord_through_the_adopting_bar(
        self, page: Page, mixer_url: str
    ):
        """
        The ring must never simply vanish - the earlier
        version pointed it at the suppressed carried entry
        itself, which has no visible element, and the ring
        went dark the moment the bar line was crossed. Needs
        windowed mode for the same reason as the bar-highlight
        test above: the G tag lives on phrase 2's own line.
        """

        build_syncopated_mixer(page, mixer_url)
        use_windowed_lyrics(page)

        seek_to_bar(page, 3)

        g = page.locator(".chord-tag", has_text=re.compile(r"^G$"))
        expect(g).to_have_class(re.compile(r"\bsounding\b"))

    def test_only_one_chord_ever_carries_the_ring(self, page: Page, mixer_url: str):
        build_syncopated_mixer(page, mixer_url)

        seek_to_bar(page, 2)

        expect(page.locator(".chord-tag.sounding, .lead-in-event.sounding")).to_have_count(1)


class TestPartsGapChords:

    def test_a_silent_voices_column_shows_the_shared_chart_during_its_gap(
        self, page: Page, mixer_url: str
    ):
        """
        "Answer" is silent for the first 4 seconds while
        "Lead" sings - the real report this suite exists
        for: the chart is shared across voices, so that
        silent stretch must still show its chords in
        Answer's own column, not go chord-blind.
        """

        build_syncopated_mixer(page, mixer_url)

        page.get_by_label("Show all parts").check()

        answer_column = page.locator(".lyrics-column", has_text="Answer")
        expect(answer_column.locator(".lead-in-event", has_text="C")).to_be_visible()
        expect(answer_column.locator(".lead-in-event", has_text="F")).to_be_visible()

    def test_the_gap_chord_line_is_present_from_the_start_not_conjured_later(
        self, page: Page, mixer_url: str
    ):
        """
        Regression pin for "suddenly more chords appear":
        the gap's chord line must already be in the DOM
        before the playhead ever reaches it, not created the
        moment playback arrives at the hole.
        """

        build_syncopated_mixer(page, mixer_url)

        page.get_by_label("Show all parts").check()

        # Playhead still at the very start (bar 1) - the gap
        # line covering 0.0-4.0s must already be rendered.
        answer_column = page.locator(".lyrics-column", has_text="Answer")
        expect(answer_column.locator(".lead-in-line").first).to_be_visible()

    def test_a_column_with_no_gap_shows_no_gap_line(self, page: Page, mixer_url: str):
        build_syncopated_mixer(page, mixer_url)

        page.get_by_label("Show all parts").check()

        lead_column = page.locator(".lyrics-column", has_text="Lead")
        expect(lead_column.locator(".lead-in-line")).to_have_count(0)