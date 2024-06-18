import time
from uuid import uuid4

import pytest

from kytool import factories
from kytool.adapters import repository
from kytool.domain import base, commands, events
from kytool.service_layer import handlers, messagebus, unit_of_work


class User(base.BaseModel):
    name: str

    def __init__(self, id: str, name: str):
        super().__init__()
        self.id = id
        self.name = name

    def __eq__(self, other):
        return self.id == other.id and self.name == other.name

    def __hash__(self) -> int:
        return super().__hash__()


class CreateUserCommand(commands.Command):
    name: str

    def __init__(self, name: str):
        super().__init__()
        self.name = name


class DeleteUserCommand(commands.Command):
    user_id: str

    def __init__(self, user_id: str):
        super().__init__()
        self.user_id = user_id


class UserCreatedEvent(events.Event):
    user_id: str
    name: str

    def __init__(self, user_id: str, name: str):
        super().__init__()
        self.user_id = user_id
        self.name = name


@handlers.register_handler(CreateUserCommand)
def create_user_handler(
    command: CreateUserCommand, uow: unit_of_work.BaseRepositoriesUnitOfWork
):
    with uow:
        instance = User(id=str(uuid4()), name=command.name)
        uow.r("users").add(instance=instance)
        uow.commit()

        return instance


@handlers.register_handler(DeleteUserCommand)
def delete_user_handler(
    command: DeleteUserCommand, uow: unit_of_work.BaseRepositoriesUnitOfWork
):
    with uow:
        instance = uow.r("users").delete(id=command.user_id)
        uow.commit()

        return instance


@handlers.register_handler(UserCreatedEvent)
def user_created_handler(
    event: UserCreatedEvent, uow: unit_of_work.BaseRepositoriesUnitOfWork
):
    with uow:
        instance = User(id=event.user_id, name=f"{event.name}copy")
        uow.r("users").add(instance=instance)
        uow.commit()

        return instance


@pytest.fixture
def uow_pool() -> unit_of_work.InMemoryUnitOfWorkPool:
    return unit_of_work.InMemoryUnitOfWorkPool(
        unit_of_work.InMemoryUnitOfWork(
            repositories=dict(users=repository.InMemoryRepository(query_fields=["id"]))
        )
    )


@pytest.fixture
def bus(uow_pool: unit_of_work.InMemoryUnitOfWorkPool) -> messagebus.MessageBus:
    return factories.create_message_bus(uow_pool=uow_pool)


class TestMessageBus:
    def test_command(
        self,
        bus: messagebus.MessageBus[unit_of_work.InMemoryUnitOfWorkPool],
    ):
        instance: User = bus.handle(CreateUserCommand(name="test"))

        assert instance.id is not None
        assert instance.name == "test"

        assert bus.uow_pool.get().r("users").get(id=instance.id) == instance

    def test_event(
        self, bus: messagebus.MessageBus[unit_of_work.InMemoryUnitOfWorkPool]
    ):
        event = UserCreatedEvent(user_id=str(uuid4()), name="test")

        assert isinstance(event, events.Event)

        bus.handle(event)

        time.sleep(0.01)

        instance: User = bus.uow_pool.get().r("users").get(id=event.user_id)  # type: ignore

        assert instance.id == event.user_id
        assert instance.name == "testcopy"

    def test_command_handler(
        self, bus: messagebus.MessageBus[unit_of_work.InMemoryUnitOfWorkPool]
    ):
        instance: User = bus.handle(CreateUserCommand(name="test"))

        assert instance.id is not None
        assert instance.name == "test"

        assert bus.uow_pool.get().r("users").get(id=instance.id) == instance

        instance = bus.handle(DeleteUserCommand(user_id=instance.id))

        assert instance.id is not None
        assert instance.name == "test"

        assert bus.uow_pool.get().r("users").get(id=instance.id) is None

    def test_force_background(
        self, bus: messagebus.MessageBus[unit_of_work.InMemoryUnitOfWorkPool]
    ):
        instance: User = bus.handle(CreateUserCommand(name="test"))

        assert instance.id is not None
        assert instance.name == "test"

        assert bus.uow_pool.get().r("users").get(id=instance.id) == instance

        async_task = bus.handle(
            DeleteUserCommand(user_id=instance.id), force_background=True
        )
        instance = async_task.get()

        assert instance is not None

        time.sleep(0.01)

        assert bus.uow_pool.get().r("users").get(id=instance.id) is None
