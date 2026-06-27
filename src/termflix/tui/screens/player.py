from __future__ import annotations

from pathlib import Path

from textual import work
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static

from termflix.image import RenderMode
from termflix.video import VideoPlayer


class PlayerScreen(Screen):
    BINDINGS = [
        ("q", "go_back", "Quit"),
        ("escape", "go_back", "Back"),
    ]

    def __init__(
        self,
        path: Path,
        *,
        colored: bool = True,
        mode: str = RenderMode.ASCII,
    ) -> None:
        super().__init__()
        self.path = path
        self.colored = colored
        self.mode = mode
        self._player: VideoPlayer | None = None

    def compose(self) -> ComposeResult:
        yield Static(
            f"  {self.path.name}  —  q to quit",
            id="player-title",
        )

    def on_mount(self) -> None:
        self._start_playback()

    @work(thread=True)
    def _start_playback(self) -> None:
        self._player = VideoPlayer(
            self.path,
            colored=self.colored,
            mode=self.mode,
        )
        self._player.play()

    def action_go_back(self) -> None:
        if self._player is not None:
            self._player._stop_event.set()
        self.app.pop_screen()
