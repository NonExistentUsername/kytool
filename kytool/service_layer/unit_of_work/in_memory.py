import logging
from copy import deepcopy
from typing import Dict

from kytool.adapters import repository
from kytool.service_layer.unit_of_work.interfaces import (
    AbstractUnitOfWork,
    AbstractUnitOfWorkPool,
)

logger = logging.getLogger(__name__)


class BaseRepositoriesUnitOfWork(AbstractUnitOfWork):
    """
    Base Unit of Work that does nothing
    """

    def __init__(self, repositories: Dict[str, repository.AbstractRepository]):
        super().__init__()
        self.repositories = repositories

    def r(self, key: str) -> repository.AbstractRepository:
        """
        Get repository

        Args:
            key (str): Repository key

        Returns:
            repository.AbstractRepository: Repository
        """

        return self.repositories[key]

    def rollback(self):
        """
        Rollback all changes made in this unit of work
        """

        pass

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


class InMemoryUnitOfWork(BaseRepositoriesUnitOfWork):
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

    def commit(self):
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


class InMemoryUnitOfWorkPool(AbstractUnitOfWorkPool[InMemoryUnitOfWork]):
    def __init__(self, uow: InMemoryUnitOfWork):
        """
        Not thread-safe Unit of Work Pool

        Supposed to be used for testing purposes

        Args:
            uow (InMemoryUnitOfWork): Unit of Work
        """
        super().__init__()
        self.uow = uow

    def get(self) -> InMemoryUnitOfWork:
        """
        Get Unit of Work

        Returns:
            InMemoryUnitOfWork: Unit of Work
        """
        return self.uow
