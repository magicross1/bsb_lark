from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.base_repository import BaseRepository


class BaseService(ABC):
    repository: BaseRepository

    def __init__(self, repository: BaseRepository) -> None:
        self.repository = repository
