"""
Module that holds the ``__models__`` list for Tortoise ORM model discovery.

When Tortoise ``init()`` scans this module, it will use the ``__models__``
list instead of trying to discover ``Model`` subclasses via module inspection.
The list is populated during ``AppConfig.ready()`` by the model generator.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tortoise import models

__models__: list[type[models.Model]] = []
