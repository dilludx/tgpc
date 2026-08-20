"""
Granular progress output for the TGPC pipeline.

Pure stdlib — no dependencies beyond the standard library.

Design:
- Progress bars and phase headers write to stdout; log lines are routed to
  stderr via ``BarHandler`` so they never corrupt the bar (and are captured
  together by CI, which merges the two streams anyway).
- On a real TTY the bar redraws in place on a single line from a background
  spinner thread, so it keeps animating even while the pipeline is blocked in
  a ``time.sleep`` (rate limiter) or ``subprocess.run`` call.
- When not a TTY (GitHub Actions, pipes) no ``\\r`` is used — discrete lines
  are printed every ``cadence`` updates, plus a heartbeat line every
  ``heartbeat_interval`` seconds whenever a step runs longer than that, so
  long operations never go silent.
"""

import itertools
import logging
import sys
import threading
import time
from contextlib import contextmanager
from typing import Optional


def _fmt_eta(seconds: Optional[float]) -> str:
    if seconds is None or seconds < 0:
        return ""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"ETA {h}h{m:02d}m{s:02d}s"
    return f"ETA {m}m{s:02d}s"


class ProgressBar:
    """Animated (TTY) or discrete-line (non-TTY) progress indicator.

    Use as a context manager::

        with ProgressBar(total=100, label="Enriching") as bar:
            for rec in records:
                bar.set_detail(rec.registration_number)
                ...
                bar.update()
    """

    def __init__(
        self,
        total: Optional[int] = None,
        label: str = "",
        stream=None,
        width: int = 40,
        cadence: int = 50,
        heartbeat_interval: int = 20,
    ):
        self.total = total
        self.label = label
        self.stream = stream or sys.stdout
        self.width = width
        self.cadence = max(1, cadence)
        self.heartbeat_interval = max(1, heartbeat_interval)
        self.tty = bool(getattr(self.stream, "isatty", lambda: False)())
        self.n = 0
        self.start = time.monotonic()
        self.last_line = self.start
        self.detail = ""
        self._max_len = 0
        self._spinner = itertools.cycle("|/-\\")
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

    # --- lifecycle ----------------------------------------------------

    def __enter__(self):
        _register(self)
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        if self.tty:
            self.draw()
        else:
            self._line(self._frame())
        return self

    def __exit__(self, exc_type, exc, tb):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1)
        _unregister(self)
        if self.tty:
            self.clear_line()
        self._line(self._frame(final=True))
        return False

    # --- API ---------------------------------------------------------

    def update(self, n: int = 1, detail: Optional[str] = None) -> None:
        with self._lock:
            self.n += n
            if detail is not None:
                self.detail = detail
            self.last_line = time.monotonic()
            if self.tty:
                self.draw()
            elif self.total is None or self.n >= self.total or self.n % self.cadence == 0:
                self._line(self._frame())

    def set_detail(self, detail: str) -> None:
        with self._lock:
            self.detail = detail
            self.last_line = time.monotonic()
            if self.tty:
                self.draw()

    def substep(self, text: str) -> None:
        """Emit a granular sub-step line for the current operation.

        On a TTY this folds into the bar's detail line (no separate output);
        when not a TTY (background/CI) it prints its own discrete line so
        every operation that runs during the process is visible in the log.
        """
        if self.tty:
            self.set_detail(text)
        else:
            self._line(f"  ↳ {text}")

    # --- rendering ----------------------------------------------------

    def _frame(self, final: bool = False) -> str:
        elapsed = time.monotonic() - self.start
        spinner = "" if final else next(self._spinner)
        if self.total is None:
            core = f"{spinner} {elapsed:.0f}s".strip()
        else:
            pct = self.n / self.total if self.total else 0
            filled = int(pct * self.width)
            bar = "#" * filled + "-" * (self.width - filled)
            rate = self.n / elapsed if elapsed > 0 else 0
            eta = _fmt_eta((self.total - self.n) / rate if rate > 0 else None)
            core = f"{spinner} {pct * 100:3.0f}% [{bar}] {self.n}/{self.total} {rate:.1f}/s {eta}".strip()
        line = f"[{self.label}] {core}" if self.label else core
        if self.detail:
            line += f" · {self.detail}"
        with self._lock:
            self._max_len = max(self._max_len, len(line))
        return line

    def _spin(self) -> None:
        while not self._stop.wait(0.15):
            if self.tty:
                self.draw()
            else:
                with self._lock:
                    if time.monotonic() - self.last_line >= self.heartbeat_interval:
                        self._line(self._frame())
                        self.last_line = time.monotonic()

    def draw(self) -> None:
        with self._lock:
            self.stream.write("\r" + self._frame())
            self.stream.flush()

    def clear_line(self) -> None:
        if self.tty:
            with self._lock:
                self.stream.write("\r" + " " * (self._max_len + 2) + "\r")
                self.stream.flush()

    def _line(self, text: str) -> None:
        with self._lock:
            self.stream.write(text + "\n")
            self.stream.flush()


class Phase:
    """Prints a ``[N/M] Label`` header and ``— done``/``— FAILED`` footer.

    Use as a context manager::

        with Phase("Health check", 2, 5):
            ok = scraper.health_check()
    """

    def __init__(self, label: str, index: int, total: int, stream=None):
        self.label = label
        self.index = index
        self.total = total
        self.stream = stream or sys.stdout
        self._failed = False

    def fail(self) -> None:
        """Mark this phase as failed (for early-abort paths that return normally)."""
        self._failed = True

    def __enter__(self):
        self.stream.write(f"[{self.index}/{self.total}] {self.label}\n")
        self.stream.flush()
        return self

    def __exit__(self, exc_type, exc, tb):
        status = "FAILED" if (exc_type or self._failed) else "done"
        self.stream.write(f"[{self.index}/{self.total}] {self.label} — {status}\n")
        self.stream.flush()
        return False


@contextmanager
def heartbeat(label: str = "", interval: int = 20, stream=None):
    """Indeterminate progress for single-shot operations with no known total.

    Prints animated ticks on a TTY and heartbeat lines otherwise, so even a
    lone network request or subprocess call never sits silent.
    """
    with ProgressBar(total=None, label=label, stream=stream, heartbeat_interval=interval) as bar:
        yield bar


# --- active bar registry (stack, bars may nest) -----------------------


_active_bars: list = []
_registry_lock = threading.Lock()


def _register(bar: ProgressBar) -> None:
    with _registry_lock:
        _active_bars.append(bar)


def _unregister(bar: ProgressBar) -> None:
    with _registry_lock:
        if _active_bars and _active_bars[-1] is bar:
            _active_bars.pop()


def _current_bar() -> Optional[ProgressBar]:
    with _registry_lock:
        return _active_bars[-1] if _active_bars else None


def step(text: str) -> None:
    """Report a granular sub-step of the currently active progress bar.

    Safe to call from anywhere in the pipeline (scraper, manager, sweeps):
    if a bar is active its detail/substep line reflects the message; if not,
    the message is printed as a plain line so it is never lost.
    """
    bar = _current_bar()
    if bar is not None:
        bar.substep(text)
    else:
        print(f"  ↳ {text}", flush=True)


class BarHandler(logging.Handler):
    """Logging handler that writes to stderr without corrupting the bar.

    On a TTY, when a progress bar is active the current bar line is cleared,
    the log line is printed, and the bar is redrawn underneath so it always
    remains the bottom line. Non-TTY output is a plain line (CI merges
    stdout + stderr anyway).
    """

    def __init__(self, stream=None, fmt: str = "%(asctime)s - %(levelname)s - %(message)s"):
        super().__init__()
        self.stream = stream or sys.stderr
        self.setFormatter(logging.Formatter(fmt))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            text = self.format(record)
            bar = _current_bar()
            if bar is not None and bar.tty:
                bar.clear_line()
            self.stream.write(text + "\n")
            self.stream.flush()
            if bar is not None and bar.tty:
                bar.draw()
        except Exception:
            self.handleError(record)
