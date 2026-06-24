from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Label, ListItem, ListView, Static

MENU = [
    ("browse", "▶  Browse files", False),
    ("path", "⌘  Paste a path", False),
    ("online", "↗  Online link", True),
    ("settings", "⚙  Settings", True),
    ("quit", "✕  Quit", False),
]


class HomeScreen(Screen):
    BINDINGS = [("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Static("termflix", id="home-title")
        yield ListView(
            *[
                ListItem(
                    Label(
                        f"{'[dim]' if soon else ''}{label}{'[/dim]' if soon else ''}",
                        markup=True,
                    ),
                    id=key,
                    disabled=soon,
                )
                for key, label, soon in MENU
            ],
            id="home-menu",
        )
        yield Static("", id="home-footer")

    def on_mount(self) -> None:
        self.query_one("#home-footer", Static).update(
            "  ↑↓ navigate   enter select   q quit"
        )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        key = event.item.id

        if key == "quit":
            self.app.exit()

        elif key == "browse":
            from termflix.tui.screens.browse import BrowseScreen

            self.app.push_screen(BrowseScreen())

        elif key == "path":
            from termflix.tui.screens.path_input import PathInputScreen

            self.app.push_screen(PathInputScreen())

    def action_quit(self) -> None:
        self.app.exit()
