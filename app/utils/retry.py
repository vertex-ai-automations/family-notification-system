import logging
import time
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

def with_retry(fn: Callable[[], T], *, attempts: int = 3, base_delay: float = 0.5, label: str = "send") -> T:
    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            if i < attempts - 1:
                delay = base_delay * (2 ** i)
                logger.info("%s attempt %d/%d failed: %s — retrying in %.1fs", label, i + 1, attempts, e, delay)
                time.sleep(delay)
    raise last_exc  # type: ignore[misc]
