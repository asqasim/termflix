from __future__ import annotations

from pathlib import Path

from rich.text import Text
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static

from termflix.image import RenderMode, convert_image


class ImageViewerScreen(Screen):
    BINDINGS = [
        ("left", "prev_image", "Previous"),
        ("right", "next_image", "Next"),
        ("c", "toggle_color", "Color"),
        ("b", "toggle_mode", "Braille"),
        ("escape", "go_back", "Back"),
        ("q", "go_back", "Back"),
    ]

    def __init__(self, path: Path, *, all_images: list[Path]) -> None:
        super().__init__()
        self.all_images = all_images
        self.index = all_images.index(path)
        self.colored = False
        self.mode = RenderMode.ASCII

    @property
    def current_path(self) -> Path:
        return self.all_images[self.index]

    def compose(self) -> ComposeResult:
        yield Static("", id="image-display")
        yield Static("", id="image-status")

    def on_mount(self) -> None:
        self._render()

    def on_resize(self) -> None:
        self._render()

    def _render(self) -> None:
        try:
            result = convert_image(
                self.current_path,
                colored=self.colored,
                mode=self.mode,
            )
        except Exception as e:
            self.query_one("#image-display", Static).update(f"Error: {e}")
            return

        # convert raw ANSI string to Rich Text object
        text = Text.from_ansi(result)
        self.query_one("#image-display", Static).update(text)
        self.query_one("#image-status", Static).update(
            f"  {self.current_path.name}"
            f"  [{self.index + 1}/{len(self.all_images)}]"
            f"  mode: {self.mode}"
            f"  color: {'on' if self.colored else 'off'}"
            f"  ←→ navigate  c color  b braille  q back"
        )

    def action_prev_image(self) -> None:
        self.index = (self.index - 1) % len(self.all_images)
        self._render()

    def action_next_image(self) -> None:
        self.index = (self.index + 1) % len(self.all_images)
        self._render()

    def action_toggle_color(self) -> None:
        self.colored = not self.colored
        self._render()

    def action_toggle_mode(self) -> None:
        self.mode = (
            RenderMode.BRAILLE if self.mode == RenderMode.ASCII else RenderMode.ASCII
        )
        self._render()

    def action_go_back(self) -> None:
        self.app.pop_screen()
