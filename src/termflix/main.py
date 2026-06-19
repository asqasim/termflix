from __future__ import annotations

from termflix.tui.app import TermflixApp
from termflix.tui.intro_anim import run_intro


def main() -> None:
    run_intro()
    app = TermflixApp()
    app.run()


if __name__ == "__main__":
    main()
