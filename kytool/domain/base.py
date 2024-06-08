from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kytool.domain.events import Event


class BaseModel:
    """
    Base class for all models in the system.

    Attributes:
        id (str): The unique identifier for the model.
        events (list[Event]): A list of events associated with the model.
    """

    def __init__(self):
        """
        Initializes a new instance of the Base class.
        """
        self.events: list[Event] = []
