from __future__ import annotations

import shutil
import sys
from pathlib import Path

# ── ANSI ───────────────────────────────────────────────────────────────────────

C_GREEN = "\033[92m"
C_WHITE = "\033[97m"
C_GREY = "\033[90m"
C_DIM = "\033[2m"
C_YELLOW = "\033[93m"
C_CYAN = "\033[96m"
C_RED = "\033[91m"
C_RESET = "\033[0m"
CLEAR = "\033[2J\033[H"
HIDE_CUR = "\033[?25l"
SHOW_CUR = "\033[?25h"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}
VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv"}


def _move(row: int, col: int) -> str:
    return f"\033[{row + 1};{col + 1}H"


def _get_key() -> str:
    """Read a single keypress and return it as a string."""
    if sys.platform == "win32":
        import msvcrt

        key = msvcrt.getch()
        if key == b"\xe0":  # arrow keys on windows send two bytes
            key2 = msvcrt.getch()
            return {b"H": "up", b"P": "down", b"K": "left", b"M": "right"}.get(key2, "")
        if key == b"\r":
            return "enter"
        if key == b"\x1b":
            return "esc"
        if key == b"\x08":
            return "backspace"
        return key.decode("utf-8", errors="ignore")
    else:
        import termios
        import tty

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                ch2 = sys.stdin.read(1)
                if ch2 == "[":
                    ch3 = sys.stdin.read(1)
                    return {"A": "up", "B": "down", "C": "right", "D": "left"}.get(
                        ch3, "esc"
                    )
                return "esc"
            if ch == "\r" or ch == "\n":
                return "enter"
            if ch == "\x7f":
                return "backspace"
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _cols() -> int:
    return shutil.get_terminal_size(fallback=(80, 24)).columns


def _lines() -> int:
    return shutil.get_terminal_size(fallback=(80, 24)).lines


def _center_col(text: str) -> int:
    return max(0, (_cols() - len(text)) // 2)


def _draw_menu(
    title: str,
    items: list[tuple[str, str]],  # (label, colour)
    selected: int,
    footer: str = "↑↓ navigate   enter select   q quit",
) -> None:
    """Draw a centered menu with the selected item highlighted."""
    cols = _cols()
    lines = _lines()
    buf: list[str] = []

    buf.append(CLEAR)

    # title
    title_row = lines // 2 - len(items) - 3
    buf.append(_move(title_row, _center_col(title)))
    buf.append(C_GREEN + title + C_RESET)

    # divider
    div = "─" * min(30, cols - 4)
    buf.append(_move(title_row + 1, _center_col(div)))
    buf.append(C_GREY + div + C_RESET)

    # menu items
    for i, (label, colour) in enumerate(items):
        row = title_row + 3 + i * 2
        col = _center_col(f"  {label}  ")

        if i == selected:
            buf.append(_move(row, col - 2))
            buf.append("\033[48;2;0;40;20m" + C_GREEN + "  " + label + "  " + C_RESET)
        else:
            buf.append(_move(row, col))
            buf.append(colour + C_DIM + label + C_RESET)

    # footer
    buf.append(_move(lines - 2, _center_col(footer)))
    buf.append(C_GREY + footer + C_RESET)

    sys.stdout.write("".join(buf))
    sys.stdout.flush()


def run_home() -> str | None:
    """Show the home menu. Returns the selected action key or None to quit."""
    items = [
        ("Browse files", C_WHITE),
        ("Paste a path", C_WHITE),
        ("Quit", C_GREY),
    ]
    keys = ["browse", "path", "quit"]
    sel = 0

    sys.stdout.write(HIDE_CUR)

    try:
        while True:
            _draw_menu("termflix", items, sel)
            key = _get_key()

            if key == "up":
                sel = (sel - 1) % len(items)
            elif key == "down":
                sel = (sel + 1) % len(items)
            elif key == "enter":
                return keys[sel]
            elif key in ("q", "esc"):
                return "quit"

    finally:
        sys.stdout.write(SHOW_CUR)


def run_browse(start: Path | None = None) -> Path | None:
    """Folder browser. Returns selected file path or None if user goes back."""
    current = start or Path.cwd()

    sys.stdout.write(HIDE_CUR)

    try:
        while True:
            # scan current folder
            entries: list[tuple[str, Path, str]] = []

            if current.parent != current:
                entries.append(("..  go up", current.parent, "up"))

            try:
                all_entries = sorted(current.iterdir())
            except PermissionError:
                all_entries = []

            for e in all_entries:
                if e.is_dir() and not e.name.startswith("."):
                    entries.append((f"▸  {e.name}", e, "dir"))

            for e in all_entries:
                if e.is_file():
                    ext = e.suffix.lower()
                    if ext in IMAGE_EXTS:
                        entries.append((f"   {e.name}", e, "image"))
                    elif ext in VIDEO_EXTS:
                        entries.append((f"   {e.name}", e, "video"))

            if not entries:
                entries.append(("  no media found", current, "empty"))

            # build display items
            display: list[tuple[str, str]] = []
            for label, _, kind in entries:
                if kind == "up":
                    colour = C_GREY
                elif kind == "dir":
                    colour = C_YELLOW
                elif kind == "image":
                    colour = C_CYAN
                elif kind == "video":
                    colour = C_GREEN
                else:
                    colour = C_DIM
                display.append((label, colour))

            cols = _cols()
            lines = _lines()
            buf: list[str] = []

            # pagination
            max_visible = lines - 8
            sel = 0
            scroll = 0

            while True:
                buf = [CLEAR]

                # header
                path_str = str(current)
                if len(path_str) > cols - 4:
                    path_str = "..." + path_str[-(cols - 7) :]
                buf.append(_move(0, 1) + C_GREEN + path_str + C_RESET)

                media_count = sum(1 for _, _, k in entries if k in ("image", "video"))
                count_str = (
                    f"{media_count} media files" if media_count else "no media files"
                )
                buf.append(_move(1, 1) + C_GREY + count_str + C_RESET)
                buf.append(_move(2, 1) + C_GREY + "─" * min(cols - 2, 60) + C_RESET)

                # visible entries
                visible = display[scroll : scroll + max_visible]
                for i, (label, colour) in enumerate(visible):
                    actual_i = scroll + i
                    row = 3 + i
                    if actual_i == sel:
                        buf.append(
                            _move(row, 1) + C_GREEN + "▶ " + C_WHITE + label + C_RESET
                        )
                    else:
                        buf.append(_move(row, 3) + colour + C_DIM + label + C_RESET)

                # footer
                footer = "↑↓ navigate   enter open   backspace go up   esc back"
                buf.append(
                    _move(lines - 2, _center_col(footer)) + C_GREY + footer + C_RESET
                )

                sys.stdout.write("".join(buf))
                sys.stdout.flush()

                key = _get_key()

                if key == "up":
                    sel = max(0, sel - 1)
                    if sel < scroll:
                        scroll = sel

                elif key == "down":
                    sel = min(len(entries) - 1, sel + 1)
                    if sel >= scroll + max_visible:
                        scroll = sel - max_visible + 1

                elif key == "enter":
                    _, path, kind = entries[sel]
                    if kind in ("dir", "up"):
                        current = path
                        break  # reload folder
                    elif kind in ("image", "video"):
                        from termflix.main import _play_file

                        sys.stdout.write(SHOW_CUR)
                        _play_file(path)
                        sys.stdout.write(HIDE_CUR)
                        # stay in current folder, don't return
                    # empty — do nothing

                elif key == "backspace":
                    if current.parent != current:
                        current = current.parent
                        break

                elif key in ("esc", "q"):
                    return None

    finally:
        sys.stdout.write(SHOW_CUR)


def run_path_input() -> Path | None:
    """Simple path input screen. Returns Path or None if cancelled."""
    cols = _cols()
    lines = _lines()
    value = ""
    error = ""

    sys.stdout.write(HIDE_CUR)

    try:
        while True:
            buf = [CLEAR]

            title = "open a file"
            subtitle = "enter a path to an image or video file"
            hint = "enter to open   esc to go back"

            title_row = lines // 2 - 4
            subtitle_row = title_row + 2
            input_row = subtitle_row + 2
            error_row = input_row + 2
            hint_row = error_row + 2

            buf.append(_move(title_row, _center_col(title)) + C_GREEN + title + C_RESET)
            buf.append(
                _move(subtitle_row, _center_col(subtitle)) + C_GREY + subtitle + C_RESET
            )

            # input box
            box_width = min(70, cols - 8)
            box_col = (cols - box_width) // 2
            box_str = value.ljust(box_width)[:box_width]
            buf.append(_move(input_row, box_col - 1) + C_GREY + "│" + C_RESET)
            buf.append(_move(input_row, box_col) + C_WHITE + box_str + C_RESET)
            buf.append(_move(input_row, box_col + box_width) + C_GREY + "│" + C_RESET)
            buf.append(
                _move(input_row - 1, box_col - 1)
                + C_GREY
                + "┌"
                + "─" * box_width
                + "┐"
                + C_RESET
            )
            buf.append(
                _move(input_row + 1, box_col - 1)
                + C_GREY
                + "└"
                + "─" * box_width
                + "┘"
                + C_RESET
            )

            if error:
                buf.append(_move(error_row, _center_col(error)) + C_RED + error + C_RESET)

            buf.append(_move(hint_row, _center_col(hint)) + C_GREY + hint + C_RESET)

            # cursor
            cursor_col = box_col + min(len(value), box_width - 1)
            buf.append(_move(input_row, cursor_col) + SHOW_CUR)

            sys.stdout.write("".join(buf))
            sys.stdout.flush()

            key = _get_key()

            if key == "esc":
                return None

            elif key == "enter":
                path = Path(value.strip())
                if not value.strip():
                    error = "please enter a path"
                elif not path.exists():
                    error = "path does not exist"
                elif not path.is_file():
                    error = "not a valid file"
                elif path.suffix.lower() not in IMAGE_EXTS | VIDEO_EXTS:
                    error = "unsupported file type"
                else:
                    return path

            elif key == "backspace":
                value = value[:-1]
                error = ""

            elif len(key) == 1:
                value += key
                error = ""

    finally:
        sys.stdout.write(HIDE_CUR)
