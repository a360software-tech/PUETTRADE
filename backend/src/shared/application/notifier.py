from collections.abc import Callable
from threading import Lock
from typing import Generic, TypeVar
from uuid import uuid4


EventT = TypeVar("EventT")


class EventNotifier(Generic[EventT]):
    def __init__(self) -> None:
        self._listeners: dict[str, Callable[[EventT], None]] = {}
        self._lock = Lock()

    def register(self, listener: Callable[[EventT], None]) -> str:
        listener_id = str(uuid4())
        with self._lock:
            self._listeners[listener_id] = listener
        return listener_id

    def unregister(self, listener_id: str) -> None:
        with self._lock:
            self._listeners.pop(listener_id, None)

    def notify(self, event: EventT) -> None:
        with self._lock:
            listeners = list(self._listeners.values())
        for listener in listeners:
            listener(event)
