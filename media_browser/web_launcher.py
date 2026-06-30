from __future__ import annotations

import argparse
import signal
import sys
import threading
import webbrowser

from .server import ServerContext, serve_in_thread


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Launch the web media browser and local API server.")
    parser.add_argument("--config", default=None, help="Path to api_keys.json.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host. Defaults to 127.0.0.1.")
    parser.add_argument("--port", type=int, default=0, help="Bind port. 0 means random free port.")
    parser.add_argument("--no-open", action="store_true", help="Do not open the browser automatically.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    context = ServerContext.from_config_path(args.config)
    server, thread = serve_in_thread(context, host=args.host, port=args.port)
    url = f"{server.base_url}/?token={context.token}"
    stopped = threading.Event()

    def stop(_signum: int, _frame: object) -> None:
        stopped.set()
        server.shutdown()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    print(f"DaVinci Online Media Browser: {url}", flush=True)
    if not args.no_open:
        webbrowser.open(url)

    try:
        while not stopped.is_set():
            stopped.wait(0.5)
    finally:
        server.shutdown()
        thread.join(timeout=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
