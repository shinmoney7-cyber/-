"""Windows-friendly entry point:  python run_all.py [--live] [--loop 30]
Same as `python -m shopping_shorts_sync vending run`."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from shopping_shorts_sync.cli import cli  # noqa: E402

if __name__ == "__main__":
    cli(["vending", "run", *sys.argv[1:]])
