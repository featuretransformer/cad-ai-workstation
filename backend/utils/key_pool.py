"""
API Key Pool & Cooldown Manager for resilient multi-key LLM inference.
Distributes load across multiple API keys in round-robin fashion and dynamically
quarantines keys on 429 rate-limit errors until their cooldown period expires.
"""
import time
import re
import threading
from typing import List, Optional, Dict, Any


class APIKeyPool:
    def __init__(self, provider_name: str, keys: Optional[List[str]] = None):
        self.provider_name = provider_name
        self.keys: List[str] = [k for k in (keys or []) if k]
        self.cooldowns: Dict[str, float] = {}  # key -> timestamp until available
        self._lock = threading.Lock()
        self._index = 0

    def set_keys(self, keys: List[str]):
        """Updates the pool with a new list of keys."""
        with self._lock:
            for k in keys:
                if k and k not in self.keys:
                    self.keys.append(k)

    def get_next_key(self) -> Optional[str]:
        """
        Returns the next available key in round-robin order.
        Skips any keys currently in cooldown.
        Returns None if all keys are currently cooling down or pool is empty.
        """
        with self._lock:
            if not self.keys:
                return None

            now = time.time()
            n = len(self.keys)
            for _ in range(n):
                candidate = self.keys[self._index % n]
                self._index = (self._index + 1) % n
                cooldown_until = self.cooldowns.get(candidate, 0.0)
                if now >= cooldown_until:
                    return candidate

            return None

    def get_earliest_cooldown_remaining(self) -> float:
        """Returns seconds until the earliest key exits cooldown."""
        with self._lock:
            if not self.keys:
                return 0.0
            now = time.time()
            remaining = [max(0.0, self.cooldowns.get(k, 0.0) - now) for k in self.keys]
            return min(remaining) if remaining else 0.0

    def mark_rate_limited(self, key: str, retry_after: Optional[float] = None, error_message: str = ""):
        """
        Quarantines a key on rate-limit errors (429/OTPM).
        Automatically parses retry duration from error text if present.
        """
        with self._lock:
            duration = retry_after
            if duration is None and error_message:
                match = re.search(r"try again in (\d+(?:\.\d+)?)\s*s", error_message, re.IGNORECASE)
                if match:
                    try:
                        duration = float(match.group(1)) + 1.5
                    except Exception:
                        pass

            if duration is None or duration <= 0:
                duration = 30.0  # default cooldown

            self.cooldowns[key] = time.time() + duration
            masked = f"...{key[-6:]}" if len(key) >= 6 else "***"
            print(
                f"[{self.provider_name.upper()} KEY POOL] Key {masked} rate-limited. "
                f"Cooldown active for {duration:.1f}s. Rotating to next key..."
            )

    def mark_success(self, key: str):
        """Clears expired cooldown records."""
        with self._lock:
            if key in self.cooldowns and self.cooldowns[key] <= time.time():
                del self.cooldowns[key]

    def has_keys(self) -> bool:
        """True if pool has at least one configured key."""
        return len(self.keys) > 0

    def status(self) -> Dict[str, Any]:
        """Returns diagnostic info about key availability."""
        now = time.time()
        available = sum(1 for k in self.keys if self.cooldowns.get(k, 0.0) <= now)
        return {
            "provider": self.provider_name,
            "total_keys": len(self.keys),
            "available_keys": available,
            "cooling_keys": len(self.keys) - available,
        }
