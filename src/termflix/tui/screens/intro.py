from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static

INTRO_ART = """\
 _                      _    __ _ _      
| |_ ___ _ __ _ __ ___ | |  / _| (_)_  __
| __/ _ \\ '__| '_ ` _ \\| | | |_| | \\ \\/ /
| ||  __/ |  | | | | | | | |  _| | |>  < 
 \\__\\___|_|  |_| |_| |_|_| |_| |_|_/_/\\_\\
"""

TAGLINE = "your terminal. your cinema."


class IntroScreen(Screen):
    """Animated splash screen — auto-advances to home after a short delay."""

    def compose(self) -> ComposeResult:
        yield Static(INTRO_ART, id="intro-art")
        yield Static(TAGLINE, id="intro-tagline")
        yield Static("press any key to continue", id="intro-hint")

    def on_mount(self) -> None:
        self.set_timer(3.0, self._advance)

    def on_key(self) -> None:
        self._advance()

    def _advance(self) -> None:
        from termflix.tui.screens.home import HomeScreen

        self.app.switch_screen(HomeScreen())
