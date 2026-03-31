from __future__ import annotations

import sys

from .constants import DEFAULT_HOME, DEFAULT_START_PAGE
from .gui import BrowserGUI


def main() -> int:
    start_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_START_PAGE
    app = BrowserGUI(start_url=start_url, home_url=DEFAULT_HOME)
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
