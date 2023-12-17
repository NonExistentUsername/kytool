from __future__ import annotations

import logging
import multiprocessing.pool
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Type, Union

from kytool.domain import commands, events

if TYPE_CHECKING:
    from . import unit_of_work

logger = logging.getLogger(__name__)

Message = Union[commands.Command, events.Event]


class MessageBus:
    """
    A message bus that handles messages, which can be either events or commands.

    Args:
        uow (unit_of_work.AbstractUnitOfWork): The unit of work to \
use for handling messages.
        event_handlers (Dict[events.Event, list[Callable]]): A dictionary mapping \
events to their handlers.
        command_handlers (Dict[commands.Command, Callable]): A dictionary mapping \
commands to their handlers.
        background_threads (int, optional): The number of background threads \
to use for handling messages. Defaults to 1.
    """

    def __init__(
        self,
        uow: unit_of_work.AbstractUnitOfWork,
        event_handlers: Dict[Type[events.Event], list[Callable]],
        command_handlers: Dict[Type[commands.Command], Callable],
        background_threads: int = 1,
    ):
        """
        Initialize message bus

        Args:
            uow (unit_of_work.AbstractUnitOfWork): _description_
            event_handlers (Dict[events.Event, list[Callable]]): _description_
            command_handlers (Dict[commands.Command, Callable]): _description_
            background_threads (int, optional): _description_. Defaults to 1.
        """

        self.uow: unit_of_work.AbstractUnitOfWork = uow
        self.event_handlers: Dict[Type[events.Event], list[Callable]] = event_handlers
        self.command_handlers: Dict[Type[commands.Command], Callable] = command_handlers
        self.pool = multiprocessing.pool.ThreadPool(background_threads)

    def handle(self, message: Message) -> Any:
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
            return self._handle_command(message)

        raise ValueError(f"{message} is not Event or Command")

    def _collect_new_events(self) -> None:
        """
        Collect all new events from all instances in the repository
        """

        for event in self.uow.collect_new_events():
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

        result = handler(command)

        self.pool.apply_async(self._collect_new_events)

        return result

    def _handle_event(self, event: events.Event) -> None:
        """
        Handles an event by invoking the corresponding event handler.

        Args:
            event (events.Event): The event to be handled.

        """

        for handler in self.event_handlers[type(event)]:
            handler(event)

        self._collect_new_events()
