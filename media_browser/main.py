from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import load_config
from .search import SearchRouter


def _run_cli(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    router = SearchRouter.from_config(config)
    result = router.search_with_errors(args.query, category=args.type, per_page=args.limit)
    payload = {
        "assets": [asset.to_dict() for asset in result.assets],
        "warnings": [{"source": error.source, "message": error.message} for error in result.errors],
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _run_ui(args: argparse.Namespace) -> int:
    try:
        from .ui.app import run_app
    except ImportError as exc:
        print(
            "Qt bindings are missing. Install them with:\n"
            "  python3 -m pip install -r requirements.txt\n\n"
            f"Original import error: {exc}",
            file=sys.stderr,
        )
        return 2

    return run_app(config_path=args.config)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DaVinci Resolve online media browser")
    parser.add_argument(
        "--config",
        default=None,
        help="Path to api_keys.json. Defaults to ./api_keys.json, ~/.davinci_plugins/api_keys.json, or the example config.",
    )
    parser.add_argument("--search", dest="query", help="Run a non-UI search and print JSON results.")
    parser.add_argument(
        "--type",
        default="all",
        choices=["auto", "all", "video", "image", "music", "sfx", "3d"],
        help="Media type for CLI search.",
    )
    parser.add_argument("--limit", type=int, default=12, help="Maximum results per adapter in CLI mode.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.query:
        return _run_cli(args)
    return _run_ui(args)


if __name__ == "__main__":
    raise SystemExit(main())
