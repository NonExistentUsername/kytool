from __future__ import annotations

import abc
import logging
from copy import deepcopy
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from kytool.adapters import repository

logger = logging.getLogger(__name__)


class AbstractUnitOfWork(abc.ABC):
    """
    Abstract class for Unit of Work
    """

    def __enter__(self) -> AbstractUnitOfWork:
        """
        Enter Unit of Work

        Returns:
            AbstractUnitOfWork: Unit of Work
        """
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """
        Exit Unit of Work
        """
        if exc_type:
            self.rollback()
        else:
            self.commit()

    @abc.abstractmethod
    def commit(self):
        """
        Commit all changes made in this unit of work
        Raises:
            NotImplementedError: Not implemented
        """

        raise NotImplementedError

    @abc.abstractmethod
    def rollback(self):
        """
        Rollback all changes made in this unit of work

        Raises:
            NotImplementedError: Not implemented
        """

        raise NotImplementedError

    @abc.abstractmethod
    def collect_new_events(self):
        """
        Collects new events from the repositories.

        Yields:
            Any: The new events collected from the repositories.
        """

        raise NotImplementedError


_UOW = TypeVar("_UOW", bound=AbstractUnitOfWork)


class AbstractUnitOfWorkPool(abc.ABC, Generic[_UOW]):
    @abc.abstractmethod
    def get(self) -> _UOW:
        """
        Get Unit of Work

        Raises:
            NotImplementedError: Not implemented

        Returns:
            _UOW: Unit of Work
        """
        raise NotImplementedError
