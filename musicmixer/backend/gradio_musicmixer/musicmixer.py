from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any

from gradio.components.base import Component
from gradio.events import Events
from gradio.i18n import I18nData

if TYPE_CHECKING:
    from gradio.components import Timer


class MusicMixer(Component):
    """
    A live mixer: several sound layers played together in
    the browser, a chord strip that follows them, and a
    loop region chosen by clicking it.

    Unlike gr.HTML, the value travels both ways. Python
    sets layers and timeline; the browser sets loop_start
    and loop_end whenever a person selects a stretch to
    listen to or sing against - which is the entire reason
    this exists rather than an HTML block.
    """

    EVENTS = [
        Events.change,
        Events.input,
    ]

    def __init__(
        self,
        value: dict | Callable | None = None,
        *,
        label: str | I18nData | None = None,
        every: "Timer | float | None" = None,
        inputs: Component | Sequence[Component] | set[Component] | None = None,
        show_label: bool | None = None,
        scale: int | None = None,
        min_width: int = 160,
        visible: bool = True,
        elem_id: str | None = None,
        elem_classes: list[str] | str | None = None,
        render: bool = True,
        key: int | str | tuple[int | str, ...] | None = None,
        preserved_by_key: list[str] | str | None = "value",
    ):
        """
        Parameters:
            value: a dict with `layers`, `timeline`,
                `loop_start` and `loop_end`. If a function is
                provided, it is called each time the app
                loads to set the initial value.
            label: shown above the component if show_label
                is True.
            every: recalculates `value` on a timer if `value`
                is a function.
            inputs: components `value` is recalculated from,
                if `value` is a function.
            show_label: whether to display the label.
            scale: relative width compared to siblings in a
                Row.
            min_width: minimum pixel width before wrapping.
            visible: whether the component is shown.
            elem_id: HTML id, for CSS targeting.
            elem_classes: HTML classes, for CSS targeting.
            render: if False, do not render in the Blocks
                context yet.
            key: identifies this component as the same one
                across a gr.render() re-render.
            preserved_by_key: constructor parameters kept
                across a re-render with the same key.
        """
        super().__init__(
            label=label,
            every=every,
            inputs=inputs,
            show_label=show_label,
            scale=scale,
            min_width=min_width,
            visible=visible,
            elem_id=elem_id,
            elem_classes=elem_classes,
            value=value,
            render=render,
            key=key,
            preserved_by_key=preserved_by_key,
        )

    def preprocess(self, payload: dict | None) -> dict | None:
        """
        Parameters:
            payload: the value as the browser last reported
                it - layers and timeline as they were sent,
                loop_start / loop_end as a person set them by
                clicking the strip.
        Returns:
            The same dict, unchanged. A handler reading
            loop_start / loop_end is how it finds out what
            stretch was selected.
        """
        return payload

    def postprocess(self, value: dict | None) -> dict | None:
        """
        Parameters:
            value: a dict built by mixer_data() - layers and
                timeline to send down. bpm is the tempo the
                mixer was built at, carried alongside the
                loop so a Python handler reading loop_start /
                loop_end back later knows what tempo those
                seconds were measured against, even if the
                BPM box has since changed. loop_start /
                loop_end are normally left unset here, so a
                freshly built mixer opens with nothing
                looped. parts names the tunes in a several-
                tune song (empty for an ordinary one) and
                part is whichever is being sung; the browser
                sends part back when a person picks another.
        Returns:
            The dict sent to the browser.
        """
        if value is None:
            return None

        return {
            "layers": value.get("layers", []),
            "timeline": value.get("timeline", []),
            "notes": value.get("notes", []),
            "phrases": value.get("phrases", []),
            "phrases_by_part": value.get("phrases_by_part", {}),
            "diagrams": value.get("diagrams", {}),
            "bpm": value.get("bpm"),
            "parts": value.get("parts", []),
            "part": value.get("part"),
            "loop_start": value.get("loop_start"),
            "loop_end": value.get("loop_end"),
        }

    def api_info(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "layers": {
                    "type": "array",
                    "items": {"type": "object"},
                },
                "timeline": {
                    "type": "array",
                    "items": {"type": "object"},
                },
                "notes": {
                    "type": "array",
                    "items": {"type": "object"},
                },
                "phrases": {
                    "type": "array",
                    "items": {"type": "object"},
                },
                "phrases_by_part": {
                    "type": "object",
                },
                "diagrams": {
                    "type": "object",
                },
                "bpm": {
                    "anyOf": [{"type": "number"}, {"type": "null"}]
                },
                "parts": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "part": {
                    "anyOf": [{"type": "string"}, {"type": "null"}]
                },
                "loop_start": {
                    "anyOf": [{"type": "number"}, {"type": "null"}]
                },
                "loop_end": {
                    "anyOf": [{"type": "number"}, {"type": "null"}]
                },
            },
        }

    def example_payload(self) -> Any:
        return {"layers": [], "timeline": [], "notes": [], "phrases": [], "phrases_by_part": {}, "diagrams": {}, "bpm": None, "parts": [], "part": None, "loop_start": None, "loop_end": None}

    def example_value(self) -> Any:
        return {"layers": [], "timeline": [], "notes": [], "phrases": [], "phrases_by_part": {}, "diagrams": {}, "bpm": None, "parts": [], "part": None, "loop_start": None, "loop_end": None}