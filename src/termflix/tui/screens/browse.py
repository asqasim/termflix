from __future__ import annotations

import hashlib
from pathlib import Path

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Label, ListItem, ListView, Static

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}
VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv"}


def _scan(path: Path) -> list[tuple[str, Path, str]]:
    """Scan a folder and return list of (label, path, kind) sorted folders first."""
    items: list[tuple[str, Path, str]] = []

    try:
        entries = sorted(path.iterdir())
    except PermissionError:
        return []

    if path.parent != path:
        items.append(("..  (go up)", path.parent, "up"))

    for entry in entries:
        if entry.is_dir() and not entry.name.startswith("."):
            items.append((f"▸  {entry.name}", entry, "dir"))

    for entry in entries:
        if entry.is_file():
            ext = entry.suffix.lower()
            if ext in IMAGE_EXTS:
                items.append((f"   {entry.name}", entry, "image"))
            elif ext in VIDEO_EXTS:
                items.append((f"   {entry.name}", entry, "video"))

    return items


class BrowseScreen(Screen):
    BINDINGS = [
        ("escape", "go_back", "Back"),
    ]

    def __init__(self, start: Path | None = None) -> None:
        super().__init__()
        self.current = start or Path.cwd()
        self._items: list[tuple[str, Path, str]] = []

    def compose(self) -> ComposeResult:
        yield Static("", id="browse-path")
        yield Static("", id="browse-count")
        yield ListView(id="browse-list")
        yield Static("↑↓ navigate   enter open   esc back", id="browse-footer")

    async def on_mount(self) -> None:
        await self._load(self.current)

    async def _load(self, path: Path) -> None:
        self.current = path
        self._items = _scan(path)

        self.query_one("#browse-path", Static).update(f"  {self.current}")

        media_count = sum(1 for _, _, k in self._items if k in ("image", "video"))
        self.query_one("#browse-count", Static).update(
            f"  {media_count} media files" if media_count else "  no media files here"
        )

        prefix = "p" + hashlib.md5(str(path).encode()).hexdigest()[:7]

        new_items = []
        for i, (label, _, kind) in enumerate(self._items):
            if kind == "up":
                colour = "dim"
            elif kind == "dir":
                colour = "yellow"
            elif kind == "image":
                colour = "cyan"
            elif kind == "video":
                colour = "green"
            else:
                colour = "white"

            new_items.append(
                ListItem(
                    Label(f"[{colour}]{label}[/{colour}]", markup=True),
                    id=f"{prefix}-{i}",
                )
            )

        old = self.query_one("#browse-list", ListView)
        await old.remove()

        new_list = ListView(*new_items, id="browse-list")
        await self.mount(new_list, before=self.query_one("#browse-footer"))
        new_list.focus()

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item is None:
            return

        idx = int(event.item.id.rsplit("-", 1)[-1])
        _, path, kind = self._items[idx]

        if kind in ("dir", "up"):
            await self._load(path)

        elif kind == "image":
            all_images = [p for _, p, k in self._items if k == "image"]
            from termflix.tui.screens.image_viewer import ImageViewerScreen

            self.app.push_screen(ImageViewerScreen(path, all_images=all_images))

        elif kind == "video":
            from termflix.tui.screens.player import PlayerScreen

            self.app.push_screen(PlayerScreen(path))

    def action_go_back(self) -> None:
        self.app.pop_screen()
