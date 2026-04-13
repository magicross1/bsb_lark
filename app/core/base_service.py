from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.common.lark_repository import BaseRepository


class BaseService(ABC):
    repository: BaseRepository

    def __init__(self, repository: BaseRepository) -> None:
        self.repository = repository
