from __future__ import annotations

import abc
import logging
from copy import deepcopy
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from kytool.adapters import repository

logger = logging.getLogger(__name__)


class AbstractUnitOfWork(abc.ABC):
    """
    Abstract class for Unit of Work
    """

    def __init__(
        self,
        repositories: Dict[str, repository.AbstractRepository],
    ):
        """
        Initializes a UnitOfWork object.

        Args:
            repositories (Dict[str, repository.AbstractRepository]): A dictionary of repository objects.
        """
        self.repositories: Dict[str, repository.AbstractRepository] = repositories

    def __enter__(self) -> AbstractUnitOfWork:
        """
        Enter Unit of Work

        Returns:
            AbstractUnitOfWork: Unit of Work
        """

        return self

    def __exit__(self, *args):
        """
        Exit Unit of Work
        """

        self.rollback()

    def commit(self):
        """
        Commit all changes made in this unit of work
        """

        self._commit()

    def r(self, key: str) -> repository.AbstractRepository:
        """
        Get repository

        Args:
            key (str): Repository key

        Returns:
            repository.AbstractRepository: Repository
        """

        return self.repositories[key]

    def collect_new_events(self):
        """
        Collects new events from the repositories.

        Yields:
            Any: The new events collected from the repositories.
        """
        for repository in self.repositories.values():
            for instance in repository.seen:
                if hasattr(instance, "events") and isinstance(instance.events, list):
                    while instance.events:
                        yield instance.events.pop(0)

    @abc.abstractmethod
    def _commit(self):
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


class InMemoryUnitOfWork(AbstractUnitOfWork):
    """
    Unit of Work that stores all changes in RAM
    """

    def __init__(
        self,
        repositories: Dict[str, repository.AbstractRepository],
    ):
        """
        Initialize InMemoryUnitOfWork

        Args:
            users (repository.AbstractRepository): Users repository
        """

        super().__init__(repositories=repositories)

        self._last_committed = deepcopy(self.repositories)

    def _commit(self):
        """
        Commit all changes made in this unit of work
        """

        logger.debug("Commiting changes in InMemoryUnitOfWork")

        self._last_committed = deepcopy(self.repositories)

    def rollback(self):
        """
        Rollback all changes made in this unit of work
        """

        logger.debug("Rolling back changes in InMemoryUnitOfWork")

        self.repositories = self._last_committed
