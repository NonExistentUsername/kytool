import contextlib

import pytest

from kytool.adapters import repository
from kytool.service_layer import unit_of_work


class SampleObject:
    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name

    def __repr__(self):
        return f"SampleObject(id={self.id}, name={self.name})"

    def __eq__(self, __value: object) -> bool:
        return (
            isinstance(__value, SampleObject)
            and self.id == __value.id
            and self.name == __value.name
        )

    def __hash__(self) -> int:
        return hash(self.id)


@pytest.fixture
def uow() -> unit_of_work.InMemoryUnitOfWork:
    return unit_of_work.InMemoryUnitOfWork(
        repositories=dict(users=repository.InMemoryRepository(query_fields=["id"]))
    )


@pytest.fixture
def fake_uow() -> unit_of_work.FakeUnitOfWork:
    return unit_of_work.FakeUnitOfWork()


@pytest.fixture
def fake_uow_pool() -> unit_of_work.FakeUnitOfWorkPool:
    return unit_of_work.FakeUnitOfWorkPool()


class TestRamUOWCreation:
    def test_works(self, uow: unit_of_work.InMemoryUnitOfWork):
        with uow:
            uow.r("users").add(SampleObject(id="123", name="test"))
            uow.commit()

        assert uow.r("users").get(id="123") == SampleObject(id="123", name="test")

        with uow:
            instances = uow.r("users").delete(id="123")
            uow.commit()

            assert instances == [SampleObject(id="123", name="test")]

        assert uow.r("users").get(id="123") is None

    def test_rolls_back(self, uow: unit_of_work.InMemoryUnitOfWork):
        with uow:
            uow.r("users").add(SampleObject(id="123", name="test"))

        assert uow.r("users").get(id="123") is not None

    def test_rolls_back_if_exception(self, uow: unit_of_work.InMemoryUnitOfWork):
        with contextlib.suppress(Exception):
            with uow:
                uow.r("users").add(SampleObject(id="123", name="test"))
                raise ValueError("test")

        assert uow.r("users").get(id="123") is None


class TestFakeUOW:
    def test_works(self, fake_uow: unit_of_work.FakeUnitOfWork):
        with fake_uow:
            fake_uow.commit()

        with fake_uow:
            pass

        with contextlib.suppress(Exception):
            with fake_uow:
                raise ValueError("test")

    def test_pool_works(self, fake_uow_pool: unit_of_work.FakeUnitOfWorkPool):
        with fake_uow_pool.get() as uow:
            uow.commit()

        with fake_uow_pool.get() as uow:
            pass

        with contextlib.suppress(Exception):
            with fake_uow_pool.get() as uow:
                raise ValueError("test")

        assert fake_uow_pool.get() is not None
        assert isinstance(fake_uow_pool.get(), unit_of_work.FakeUnitOfWork)
