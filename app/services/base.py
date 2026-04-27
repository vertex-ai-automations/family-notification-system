from abc import ABC, abstractmethod
from typing import List, Optional

class NotificationService(ABC):
    name: str
    enabled: bool = True
    # Set by send() — read by the caller to log error detail or skip log row entirely.
    last_error: Optional[str] = None
    last_skip: bool = False

    @abstractmethod
    def send(self, person: dict, message: str, **context) -> bool:
        ...

    @abstractmethod
    def health_check(self) -> bool:
        ...

    def _reset(self):
        self.last_error = None
        self.last_skip = False

class ServiceRegistry:
    def __init__(self, services: List[NotificationService]):
        self._services = services

    def get_enabled(self) -> List[NotificationService]:
        return [s for s in self._services if s.enabled]

    def get_all(self) -> List[NotificationService]:
        return self._services
