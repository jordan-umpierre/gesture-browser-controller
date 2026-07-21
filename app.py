from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading

from controller import COMMANDS, Controller, GestureRecognizer, new_channel_token


ROOT = Path(__file__).parent
HTML = (ROOT / "index.html").read_text()


class App:
    def __init__(self) -> None:
        self.controller = Controller()
        self.token = new_channel_token()


def make_handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: str, content_type: str = "application/json") -> None:
            encoded = body.encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(encoded)

        def _authorized(self) -> bool:
            origin = self.headers.get("Origin")
            return self.headers.get("Authorization") == f"Bearer {app.token}" and (origin in {None, "http://127.0.0.1:8765", "http://localhost:8765"})

        def do_GET(self) -> None:
            if self.path == "/":
                self._send(200, HTML.replace("__TOKEN__", app.token), "text/html; charset=utf-8")
            elif self.path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
            elif self.path == "/api/state" and self._authorized():
                self._send(200, json.dumps(app.controller.snapshot()))
            else:
                self._send(401, '{"error":"unauthorized"}')

        def do_POST(self) -> None:
            if not self._authorized():
                self._send(401, '{"error":"unauthorized"}')
                return
            if self.path == "/api/pause":
                app.controller.pause()
            elif self.path == "/api/resume":
                app.controller.resume()
            elif self.path == "/api/command":
                try:
                    data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
                    command = data["command"]
                    if command not in COMMANDS:
                        raise ValueError
                    app.controller.execute(command)
                except (ValueError, KeyError, json.JSONDecodeError):
                    self._send(400, '{"error":"invalid command"}')
                    return
            else:
                self._send(404, '{"error":"not found"}')
                return
            self._send(200, json.dumps(app.controller.snapshot()))

        def log_message(self, *_args) -> None:
            pass

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Local Gesture Browser Controller")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--camera", action="store_true", help="explicitly request the local camera")
    args = parser.parse_args()
    app = App()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(app))
    if args.camera:
        from camera import run_camera
        app.controller.resume()
        threading.Thread(target=run_camera, args=(app.controller.observe, GestureRecognizer(app.controller.profile)), daemon=True).start()
    print(f"Open http://127.0.0.1:{args.port} — processing stays local; press Ctrl-C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
