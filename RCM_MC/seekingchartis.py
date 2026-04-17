#!/usr/bin/env python3
"""SeekingChartis — one command to launch.

Usage:
    python seekingchartis.py
    python seekingchartis.py --port 9090
    python seekingchartis.py --db my_portfolio.db --no-browser

Starts the server and opens the browser automatically.
"""
from __future__ import annotations

import argparse
import os
import sys
import threading
import time
import webbrowser


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SeekingChartis — Healthcare PE Diligence Platform",
    )
    parser.add_argument("--port", type=int, default=8080, help="Port (default 8080)")
    parser.add_argument("--db", default="seekingchartis.db", help="Database file (default seekingchartis.db)")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    args = parser.parse_args()

    # Ensure we're in the right directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # Add to path if needed
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    from rcm_mc import __version__, __product__
    from rcm_mc.server import build_server

    url = f"http://127.0.0.1:{args.port}"

    print(f"""
  ╔═══════════════════════════════════════════════════════╗
  ║                                                       ║
  ║   {__product__} v{__version__}                        ║
  ║   Healthcare PE Diligence Platform                    ║
  ║                                                       ║
  ║   {url:<50s}║
  ║                                                       ║
  ║   Database: {args.db:<41s}║
  ║                                                       ║
  ║   Pages:                                              ║
  ║     Home .............. {url}/home                     ║
  ║     Market Data ....... {url}/market-data/map          ║
  ║     News .............. {url}/news                     ║
  ║     Screener .......... {url}/screen                   ║
  ║     Library ........... {url}/library                  ║
  ║     API Docs .......... {url}/api/docs                 ║
  ║                                                       ║
  ║   Ctrl+C to stop                                      ║
  ║                                                       ║
  ╚═══════════════════════════════════════════════════════╝
""")

    server, handler_cls = build_server(port=args.port, db_path=args.db)

    if not args.no_browser:
        def _open():
            time.sleep(0.3)
            webbrowser.open(f"{url}/home")
        threading.Thread(target=_open, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
        server.server_close()
        print("Done.")


if __name__ == "__main__":
    main()
