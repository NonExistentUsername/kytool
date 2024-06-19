from kytool.service_layer.unit_of_work.interfaces import (
    AbstractUnitOfWork,
    AbstractUnitOfWorkPool,
)


class FakeUnitOfWork(AbstractUnitOfWork):
    def __init__(self):
        super().__init__()

    def rollback(self):
        pass

    def collect_new_events(self):
        return []

    def commit(self):
        pass


class FakeUnitOfWorkPool(AbstractUnitOfWorkPool[FakeUnitOfWork]):
    def __init__(self):
        super().__init__()

    def get(self) -> FakeUnitOfWork:
        return FakeUnitOfWork()
