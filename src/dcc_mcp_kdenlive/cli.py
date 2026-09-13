"""CLI bootstrap: explicit host binding or independent file/render service."""

import argparse
import json
import os
import signal
import threading

from . import __version__


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    parser.set_defaults(port=None, pid=None, hwnd=None, host_version=None)
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("doctor")
    serve = sub.add_parser("serve")
    serve.add_argument("--port", type=int)
    serve.add_argument("--pid", type=int)
    serve.add_argument("--hwnd", type=int)
    serve.add_argument("--host-version")
    args = parser.parse_args()
    if args.command == "doctor":
        from .runtime import get_status

        print(json.dumps(get_status(), indent=2))
        return
    if bool(args.pid) != bool(args.hwnd):
        parser.error("--pid and --hwnd must be supplied together")
    if args.pid:
        # Operator-selected exact host scope; core/DCC-CUA verifies HWND ownership.
        os.environ["DCC_MCP_UI_CONTROL_UIA_PROCESS_ID"] = str(args.pid)
        os.environ["DCC_MCP_UI_CONTROL_UIA_WINDOW_HANDLE"] = str(args.hwnd)
    from .server import KdenliveServer

    server = KdenliveServer(args.port, args.pid, args.hwnd, args.host_version)
    stopped = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stopped.set())
    try:
        server.register_builtin_actions()
        server.start()
        print(
            json.dumps({"mcp_url": server.mcp_url, "instance_id": server.instance_id}), flush=True
        )
        while not stopped.wait(1):
            if args.pid:
                from .runtime import validate_host

                validate_host(args.pid)
    finally:
        server.stop()


if __name__ == "__main__":
    main()
