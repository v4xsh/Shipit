"""Serve board.html and a server-sent events stream on localhost."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PAGE = Path(__file__).with_name("board.html")


def handler(hub):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # keep the terminal clean

        def do_GET(self):
            if self.path == "/events":
                return self.stream()
            if self.path not in ("/", "/index.html"):
                return self.send_error(404)
            body = PAGE.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def stream(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            seen, generation = 0, hub.generation
            try:
                while True:
                    events, seen, generation = hub.wait(seen, generation)
                    chunk = "".join(f"event: {k}\ndata: {json.dumps(d, ensure_ascii=False)}\n\n"
                                    for k, d in events) or ": ping\n\n"
                    self.wfile.write(chunk.encode("utf-8"))
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                return

    return Handler


def start(hub, port=7878):
    """Start in a daemon thread; falls back to any free port. Returns the server."""
    for p in (port, 0):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", p), handler(hub))
            break
        except OSError:
            continue
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def url(server):
    return f"http://127.0.0.1:{server.server_address[1]}/"
