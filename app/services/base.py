from abc import ABC, abstractmethod
from typing import List

class NotificationService(ABC):
    name: str
    enabled: bool = True

    @abstractmethod
    def send(self, person: dict, message: str) -> bool:
        ...

    @abstractmethod
    def health_check(self) -> bool:
        ...

class ServiceRegistry:
    def __init__(self, services: List[NotificationService]):
        self._services = services

    def get_enabled(self) -> List[NotificationService]:
        return [s for s in self._services if s.enabled]

    def get_all(self) -> List[NotificationService]:
        return self._services
