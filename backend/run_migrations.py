from pathlib import Path
import sys

from alembic.config import main as alembic_main


def main() -> int:
    root = Path(__file__).resolve().parent
    config_path = root / "alembic.ini"
    return alembic_main(["-c", str(config_path), "upgrade", "head"])


if __name__ == "__main__":
    raise SystemExit(main())
