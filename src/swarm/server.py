import socket
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class StaticServer:
    def __init__(self, workdir: Path) -> None:
        self.workdir = workdir.resolve()
        self.port = _free_port()
        handler = partial(_QuietHandler, directory=str(self.workdir))
        self._httpd = ThreadingHTTPServer(("127.0.0.1", self.port), handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    def start(self) -> str:
        self._thread.start()
        return f"http://127.0.0.1:{self.port}/index.html"

    def stop(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args, **kwargs) -> None:
        pass


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
