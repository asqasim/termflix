from __future__ import annotations

from pathlib import Path

from termflix.compat import get_terminal_size
from termflix.image import RenderMode, convert_image
from termflix.tui.intro_anim import run_intro
from termflix.tui.menu import run_browse, run_home, run_path_input
from termflix.video import VideoPlayer

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}
VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv"}

CLEAR = "\033[2J\033[H"
SHOW_CUR = "\033[?25h"


def _play_file(path: Path) -> None:
    """Route a file to the correct player based on extension."""
    ext = path.suffix.lower()

    if ext in IMAGE_EXTS:
        _view_image(path)
    elif ext in VIDEO_EXTS:
        _play_video(path)


def _view_image(path: Path, all_images: list[Path] | None = None) -> None:
    import sys

    from termflix.tui.menu import _get_key

    images = all_images or [path]
    index = images.index(path) if path in images else 0
    colored = True
    mode = RenderMode.ASCII
    last_size = (0, 0)

    while True:
        current = images[index]
        cols, lines = get_terminal_size()

        # re-render if size changed or new image
        if (cols, lines) != last_size:
            last_size = (cols, lines)
            result = convert_image(current, colored=colored, mode=mode)
            sys.stdout.write(CLEAR)
            sys.stdout.write(result)

            status = (
                f"  {current.name}"
                f"  [{index + 1}/{len(images)}]"
                f"  c color  b braille"
                f"  ←→ navigate  q back"
            )
            sys.stdout.write(f"\033[{lines};0H\033[K\033[90m{status}\033[0m")
            sys.stdout.flush()

        key = _get_key()

        if key == "right":
            index = (index + 1) % len(images)
            last_size = (0, 0)  # force re-render
        elif key == "left":
            index = (index - 1) % len(images)
            last_size = (0, 0)
        elif key == "c":
            colored = not colored
            last_size = (0, 0)
        elif key == "b":
            mode = RenderMode.BRAILLE if mode == RenderMode.ASCII else RenderMode.ASCII
            last_size = (0, 0)
        elif key in ("q", "esc"):
            break


def _play_video(path: Path) -> None:
    """Play a video in the terminal."""
    player = VideoPlayer(path, colored=True, mode=RenderMode.ASCII)
    player.play()


def main() -> None:
    import sys

    run_intro()

    while True:
        action = run_home()

        if action == "quit" or action is None:
            sys.stdout.write(CLEAR + SHOW_CUR)
            break

        elif action == "browse":
            path = run_browse()
            if path:
                _play_file(path)

        elif action == "path":
            path = run_path_input()
            if path:
                _play_file(path)


if __name__ == "__main__":
    main()
