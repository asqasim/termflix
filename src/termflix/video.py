from __future__ import annotations

import threading
import time
from pathlib import Path
from queue import Empty, Queue
from typing import Generator

import cv2
from PIL import Image

from termflix.image import RenderMode, image_to_ascii, resize_image

_SENTINEL = object()  # signals threads to stop


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
    Used for single-threaded contexts like image preview.

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


class VideoPlayer:
    """Threaded video player that decodes, renders, and displays frames in parallel.

    Architecture:
        Reader thread  → raw_queue  → Renderer thread → rendered_queue → Display (main)

    The reader and renderer run ahead of display, keeping a buffer of
    pre-rendered ASCII frames ready so display never waits on processing.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        width: int = 80,
        colored: bool = False,
        mode: str = RenderMode.ASCII,
        raw_buffer_size: int = 32,
        rendered_buffer_size: int = 16,
    ) -> None:
        self.path = path
        self.width = width
        self.colored = colored
        self.mode = mode

        self._raw_queue: Queue = Queue(maxsize=raw_buffer_size)
        self._rendered_queue: Queue = Queue(maxsize=rendered_buffer_size)

        self._stop_event = threading.Event()
        self._reader_thread = threading.Thread(target=self._reader, daemon=True)
        self._renderer_thread = threading.Thread(target=self._renderer, daemon=True)

        self.metadata: VideoMetadata | None = None

    def play(self) -> None:
        """Start playback. Blocks until video ends or user interrupts with Ctrl+C."""
        cap, self.metadata = open_video(self.path)

        self._reader_thread = threading.Thread(
            target=self._reader, args=(cap,), daemon=True
        )
        self._renderer_thread = threading.Thread(target=self._renderer, daemon=True)

        self._reader_thread.start()
        self._renderer_thread.start()

        self._display()

        self._stop_event.set()
        self._reader_thread.join(timeout=2)
        self._renderer_thread.join(timeout=2)
        release_video(cap)

    def _reader(self, cap: cv2.VideoCapture) -> None:
        """Thread: reads raw BGR frames from disk and puts them in raw_queue."""
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        for _ in range(total):
            if self._stop_event.is_set():
                break

            success, frame_bgr = cap.read()
            if not success:
                break

            # convert BGR → RGB numpy array, keep as numpy for speed
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            self._raw_queue.put(frame_rgb)  # blocks if buffer is full — intentional

        self._raw_queue.put(_SENTINEL)

    def _renderer(self) -> None:
        """Thread: takes raw numpy frames, converts to ASCII, puts in rendered_queue."""
        while not self._stop_event.is_set():
            try:
                frame = self._raw_queue.get(timeout=1)
            except Empty:
                continue

            if frame is _SENTINEL:
                self._rendered_queue.put(_SENTINEL)
                break

            pil_image = Image.fromarray(frame)
            resized = resize_image(pil_image, self.width, mode=self.mode)
            rendered = image_to_ascii(resized, colored=self.colored, mode=self.mode)
            self._rendered_queue.put(rendered)

    def _display(self) -> None:
        """Main thread: pulls pre-rendered strings and prints at correct fps timing."""
        assert self.metadata is not None
        frame_duration = 1.0 / self.metadata.fps

        # clear screen once before playback starts
        print("\033[2J\033[H", end="", flush=True)

        try:
            while not self._stop_event.is_set():
                start = time.perf_counter()

                try:
                    frame_str = self._rendered_queue.get(timeout=2)
                except Empty:
                    break

                if frame_str is _SENTINEL:
                    break

                # move cursor to top-left and overwrite — no flicker clear
                print("\033[H", end="")
                print(frame_str, flush=True)

                elapsed = time.perf_counter() - start
                sleep_time = frame_duration - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            pass
