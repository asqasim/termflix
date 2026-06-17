from __future__ import annotations

from textual.app import App

from termflix.tui.screens.intro import IntroScreen


class TermflixApp(App):
    """Root application — owns the screen stack."""

    CSS_PATH = "styles/termflix.tcss"
    TITLE = "termflix"

    def on_mount(self) -> None:
        self.push_screen(IntroScreen())
