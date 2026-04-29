from abc import ABC, abstractmethod


class EmailProvider(ABC):
    @abstractmethod
    def send(self, to: str, subject: str, body: str) -> bool: ...
