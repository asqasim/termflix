import shutil
import subprocess
import sys


def get_os() -> str:
    """Detect and return the operating system name."""
    platform_map = {
        "win32": "windows",
        "darwin": "macos",
        "linux": "linux",
    }
    if sys.platform not in platform_map:
        raise OSError(f"Unsupported operating system: {sys.platform}")
    return platform_map[sys.platform]


def clear_screen() -> None:
    """Clear the terminal screen."""
    if MY_OS == "windows":
        subprocess.run(["cls"], shell=True, check=True)
    else:
        subprocess.run(["clear"], check=True)


def get_terminal_size() -> tuple[int, int]:
    """Return current terminal size as (columns, lines)."""
    size = shutil.get_terminal_size(fallback=(80, 24))
    return size.columns, size.lines


MY_OS = get_os()
