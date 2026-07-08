from __future__ import annotations

import sys
from pathlib import Path

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static

from termflix.compat import get_terminal_size
from termflix.image import RenderMode, convert_image

HIDE_CUR = "\033[?25l"
SHOW_CUR = "\033[?25h"
CLEAR = "\033[2J\033[H"


def _render_to_terminal(
    path: Path,
    *,
    colored: bool = False,
    mode: str = RenderMode.ASCII,
) -> None:
    """Render an image directly to the terminal bypassing Textual."""
    result = convert_image(path, colored=colored, mode=mode)
    cols, lines = get_terminal_size()

    sys.stdout.write(CLEAR + HIDE_CUR)
    sys.stdout.write(result)
    sys.stdout.flush()


class ImageViewerScreen(Screen):
    """Fullscreen image viewer — renders directly to terminal."""

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
        yield Static("", id="image-status")

    def on_mount(self) -> None:
        self._render()

    def on_resize(self) -> None:
        self._render()

    def _render(self) -> None:
        try:
            _render_to_terminal(
                self.current_path,
                colored=self.colored,
                mode=self.mode,
            )
        except Exception as e:
            sys.stdout.write(f"\033[H\033[2JError: {e}\n")
            sys.stdout.flush()
            return

        # status bar at bottom
        cols, lines = get_terminal_size()
        status = (
            f"  {self.current_path.name}"
            f"  [{self.index + 1}/{len(self.all_images)}]"
            f"  mode:{self.mode}"
            f"  color:{'on' if self.colored else 'off'}"
            f"  ←→ navigate  c color  b braille  q back"
        )
        sys.stdout.write(f"\033[{lines};0H\033[K{status}")
        sys.stdout.write(SHOW_CUR)
        sys.stdout.flush()

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
        sys.stdout.write(CLEAR + SHOW_CUR)
        sys.stdout.flush()
        self.app.pop_screen()
