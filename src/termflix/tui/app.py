from __future__ import annotations

from textual.app import App


class TermflixApp(App):
    CSS_PATH = "styles/termflix.tcss"
    TITLE = "termflix"

    def on_mount(self) -> None:
        from termflix.tui.screens.home import HomeScreen

        self.push_screen(HomeScreen())
