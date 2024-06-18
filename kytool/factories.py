from typing import Callable, List, Optional, Type

from kytool import di
from kytool.adapters import repository
from kytool.domain import commands, events
from kytool.service_layer import handlers, messagebus, unit_of_work


def create_uow(uow_type: str) -> unit_of_work.AbstractUnitOfWork:
    if uow_type == "ram":
        return unit_of_work.InMemoryUnitOfWork(
            {
                "default": repository.InMemoryRepository(
                    query_fields=["id", "username", "email"]
                )
            }
        )

    raise ValueError(f"Unknown uow_type: {uow_type}")


def create_message_bus(
    uow_pool: Optional[unit_of_work.AbstractUnitOfWorkPool] = None,
    event_handlers: dict[Type[events.Event], List[Callable]] = handlers.EVENT_HANDLERS,
    command_handlers: dict[
        Type[commands.Command], Callable
    ] = handlers.COMMAND_HANDLERS,
    dependencies: Optional[dict[str, object]] = None,
    background_threads: int = 1,
) -> messagebus.MessageBus:
    """
    Create message bus

    Args:
        uow (Optional[unit_of_work.AbstractUnitOfWorkPool]): Unit of work pool. When None is passed, \
            FakeUnitOfWorkPool is used. Defaults to None.

    Returns:
        messagebus.MessageBus: Message bus
    """
    if not dependencies:
        dependencies = {}

    if not uow_pool:
        uow_pool = unit_of_work.FakeUnitOfWorkPool()

    injected_command_handlers = {
        command: di.inject_dependencies(handler, dependencies)
        for command, handler in command_handlers.items()
    }
    injected_event_handlers = {
        event: [
            di.inject_dependencies(handler, dependencies) for handler in handlers_list
        ]
        for event, handlers_list in event_handlers.items()
    }

    return messagebus.MessageBus(
        uow_pool=uow_pool,
        event_handlers=injected_event_handlers,
        command_handlers=injected_command_handlers,
        background_threads=background_threads,
    )
