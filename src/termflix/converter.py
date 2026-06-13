from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, UnidentifiedImageError

# ── Character sets ─────────────────────────────────────────────────────────────

# 10-char ASCII — high contrast, best for B&W recognition
ASCII_CHARS_10 = r"@%#*+=-:. "

# 70-char ASCII — smooth gradients, better for color
ASCII_CHARS_70 = (
    r"$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\|()1{}[]?-_+~<>i!lI;:,\"^`'. "
)

# Braille unicode block U+2800–U+28FF
# Each character is a 2×4 dot grid = 8 pixels per character
# Dot bit mapping (historical, non-linear order):
#   col 0  col 1
#   dot1   dot4   → bit 0, bit 3
#   dot2   dot5   → bit 1, bit 4
#   dot3   dot6   → bit 2, bit 5
#   dot7   dot8   → bit 6, bit 7
BRAILLE_OFFSET = 0x2800
BRAILLE_DOT_MAP = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80]

# Maps (row, col) position in the 4×2 block to its bit value
BRAILLE_BIT_MAP: dict[tuple[int, int], int] = {
    (0, 0): 0x01,
    (0, 1): 0x08,
    (1, 0): 0x02,
    (1, 1): 0x10,
    (2, 0): 0x04,
    (2, 1): 0x20,
    (3, 0): 0x40,
    (3, 1): 0x80,
}

# Terminal characters are roughly twice as tall as wide.
# This corrects aspect ratio so images don't appear vertically squashed.
ASPECT_RATIO_CORRECTION = 0.45

# Braille chars are 2 wide × 4 tall pixels each, so aspect correction differs
BRAILLE_ASPECT_CORRECTION = 0.25


class RenderMode:
    ASCII_10 = "ascii10"
    ASCII_70 = "ascii70"
    BRAILLE = "braille"


# ── Public API ─────────────────────────────────────────────────────────────────


def load_image(path: str | Path) -> Image.Image:
    """Load an image from disk and return a Pillow Image object.

    Args:
        path: Path to the image file.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not a valid image.

    Returns:
        A Pillow Image object.
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {path}")

    try:
        image = Image.open(path)
        image.load()  # force decode now so errors surface here, not later
    except UnidentifiedImageError as e:
        raise ValueError(f"File is not a valid image: {path}") from e

    return image


def resize_image(
    image: Image.Image,
    width: int,
    *,
    mode: str = RenderMode.ASCII_10,
) -> Image.Image:
    """Resize image to target width with correct aspect ratio for the render mode.

    Args:
        image: A Pillow Image object.
        width: Target width in terminal columns.
        mode: Render mode — affects aspect ratio correction.

    Raises:
        ValueError: If width is not a positive integer.

    Returns:
        A resized Pillow Image object.
    """
    if width <= 0:
        raise ValueError(f"Width must be a positive integer, got {width}")

    original_width, original_height = image.size
    aspect_ratio = original_height / original_width

    if mode == RenderMode.BRAILLE:
        # Braille chars cover 2×4 pixels so we need 4× the pixel rows
        # but only 2× the pixel columns per terminal character
        pixel_width = width * 2
        correction = BRAILLE_ASPECT_CORRECTION
        pixel_height = int(pixel_width * aspect_ratio * correction) * 4
        return image.resize((pixel_width, pixel_height), Image.LANCZOS)

    height = int(width * aspect_ratio * ASPECT_RATIO_CORRECTION)
    return image.resize((width, height), Image.LANCZOS)


def image_to_ascii(
    image: Image.Image,
    *,
    colored: bool = False,
    mode: str = RenderMode.ASCII_10,
) -> str:
    """Convert a Pillow image to a terminal-renderable string.

    Args:
        image: A Pillow Image object. Should already be resized.
        colored: If True, wraps characters in ANSI truecolor escape codes.
        mode: One of RenderMode.ASCII_10, ASCII_70, or BRAILLE.

    Returns:
        A string of characters representing the image, rows separated by newlines.
    """
    if mode == RenderMode.BRAILLE:
        return _image_to_braille(image, colored=colored)

    chars = ASCII_CHARS_10 if mode == RenderMode.ASCII_10 else ASCII_CHARS_70

    if colored:
        rgb = image.convert("RGB")
        pixels = np.array(rgb)
        rows = []
        for row in pixels:
            line = "".join(
                _pixel_to_colored_char(r, g, b, chars=chars) for r, g, b in row
            )
            rows.append(line)
        return "\n".join(rows)

    gray = np.array(image.convert("L"))
    rows = []
    for row in gray:
        line = "".join(_brightness_to_char(p, chars=chars) for p in row)
        rows.append(line)
    return "\n".join(rows)


def convert_image(
    path: str | Path,
    *,
    width: int = 80,
    colored: bool = False,
    mode: str = RenderMode.ASCII_10,
) -> str:
    """Full pipeline: load, resize, and convert an image to a terminal string.

    Args:
        path: Path to the image file.
        width: Target width in terminal columns. Defaults to 80.
        colored: Whether to use ANSI color codes. Defaults to False.
        mode: Character mode. Defaults to RenderMode.ASCII_10.

    Returns:
        Terminal string representation of the image.
    """
    image = load_image(path)
    image = resize_image(image, width, mode=mode)
    return image_to_ascii(image, colored=colored, mode=mode)


# ── Private helpers ────────────────────────────────────────────────────────────


def _brightness_to_char(brightness: int, *, chars: str) -> str:
    """Map a 0–255 brightness value to a character from the given set."""
    index = int(brightness / 255 * (len(chars) - 1))
    return chars[index]


def _pixel_to_colored_char(r: int, g: int, b: int, *, chars: str) -> str:
    """Wrap a character in an ANSI truecolor escape code."""
    brightness = int(0.299 * r + 0.587 * g + 0.114 * b)  # ITU-R BT.601 luminance
    char = _brightness_to_char(brightness, chars=chars)
    return f"\033[38;2;{r};{g};{b}m{char}\033[0m"


def _image_to_braille(image: Image.Image, *, colored: bool = False) -> str:
    """Convert a pre-resized image to Braille unicode characters.

    The image must have dimensions that are multiples of 2 (width) and 4 (height)
    since each Braille character covers a 2×4 pixel block.

    Args:
        image: A Pillow Image object sized at pixel_width × pixel_height.
        colored: If True, colors each Braille char with the average block color.

    Returns:
        A Braille string representing the image.
    """
    gray = np.array(image.convert("L"))
    threshold = 128  # pixels brighter than this become a raised dot

    pixel_height, pixel_width = gray.shape
    char_width = pixel_width // 2
    char_height = pixel_height // 4

    rows = []

    if colored:
        rgb = np.array(image.convert("RGB"))

    for char_row in range(char_height):
        line = []
        for char_col in range(char_width):
            # Extract the 4×2 pixel block for this braille character
            py = char_row * 4
            px = char_col * 2

            bits = 0
            for row_offset in range(4):
                for col_offset in range(2):
                    pixel_brightness = gray[py + row_offset, px + col_offset]
                    if pixel_brightness > threshold:
                        bits |= BRAILLE_BIT_MAP[(row_offset, col_offset)]

            char = chr(BRAILLE_OFFSET + bits)

            if colored:
                # Average color of the 4×2 block
                block = rgb[py : py + 4, px : px + 2]
                avg = block.mean(axis=(0, 1)).astype(int)
                r, g, b = int(avg[0]), int(avg[1]), int(avg[2])
                char = f"\033[38;2;{r};{g};{b}m{char}\033[0m"

            line.append(char)

        rows.append("".join(line))

    return "\n".join(rows)
