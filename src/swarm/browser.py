from __future__ import annotations

import queue
import threading
from collections.abc import Callable
from concurrent.futures import Future
from pathlib import Path
from typing import Any

ACTION_TIMEOUT_MS = 15_000
_SHUTDOWN = object()


class _Worker:
    def __init__(self) -> None:
        self._queue: queue.Queue = queue.Queue()
        self._ready = threading.Event()
        self._error: BaseException | None = None
        self._thread = threading.Thread(target=self._run, name="swarm-browser", daemon=True)
        self._thread.start()
        self._ready.wait(timeout=30)
        if self._error:
            raise self._error

    def _run(self) -> None:
        try:
            from playwright.sync_api import sync_playwright
            pw = sync_playwright().start()
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(viewport={"width": 1024, "height": 768})
            page = ctx.new_page()
            page.set_default_timeout(ACTION_TIMEOUT_MS)
        except BaseException as e:
            self._error = e
            self._ready.set()
            return

        self._ready.set()
        try:
            while True:
                item = self._queue.get()
                if item is _SHUTDOWN:
                    return
                fn, fut = item
                try:
                    fut.set_result(fn(page))
                except BaseException as e:
                    fut.set_exception(e)
        finally:
            try:
                browser.close()
            finally:
                pw.stop()

    def submit(self, fn: Callable[[Any], Any]) -> Any:
        fut: Future = Future()
        self._queue.put((fn, fut))
        return fut.result()

    def stop(self) -> None:
        self._queue.put(_SHUTDOWN)
        self._thread.join(timeout=5)


_worker: _Worker | None = None


def _w() -> _Worker:
    global _worker
    if _worker is None:
        _worker = _Worker()
    return _worker


def shutdown() -> None:
    global _worker
    if _worker is not None:
        _worker.stop()
        _worker = None


def screenshot_url(url: str, out: Path, settle_ms: int = 500) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)

    def do(page) -> Path:
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(settle_ms)
        page.screenshot(path=str(out), full_page=False)
        return out

    return _w().submit(do)
