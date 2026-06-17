from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ASCII_CHARS_BW = np.array(list(r" .:-=+*#%@"))
ASCII_CHARS_COLOR = np.array(
    list(r" .'`^\",:;Il!i~+_-?][}{1)(|\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao#MW&8%B@$")
)

ASPECT_RATIO_CORRECTION = 0.45
BRAILLE_ASPECT_CORRECTION = 0.25

BRAILLE_OFFSET = 0x2800
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

_BRAILLE_ROW_OFFSETS = np.array([0, 0, 1, 1, 2, 2, 3, 3])
_BRAILLE_COL_OFFSETS = np.array([0, 1, 0, 1, 0, 1, 0, 1])
_BRAILLE_BITS = np.array([0x01, 0x08, 0x02, 0x10, 0x04, 0x20, 0x40, 0x80])


class RenderMode:
    ASCII = "ascii"
    BRAILLE = "braille"


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
        image.load()
    except Exception as e:
        raise ValueError(f"File is not a valid image: {path}") from e

    return image


def fit_to_terminal(
    image: Image.Image,
    *,
    mode: str = RenderMode.ASCII,
) -> tuple[int, int]:
    """Calculate width and height that fit the image inside the current terminal.

    Constrains by both terminal width and height while preserving aspect ratio.

    Args:
        image: A Pillow Image object.
        mode: Render mode affects aspect ratio correction.

    Returns:
        A tuple of (width, height) that fits inside the terminal.
    """
    from termflix.compat import get_terminal_size

    term_cols, term_lines = get_terminal_size()
    term_lines -= 2

    orig_w, orig_h = image.size
    aspect_ratio = orig_h / orig_w

    correction = (
        BRAILLE_ASPECT_CORRECTION
        if mode == RenderMode.BRAILLE
        else ASPECT_RATIO_CORRECTION
    )

    width = term_cols
    height = int(width * aspect_ratio * correction)

    if height > term_lines:
        height = term_lines
        width = int(height / (aspect_ratio * correction))

    return max(1, width), max(1, height)


def resize_image(
    image: Image.Image,
    width: int,
    *,
    mode: str = RenderMode.ASCII,
) -> Image.Image:
    """Resize image to target width with correct aspect ratio for the render mode.

    Args:
        image: A Pillow Image object.
        width: Target width in terminal columns.
        mode: Render mode affects aspect ratio correction.

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
        pixel_width = width * 2
        pixel_height = int(pixel_width * aspect_ratio * BRAILLE_ASPECT_CORRECTION) * 4
        return image.resize((pixel_width, pixel_height), Image.LANCZOS)

    height = int(width * aspect_ratio * ASPECT_RATIO_CORRECTION)
    return image.resize((width, height), Image.LANCZOS)


def resize_frame(
    frame_rgb: np.ndarray,
    width: int,
    *,
    mode: str = RenderMode.ASCII,
) -> np.ndarray:
    """Resize a raw numpy RGB frame directly using OpenCV.

    Args:
        frame_rgb: A numpy array of shape (H, W, 3) in RGB order.
        width: Target width in terminal columns.
        mode: Render mode affects aspect ratio correction.

    Raises:
        ValueError: If width is not a positive integer or cv2.resize fails.

    Returns:
        A resized numpy array.
    """
    if width <= 0:
        raise ValueError(f"Width must be a positive integer, got {width}")

    h, w = frame_rgb.shape[:2]
    aspect_ratio = h / w

    if mode == RenderMode.BRAILLE:
        pixel_width = width * 2
        pixel_height = int(pixel_width * aspect_ratio * BRAILLE_ASPECT_CORRECTION) * 4
        pixel_height = max(4, (pixel_height // 4) * 4)
        result = cv2.resize(
            frame_rgb, (pixel_width, pixel_height), interpolation=cv2.INTER_LINEAR
        )
    else:
        pixel_height = max(1, int(width * aspect_ratio * ASPECT_RATIO_CORRECTION))
        result = cv2.resize(
            frame_rgb, (width, pixel_height), interpolation=cv2.INTER_LINEAR
        )

    if result is None:
        raise ValueError(
            f"cv2.resize returned None for dimensions ({width}, {pixel_height})"
        )

    return result


def frame_to_ascii(
    frame_rgb: np.ndarray,
    *,
    colored: bool = False,
    mode: str = RenderMode.ASCII,
) -> str:
    """Convert a raw numpy RGB frame to a terminal string — fully vectorized.

    Args:
        frame_rgb: A numpy array of shape (H, W, 3) in RGB order.
        colored: If True, wraps characters in ANSI truecolor escape codes.
        mode: RenderMode.ASCII or RenderMode.BRAILLE.

    Returns:
        A terminal string representing the frame.
    """
    if mode == RenderMode.BRAILLE:
        return _frame_to_braille(frame_rgb, colored=colored)

    chars = ASCII_CHARS_COLOR if colored else ASCII_CHARS_BW

    gray = (
        0.299 * frame_rgb[:, :, 0]
        + 0.587 * frame_rgb[:, :, 1]
        + 0.114 * frame_rgb[:, :, 2]
    ).astype(np.uint8)

    indices = (gray.astype(np.float32) / 255 * (len(chars) - 1)).astype(np.int32)
    char_array = chars[indices]

    if not colored:
        return "\n".join("".join(row) for row in char_array)

    r = frame_rgb[:, :, 0]
    g = frame_rgb[:, :, 1]
    b = frame_rgb[:, :, 2]

    rows = []
    for y in range(char_array.shape[0]):
        parts = []
        for x in range(char_array.shape[1]):
            parts.append(
                f"\033[38;2;{r[y, x]};{g[y, x]};{b[y, x]}m{char_array[y, x]}\033[0m"
            )
        rows.append("".join(parts))
    return "\n".join(rows)


def image_to_ascii(
    image: Image.Image,
    *,
    colored: bool = False,
    mode: str = RenderMode.ASCII,
) -> str:
    """Convert a Pillow image to a terminal string.

    Args:
        image: A Pillow Image object. Should already be resized.
        colored: If True, wraps characters in ANSI truecolor escape codes.
        mode: RenderMode.ASCII or RenderMode.BRAILLE.

    Returns:
        A string of characters representing the image, rows separated by newlines.
    """
    frame_rgb = np.array(image.convert("RGB"))
    return frame_to_ascii(frame_rgb, colored=colored, mode=mode)


def convert_image(
    path: str | Path,
    *,
    width: int = 0,
    colored: bool = False,
    mode: str = RenderMode.ASCII,
) -> str:
    """Full pipeline: load, resize, and convert an image to a terminal string.

    Args:
        path: Path to the image file.
        width: Target width in terminal columns. 0 means auto-fit to terminal.
        colored: Whether to use ANSI color codes. Defaults to False.
        mode: RenderMode.ASCII or RenderMode.BRAILLE. Defaults to ASCII.

    Returns:
        Terminal string representation of the image.
    """
    image = load_image(path)

    if width == 0:
        width, _ = fit_to_terminal(image, mode=mode)

    image = resize_image(image, width, mode=mode)
    return image_to_ascii(image, colored=colored, mode=mode)


def _brightness_to_char(brightness: int, *, chars: np.ndarray) -> str:
    index = int(brightness / 255 * (len(chars) - 1))
    return chars[index]


def _frame_to_braille(frame_rgb: np.ndarray, *, colored: bool = False) -> str:
    """Convert a numpy RGB frame to Braille unicode — vectorized."""
    gray = (
        0.299 * frame_rgb[:, :, 0]
        + 0.587 * frame_rgb[:, :, 1]
        + 0.114 * frame_rgb[:, :, 2]
    ).astype(np.uint8)

    threshold = int(np.mean(gray))
    binary = (gray > threshold).astype(np.uint8)

    pixel_height, pixel_width = gray.shape
    char_height = pixel_height // 4
    char_width = pixel_width // 2

    blocks = binary[: char_height * 4, : char_width * 2]
    blocks = blocks.reshape(char_height, 4, char_width, 2).transpose(0, 2, 1, 3)

    bits = np.zeros((char_height, char_width), dtype=np.uint32)
    for row in range(4):
        for col in range(2):
            bit_value = BRAILLE_BIT_MAP[(row, col)]
            bits += blocks[:, :, row, col].astype(np.uint32) * bit_value

    chars = np.vectorize(lambda b: chr(BRAILLE_OFFSET + b))(bits)

    if not colored:
        return "\n".join("".join(row) for row in chars)

    rgb = frame_rgb[: char_height * 4, : char_width * 2]
    rgb_blocks = rgb.reshape(char_height, 4, char_width, 2, 3).transpose(0, 2, 1, 3, 4)
    avg_colors = rgb_blocks.mean(axis=(2, 3)).astype(np.uint8)

    rows = []
    for y in range(char_height):
        parts = []
        for x in range(char_width):
            r, g, b = avg_colors[y, x]
            parts.append(f"\033[38;2;{r};{g};{b}m{chars[y, x]}\033[0m")
        rows.append("".join(parts))
    return "\n".join(rows)
