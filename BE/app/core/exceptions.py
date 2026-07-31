from dataclasses import dataclass, field
from typing import Any


@dataclass
class DomainError(Exception):
    code: str
    message: str
    status_code: int = 400
    details: list[dict[str, Any]] = field(default_factory=list)

    def __str__(self) -> str:
        return self.message
