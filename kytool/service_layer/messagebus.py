from __future__ import annotations

import inspect
import logging
import multiprocessing.pool
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generic,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from kytool.domain import commands, events
from kytool.service_layer.unit_of_work import AbstractUnitOfWork, AbstractUnitOfWorkPool

if TYPE_CHECKING:
    from . import unit_of_work

logger = logging.getLogger(__name__)

Message = Union[commands.Command, events.Event]
_UOW = TypeVar("_UOW", bound=AbstractUnitOfWorkPool)


class MessageBus(Generic[_UOW]):
    """
    A message bus that handles messages, which can be either events or commands.
    """

    def _inject_uow(self, handler: Callable) -> Callable:
        def wrapper(message: Message) -> Any:
            uow = self.uow_pool.get()
            result = handler(message, uow=uow)
            return uow, result

        if inspect.signature(handler).parameters.get("uow"):
            return wrapper
        else:
            return lambda message: (None, handler(message))

    def _get_injected_command_handlers(
        self, command_handlers: Dict[Type[commands.Command], Callable]
    ) -> Dict[Type[commands.Command], Callable]:
        return {
            command: self._inject_uow(handler)
            for command, handler in command_handlers.items()
        }

    def _get_injected_event_handlers(
        self, event_handlers: Dict[Type[events.Event], list[Callable]]
    ) -> Dict[Type[events.Event], list[Callable]]:
        return {
            event: [self._inject_uow(handler) for handler in handlers_list]
            for event, handlers_list in event_handlers.items()
        }

    def __init__(
        self,
        uow_pool: _UOW,
        event_handlers: Dict[Type[events.Event], list[Callable]],
        command_handlers: Dict[Type[commands.Command], Callable],
        background_threads: int = 1,
    ):
        """
        Initialize message bus

        Args:
            uow_pool (_UOW): Unit of work pool
            event_handlers (Dict[events.Event, list[Callable]]): Event handlers
            command_handlers (Dict[commands.Command, Callable]): Command handlers
            background_threads (int, optional): Number of background threads. Defaults to 1.
        """

        self.uow_pool: _UOW = uow_pool
        self.event_handlers: Dict[
            Type[events.Event], list[Callable]
        ] = self._get_injected_event_handlers(event_handlers=event_handlers)
        self.command_handlers: Dict[
            Type[commands.Command], Callable
        ] = self._get_injected_command_handlers(command_handlers=command_handlers)
        self.pool = multiprocessing.pool.ThreadPool(background_threads)

    def handle(self, message: Message, force_background=False) -> Any:
        """
        Handle message

        Args:
            message (Message): Message to handle. It can be either Event or Command

        Raises:
            ValueError: If message is not Event or Command
        """
        if isinstance(message, events.Event):
            self.pool.apply_async(self._handle_event, (message,))
            return None

        if isinstance(message, commands.Command):
            if force_background:
                return self.pool.apply_async(self._handle_command, (message,))

            return self._handle_command(message)

        raise ValueError(f"{message} is not Event or Command")

    def _collect_new_events(self, uow: AbstractUnitOfWork) -> None:
        """
        Collect all new events from all instances in the repository
        """

        for event in uow.collect_new_events():
            self.handle(event)

    def _handle_with_profiling(self, message: Message) -> Any:
        """
        Handle message with profiling

        Args:
            message (Message): Message to handle. It can be either Event or Command
        """
        import cProfile

        pr = cProfile.Profile()
        pr.enable()
        result = self._handle(message)
        pr.disable()
        pr.print_stats(sort="time")

        return result

    def _handle(self, message: Message) -> Any:
        """
        Handle message

        Args:
            message (Message): Message to handle. It can be either Event or Command

        Returns:
            Any: Result of handling message
        """

        if isinstance(message, commands.Command):
            return self._handle_command(message)

        return self._handle_event(message)

    def _handle_command(self, command: commands.Command) -> Any:
        """
        Handles a command by invoking the corresponding command handler.

        Args:
            command (commands.Command): The command to be handled.

        Returns:
            Any: The result of handling the command.

        """
        handler = self.command_handlers[type(command)]

        uow, result = handler(command)

        if uow:
            self.pool.apply_async(self._collect_new_events)

        return result

    def _handle_event(self, event: events.Event) -> None:
        """
        Handles an event by invoking the corresponding event handler.

        Args:
            event (events.Event): The event to be handled.

        """

        for handler in self.event_handlers[type(event)]:
            uow, _ = handler(event)
            self._collect_new_events(uow=uow)
