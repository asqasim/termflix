from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Label, ListItem, ListView, Static

MENU_ITEMS = [
    ("play", "▶  Play", "play a file from your machine"),
    ("browse", "◉  Browse", "browse bundled movies"),
    ("settings", "⚙  Settings", "render mode, color, quality"),
    ("quit", "✕  Quit", "exit termflix"),
]


class HomeScreen(Screen):
    """Main menu."""

    def compose(self) -> ComposeResult:
        yield Static("termflix", id="home-title")
        yield ListView(
            *[ListItem(Label(label), id=key) for key, label, _ in MENU_ITEMS],
            id="home-menu",
        )
        yield Static("", id="home-hint")

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item is None:
            return
        key = event.item.id
        hint = next((desc for k, _, desc in MENU_ITEMS if k == key), "")
        self.query_one("#home-hint", Static).update(hint)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        key = event.item.id

        if key == "quit":
            self.app.exit()

        elif key == "play":
            from termflix.tui.screens.browse import BrowseScreen

            self.app.push_screen(BrowseScreen(mode="file"))

        elif key == "browse":
            from termflix.tui.screens.browse import BrowseScreen

            self.app.push_screen(BrowseScreen(mode="bundled"))

        elif key == "settings":
            from termflix.tui.screens.settings import SettingsScreen

            self.app.push_screen(SettingsScreen())
