from __future__ import annotations

import random
import shutil
import sys
import threading
import time

# ── ANSI ───────────────────────────────────────────────────────────────────────

C_WHITE = "\033[97m"
C_YELLOW = "\033[93m"
C_ORANGE = "\033[33m"
C_GREY = "\033[90m"
C_DIM = "\033[2m"
C_RESET = "\033[0m"
CLEAR = "\033[2J\033[H"
HIDE_CUR = "\033[?25l"
SHOW_CUR = "\033[?25h"


def _move(row: int, col: int) -> str:
    return f"\033[{row + 1};{col + 1}H"


def _centered_col(text: str, term_cols: int) -> int:
    return max(0, (term_cols - len(text)) // 2)


# ── Logo ───────────────────────────────────────────────────────────────────────

LOGO_LINES = [
    r" _                      __ _ _      ",
    r"| |_ ___ _ __ _ __ _  / _| (_)_  __",
    r"| __/ _ \ '__| '_ ` _ \| |_| | \ \/ /",
    r"| ||  __/ |  | | | | | |  _| | |>  < ",
    r" \__\___|_|  |_| |_| |_|_| |_|_/_/\_\ ",
]

TAGLINE = "your terminal. your cinema."
HINT = "press any key to continue"

LOGO_COLOURS = [C_YELLOW, C_ORANGE, C_WHITE, C_ORANGE, C_YELLOW]

# ── TV definition ──────────────────────────────────────────────────────────────
# Edit these 4 values to resize the TV.
# All static and TV drawing auto-adjusts.

TV_WIDTH = 38  # inner content width  (must be even)
TV_HEIGHT = 13  # inner content height

STATIC_CHARS = list(" . · . . · . · ")


def _build_tv(
    inner_row: int,  # top-left row of TV inner screen
    inner_col: int,  # top-left col of TV inner screen
    tick: int,
    shutdown_ratio: float = 0.0,  # 0.0 = normal, 1.0 = fully off
) -> list[str]:
    """Return a list of ANSI strings that draw the full TV for one frame.

    Args:
        inner_row: Top row of the inner screen area.
        inner_col: Left col of the inner screen area.
        tick: Current frame tick for static animation.
        shutdown_ratio: 0.0 = normal static, 1.0 = screen collapsed to line.
    """
    buf: list[str] = []
    w = TV_WIDTH
    h = TV_HEIGHT

    # ── outer border coords ───────────────────────────────────────────────────
    border_row = inner_row - 1
    border_col = inner_col - 2

    outer_w = w + 4  # 2 padding each side
    outer_h = h + 2  # 1 padding top and bottom

    # ── antenna ───────────────────────────────────────────────────────────────
    antenna_center = border_col + outer_w // 2
    buf.append(
        _move(border_row - 3, antenna_center - 4) + C_GREY + r"  /\       /\  " + C_RESET
    )
    buf.append(
        _move(border_row - 2, antenna_center - 4) + C_GREY + r" /  \     /  \ " + C_RESET
    )
    buf.append(
        _move(border_row - 1, antenna_center - 4) + C_GREY + r"/    \___/    \\" + C_RESET
    )

    # ── TV border ─────────────────────────────────────────────────────────────
    buf.append(
        _move(border_row, border_col) + C_GREY + "┌" + "─" * outer_w + "┐" + C_RESET
    )
    for r in range(outer_h):
        buf.append(_move(border_row + 1 + r, border_col) + C_GREY + "│" + C_RESET)
        buf.append(
            _move(border_row + 1 + r, border_col + outer_w + 1) + C_GREY + "│" + C_RESET
        )
    buf.append(
        _move(border_row + outer_h + 1, border_col)
        + C_GREY
        + "└"
        + "─" * outer_w
        + "┘"
        + C_RESET
    )

    # ── TV stand ──────────────────────────────────────────────────────────────
    stand_row = border_row + outer_h + 2
    stand_col = border_col + outer_w // 2 - 6
    buf.append(_move(stand_row, stand_col) + C_GREY + "   ████████████   " + C_RESET)
    buf.append(_move(stand_row + 1, stand_col) + C_GREY + "      ██   ██      " + C_RESET)

    # ── static screen content ─────────────────────────────────────────────────
    if shutdown_ratio == 0.0:
        # normal static — full screen
        for r in range(h):
            row_chars = []
            for c in range(w):
                ch = random.choice(STATIC_CHARS)
                colour = C_WHITE if random.random() > 0.5 else C_GREY
                row_chars.append(colour + ch + C_RESET)
            buf.append(_move(inner_row + r, inner_col) + "".join(row_chars))

    else:
        # shutdown animation — static compresses to a horizontal line
        # ratio 0→1: visible rows shrink from full height to 1
        visible_rows = max(1, int(h * (1.0 - shutdown_ratio)))
        center_r = inner_row + h // 2

        # clear screen area first
        for r in range(h):
            buf.append(_move(inner_row + r, inner_col) + " " * w)

        # draw compressed static rows around center
        half = visible_rows // 2
        for r in range(-half, half + 1):
            actual_row = center_r + r
            if inner_row <= actual_row < inner_row + h:
                row_chars = []
                brightness = 1.0 - abs(r) / max(half, 1)
                for c in range(w):
                    ch = random.choice(STATIC_CHARS)
                    if brightness > 0.7:
                        colour = C_WHITE
                    elif brightness > 0.3:
                        colour = C_GREY
                    else:
                        colour = C_DIM
                    row_chars.append(colour + ch + C_RESET)
                buf.append(_move(actual_row, inner_col) + "".join(row_chars))

    return buf


def _tv_off_flash(
    inner_row: int,
    inner_col: int,
    term_cols: int,
) -> None:
    """The final TV shutoff — static compresses to line then bright flash then black."""
    w = TV_WIDTH
    h = TV_HEIGHT
    center_r = inner_row + h // 2

    # phase 1 — compress static to a line over 0.6 seconds
    compress_dur = 0.6
    compress_fps = 24
    compress_start = time.perf_counter()

    while True:
        elapsed = time.perf_counter() - compress_start
        ratio = min(elapsed / compress_dur, 1.0)
        buf = _build_tv(inner_row, inner_col, tick=0, shutdown_ratio=ratio)
        sys.stdout.write("".join(buf))
        sys.stdout.flush()
        time.sleep(1 / compress_fps)
        if ratio >= 1.0:
            break

    # phase 2 — bright horizontal line flash
    for intensity in [C_WHITE, C_WHITE, C_YELLOW, C_WHITE, C_GREY, C_DIM, ""]:
        buf = []
        for r in range(h):
            buf.append(_move(inner_row + r, inner_col) + " " * w)
        if intensity:
            line = "─" * w
            buf.append(_move(center_r, inner_col) + intensity + line + C_RESET)
        sys.stdout.write("".join(buf))
        sys.stdout.flush()
        time.sleep(0.06)

    # phase 3 — single bright pixel star in center
    star_col = inner_col + w // 2
    for ch, colour, delay in [
        ("✦", C_WHITE, 0.08),
        ("·", C_WHITE, 0.06),
        ("·", C_GREY, 0.05),
        (" ", "", 0.04),
    ]:
        buf = []
        for r in range(h):
            buf.append(_move(inner_row + r, inner_col) + " " * w)
        if colour:
            buf.append(_move(center_r, star_col) + colour + ch + C_RESET)
        sys.stdout.write("".join(buf))
        sys.stdout.flush()
        time.sleep(delay)

    # phase 4 — all black
    buf = []
    for r in range(h):
        buf.append(_move(inner_row + r, inner_col) + " " * w)
    sys.stdout.write("".join(buf))
    sys.stdout.flush()
    time.sleep(0.3)


def run_intro() -> None:
    """Run the termflix TV static intro animation."""
    term_cols, term_lines = shutil.get_terminal_size(fallback=(80, 24))

    # ── layout — logo left, TV right ──────────────────────────────────────────
    total_width = len(LOGO_LINES[2]) + 6 + TV_WIDTH + 4
    left_margin = max(0, (term_cols - total_width) // 2)

    logo_col = left_margin
    logo_width = max(len(line) for line in LOGO_LINES)

    # TV inner screen top-left
    tv_inner_col = logo_col + logo_width + 6
    tv_inner_row = max(3, (term_lines - TV_HEIGHT) // 2)

    # logo vertically centered alongside TV
    logo_row = tv_inner_row + (TV_HEIGHT - len(LOGO_LINES)) // 2

    # tagline_row = tv_inner_row + TV_HEIGHT + 4
    # # hint_row = tagline_row + 2

    # ── key listener ──────────────────────────────────────────────────────────
    skipped = threading.Event()

    def _listen() -> None:
        try:
            if sys.platform == "win32":
                import msvcrt

                msvcrt.getch()
            else:
                import termios
                import tty

                fd = sys.stdin.fileno()
                old = termios.tcgetattr(fd)
                try:
                    tty.setraw(fd)
                    sys.stdin.read(1)
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old)
        except Exception:
            pass
        skipped.set()

    key_thread = threading.Thread(target=_listen, daemon=True)
    key_thread.start()

    # ── animation ─────────────────────────────────────────────────────────────
    fps = 12
    frame_time = 1.0 / fps
    total_dur = 12.0
    start = time.perf_counter()
    tick = 0

    sys.stdout.write(CLEAR + HIDE_CUR)
    sys.stdout.flush()

    try:
        while True:
            if skipped.is_set():
                break

            elapsed = time.perf_counter() - start
            if elapsed > total_dur:
                break

            frame_start = time.perf_counter()
            buf: list[str] = []

            # ── draw logo ─────────────────────────────────────────────────
            for i, line in enumerate(LOGO_LINES):
                colour = LOGO_COLOURS[i % len(LOGO_COLOURS)]
                buf.append(_move(logo_row + i, logo_col) + colour + line + C_RESET)

            # ── draw tagline ──────────────────────────────────────────────
            buf.append(
                _move(logo_row + len(LOGO_LINES) + 1, logo_col)
                + C_GREY
                + TAGLINE
                + C_RESET
            )

            # ── draw hint ─────────────────────────────────────────────────
            if elapsed > 3.0:
                buf.append(
                    _move(logo_row + len(LOGO_LINES) + 3, logo_col)
                    + C_DIM
                    + HINT
                    + C_RESET
                )

            # ── draw TV with static ───────────────────────────────────────
            tv_buf = _build_tv(tv_inner_row, tv_inner_col, tick)
            buf.extend(tv_buf)

            sys.stdout.write("".join(buf))
            sys.stdout.flush()

            elapsed_frame = time.perf_counter() - frame_start
            sleep = frame_time - elapsed_frame
            if sleep > 0:
                time.sleep(sleep)

            tick += 1

    finally:
        # ── TV shutoff animation ──────────────────────────────────────────
        _tv_off_flash(tv_inner_row, tv_inner_col, term_cols)

        sys.stdout.write(CLEAR + SHOW_CUR + C_RESET)
        sys.stdout.flush()
