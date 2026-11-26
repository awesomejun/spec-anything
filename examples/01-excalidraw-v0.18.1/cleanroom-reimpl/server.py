#!/usr/bin/env python3
"""
Zero-dependency Python stdlib static HTTP server for SketchBoard CR (clean-room whiteboard).
Serves cleanroom-reimpl/ on 127.0.0.1:<port> (default 4183).
"""
import argparse
import functools
import http.server
import pathlib
import socketserver


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


def main():
    ap = argparse.ArgumentParser(description="Serve SketchBoard CR clean-room whiteboard")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=4183)
    args = ap.parse_args()

    root = pathlib.Path(__file__).resolve().parent
    handler = functools.partial(QuietHandler, directory=str(root))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((args.host, args.port), handler) as httpd:
        print(f"SketchBoard CR listening on http://{args.host}:{args.port}/", flush=True)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
