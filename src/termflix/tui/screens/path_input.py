from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.screen import Screen
from textual.validation import ValidationResult, Validator
from textual.widgets import Input, Static


class PathValidator(Validator):
    """Validates that the input is an existing file path."""

    def validate(self, value: str) -> ValidationResult:
        path = Path(value.strip())
        if not value.strip():
            return self.success()
        if not path.exists():
            return self.failure("Path does not exist")
        if not path.is_file():
            return self.failure("Path is not a file")
        return self.success()


class PathInputScreen(Screen):
    BINDINGS = [
        ("escape", "go_back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Static("", id="path-spacer")
        yield Static("open a file", id="path-title")
        yield Static("enter a path to an image or video file", id="path-subtitle")
        yield Input(
            placeholder="C:\\Videos\\movie.mp4  or  /home/user/video.mp4",
            validators=[PathValidator()],
            id="path-input",
        )
        yield Static("", id="path-error")
        yield Static("enter to open   esc to go back", id="path-hint")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()

        if not value:
            return

        path = Path(value)

        if not path.exists():
            self.query_one("#path-error", Static).update("[red]path does not exist[/red]")
            return

        if not path.is_file():
            self.query_one("#path-error", Static).update("[red]not a valid file[/red]")
            return

        # clear error
        self.query_one("#path-error", Static).update("")

        # route to correct screen based on file type
        suffix = path.suffix.lower()
        image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}
        video_exts = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv"}

        if suffix in image_exts:
            from termflix.tui.screens.image_viewer import ImageViewerScreen

            self.app.switch_screen(ImageViewerScreen(path, all_images=[path]))

        elif suffix in video_exts:
            from termflix.tui.screens.player import PlayerScreen

            self.app.switch_screen(PlayerScreen(path))

        else:
            self.query_one("#path-error", Static).update(
                "[red]unsupported file type[/red]"
            )

    def on_input_changed(self, event: Input.Changed) -> None:
        self.query_one("#path-error", Static).update("")

    def action_go_back(self) -> None:
        self.app.pop_screen()
