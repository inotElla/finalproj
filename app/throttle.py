import threading
import time


class AttemptLimiter:
    """Counts failed attempts per key (for example "ip|email") inside a time window.

    After `max_attempts` failures the key is blocked until the oldest failure falls
    out of the window. This slows down someone guessing passwords.

    The counts live in this program's memory. That is fine for one server process
    (your laptop, or Render's free plan). With several processes each would count
    separately, and a restart clears the counts."""

    def __init__(self, max_attempts, window_seconds):
        self.max_attempts = max_attempts
        self.window = window_seconds
        self._failures = {}  # key -> list of timestamps
        self._lock = threading.Lock()  # two requests may touch the dict at once

    def _recent(self, key, now):
        # Keep only the failures that are still inside the window.
        recent = [t for t in self._failures.get(key, []) if now - t < self.window]
        if recent:
            self._failures[key] = recent
        else:
            self._failures.pop(key, None)
        return recent

    def is_blocked(self, key):
        with self._lock:
            return len(self._recent(key, time.time())) >= self.max_attempts

    def record(self, key):
        """Write down one failed attempt."""
        with self._lock:
            now = time.time()
            self._recent(key, now)
            self._failures.setdefault(key, []).append(now)

    def reset(self, key):
        """Forget the failures (after a successful login)."""
        with self._lock:
            self._failures.pop(key, None)

    def minutes_left(self, key):
        """Whole minutes until the key is allowed to try again (at least 1)."""
        with self._lock:
            now = time.time()
            recent = self._recent(key, now)
            if not recent:
                return 0
            return max(1, int((min(recent) + self.window - now) // 60) + 1)


# Shared by the routes: 5 wrong logins in 10 minutes, 5 reset requests in an hour.
login_limiter = AttemptLimiter(max_attempts=5, window_seconds=10 * 60)
reset_limiter = AttemptLimiter(max_attempts=5, window_seconds=60 * 60)
