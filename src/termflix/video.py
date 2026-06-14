from __future__ import annotations

from pathlib import Path
from typing import Generator

import cv2
from PIL import Image


class VideoMetadata:
    """Holds metadata extracted from a video file."""

    def __init__(self, fps: float, frame_count: int, width: int, height: int) -> None:
        self.fps = fps
        self.frame_count = frame_count
        self.width = width
        self.height = height
        self.duration = frame_count / fps if fps > 0 else 0.0

    def __repr__(self) -> str:
        return (
            f"VideoMetadata("
            f"fps={self.fps:.2f}, "
            f"frames={self.frame_count}, "
            f"resolution={self.width}x{self.height}, "
            f"duration={self.duration:.2f}s)"
        )


def open_video(path: str | Path) -> tuple[cv2.VideoCapture, VideoMetadata]:
    """Open a video file and return a capture object with its metadata.

    Args:
        path: Path to the video file.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file cannot be opened as a video.

    Returns:
        A tuple of (VideoCapture, VideoMetadata).
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Video file not found: {path}")

    cap = cv2.VideoCapture(str(path))

    if not cap.isOpened():
        raise ValueError(f"File could not be opened as a video: {path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    metadata = VideoMetadata(
        fps=fps,
        frame_count=frame_count,
        width=width,
        height=height,
    )

    return cap, metadata


def extract_frames(
    cap: cv2.VideoCapture,
    *,
    start_frame: int = 0,
    end_frame: int | None = None,
    step: int = 1,
) -> Generator[tuple[int, Image.Image], None, None]:
    """Yield frames from a VideoCapture as Pillow images.

    Args:
        cap: An open cv2.VideoCapture object.
        start_frame: Frame index to start from. Defaults to 0.
        end_frame: Frame index to stop at (exclusive). None means end of video.
        step: Yield every nth frame. Defaults to 1 (every frame).

    Yields:
        A tuple of (frame_index, PIL Image) for each frame.
    """
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    end = end_frame if end_frame is not None else total_frames

    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    for frame_index in range(start_frame, end, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        success, frame_bgr = cap.read()

        if not success:
            break

        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        yield frame_index, Image.fromarray(frame_rgb)


def get_frame_at(cap: cv2.VideoCapture, frame_index: int) -> Image.Image:
    """Extract a single frame at a specific index.

    Args:
        cap: An open cv2.VideoCapture object.
        frame_index: The frame index to extract.

    Raises:
        ValueError: If the frame could not be read.

    Returns:
        A Pillow Image of the frame.
    """
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    success, frame_bgr = cap.read()

    if not success:
        raise ValueError(f"Could not read frame at index {frame_index}")

    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    return Image.fromarray(frame_rgb)


def release_video(cap: cv2.VideoCapture) -> None:
    """Release a VideoCapture object and free its resources.

    Args:
        cap: An open cv2.VideoCapture object.
    """
    cap.release()
