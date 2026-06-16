from __future__ import annotations

# import math
import threading
import time
from pathlib import Path
from queue import Empty, Queue
from typing import Generator

import cv2
from PIL import Image

from termflix.compat import get_terminal_size
from termflix.image import RenderMode, frame_to_ascii, resize_frame

_SENTINEL = object()


MAX_RENDER_WIDTH = 300  # beyond this zoom level, stop auto-adjusting


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


def extract_frames(
    cap: cv2.VideoCapture,
    *,
    start_frame: int = 0,
    end_frame: int | None = None,
    step: int = 1,
) -> Generator[tuple[int, Image.Image], None, None]:
    """Yield frames one at a time from a VideoCapture as Pillow images.

    Args:
        cap: An open cv2.VideoCapture object.
        start_frame: Frame index to start from. Defaults to 0.
        end_frame: Frame index to stop at exclusive. None means end of video.
        step: Yield every nth frame. Defaults to 1.

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


def _current_render_width() -> int:
    """Return clamped terminal width for rendering.

    Clamps between 20 and MAX_RENDER_WIDTH so extreme zoom-out
    doesn't keep increasing resolution and slowing playback.
    """
    columns, _ = get_terminal_size()
    return max(20, min(columns, MAX_RENDER_WIDTH))


class VideoPlayer:
    """Threaded video player with live terminal resize detection.

    Architecture:
        Reader thread  → raw_queue  → Renderer thread → rendered_queue → Display

    The renderer checks terminal size before each frame. If it changed since
    the last frame, it re-renders at the new dimensions automatically.
    Zooming in or out takes effect within 1-2 frames.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        colored: bool = False,
        mode: str = RenderMode.ASCII,
        raw_buffer_size: int = 32,
        rendered_buffer_size: int = 16,
    ) -> None:
        self.path = path
        self.colored = colored
        self.mode = mode

        self._raw_queue: Queue = Queue(maxsize=raw_buffer_size)
        self._rendered_queue: Queue = Queue(maxsize=rendered_buffer_size)
        self._stop_event = threading.Event()

        self.metadata: VideoMetadata | None = None

        # shared state between renderer and display — protected by a lock
        self._current_width = _current_render_width()
        self._width_lock = threading.Lock()

    def play(self) -> None:
        """Start playback. Blocks until video ends or user interrupts with Ctrl+C."""
        cap, self.metadata = open_video(self.path)

        reader_thread = threading.Thread(target=self._reader, args=(cap,), daemon=True)
        renderer_thread = threading.Thread(target=self._renderer, daemon=True)

        reader_thread.start()
        renderer_thread.start()

        self._display()

        self._stop_event.set()
        reader_thread.join(timeout=2)
        renderer_thread.join(timeout=2)
        release_video(cap)

    def _reader(self, cap: cv2.VideoCapture) -> None:
        """Thread: reads raw BGR frames from disk into raw_queue."""
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        for _ in range(total):
            if self._stop_event.is_set():
                break

            success, frame_bgr = cap.read()
            if not success:
                break

            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            self._raw_queue.put(frame_rgb)

        self._raw_queue.put(_SENTINEL)

    def _renderer(self) -> None:
        """Thread: converts raw frames to ASCII, detecting terminal resize each frame."""
        last_width = self._current_width

        while not self._stop_event.is_set():
            try:
                frame = self._raw_queue.get(timeout=1)
            except Empty:
                continue

            if frame is _SENTINEL:
                self._rendered_queue.put(_SENTINEL)
                break

            # check if terminal was resized since last frame
            new_width = _current_render_width()
            if new_width != last_width:
                last_width = new_width
                with self._width_lock:
                    self._current_width = new_width

                # drain rendered queue so stale wrong-size frames don't display
                while not self._rendered_queue.empty():
                    try:
                        self._rendered_queue.get_nowait()
                    except Empty:
                        break

            resized = resize_frame(frame, last_width, mode=self.mode)
            rendered = frame_to_ascii(resized, colored=self.colored, mode=self.mode)
            self._rendered_queue.put(rendered)

    def _display(self) -> None:
        """Main thread: prints pre-rendered frames at correct fps timing."""
        assert self.metadata is not None
        frame_duration = 1.0 / self.metadata.fps

        print("\033[2J\033[H", end="", flush=True)  # clear screen once

        try:
            while not self._stop_event.is_set():
                start = time.perf_counter()

                try:
                    frame_str = self._rendered_queue.get(timeout=2)
                except Empty:
                    break

                if frame_str is _SENTINEL:
                    break

                print("\033[H", end="")  # move cursor to top-left, no flicker
                print(frame_str, flush=True)

                elapsed = time.perf_counter() - start
                sleep_time = frame_duration - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            pass
