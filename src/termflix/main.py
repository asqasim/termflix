from __future__ import annotations

import sys
from pathlib import Path

from termflix.compat import get_terminal_size
from termflix.image import RenderMode, convert_image
from termflix.tui.intro_anim import run_intro
from termflix.tui.menu import (
    CLEAR_SCREEN,
    CURSOR_HOME,
    run_browse,
    run_home,
    run_path_input,
)
from termflix.video import VideoPlayer

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}
VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv"}

SHOW_CUR = "\033[?25h"
HIDE_CUR = "\033[?25l"


def _play_file(path: Path) -> None:
    ext = path.suffix.lower()
    if ext in IMAGE_EXTS:
        _view_image(path)
    elif ext in VIDEO_EXTS:
        _play_video(path)


def _view_image(path: Path, all_images: list[Path] | None = None) -> None:
    from termflix.tui.menu import _get_key

    images = all_images or [path]
    index = images.index(path) if path in images else 0
    colored = True
    mode = RenderMode.ASCII
    last_size = (0, 0)
    first = True

    sys.stdout.write(HIDE_CUR)

    try:
        while True:
            current = images[index]
            cols, lines = get_terminal_size()

            if (cols, lines) != last_size:
                last_size = (cols, lines)
                result = convert_image(current, colored=colored, mode=mode)

                sys.stdout.write(CLEAR_SCREEN if first else CURSOR_HOME)
                first = False
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
                last_size = (0, 0)
            elif key == "left":
                index = (index - 1) % len(images)
                last_size = (0, 0)
            elif key == "c":
                colored = not colored
                last_size = (0, 0)
            elif key == "b":
                mode = (
                    RenderMode.BRAILLE if mode == RenderMode.ASCII else RenderMode.ASCII
                )
                last_size = (0, 0)
            elif key in ("q", "esc"):
                break

    finally:
        sys.stdout.write(SHOW_CUR)


def _play_video(path: Path) -> None:
    player = VideoPlayer(path, colored=True, mode=RenderMode.ASCII)
    player.play()


def main() -> None:
    run_intro()

    while True:
        action = run_home()

        if action == "quit" or action is None:
            sys.stdout.write(CLEAR_SCREEN + SHOW_CUR)
            break

        elif action == "browse":
            run_browse()

        elif action == "path":
            path = run_path_input()
            if path:
                _play_file(path)


if __name__ == "__main__":
    main()
