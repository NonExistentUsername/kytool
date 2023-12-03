from typing import Callable, Dict, List, Type, Union

from kytool.domain import commands, events

EVENT_HANDLERS: Dict[Type[events.Event], List[Callable]] = {}
COMMAND_HANDLERS: Dict[Type[commands.Command], Callable] = {}

MessageType = Union[Type[commands.Command], Type[events.Event]]


def register_handler(message: MessageType) -> Callable:
    """
    Decorator for registering handlers for messages.

    Args:
        message (MessageType): The type of message to register a handler for.

    Returns:
        Callable: The decorator function.
    """

    def decorator(handler: Callable) -> Callable:
        """
        Decorator for registering handlers for messages.

        Args:
            handler (Callable): The handler function.

        Returns:
            Callable: The handler function.
        """
        if issubclass(message, events.Event):
            EVENT_HANDLERS.setdefault(message, []).append(handler)
        elif issubclass(message, commands.Command):
            COMMAND_HANDLERS[message] = handler
        else:
            raise ValueError(f"Invalid message type {message}")

        return handler

    return decorator
