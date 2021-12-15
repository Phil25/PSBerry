from threading import Lock
from copy import deepcopy
from typing import Dict

"""
Expected operations:
- DeleteFile
- ChangeSlot
- CreateSlot
- DeleteSlot
- EditSlot
"""
class OperationBase():
    @property
    def overview(self) -> str:
        return "No operation overview..."

    def run(self, mount_point: str):
        assert False, "Operation not defined"

class State():
    def __init__(self) -> None:
        self._lock = Lock()
        self._data = {"operations": {}, "filesystem": {"slots": {}, "active_slot": "", "media": {}}, "drivers": []}
        self._listeners = {}

    def _call_listeners(self, field: str, value):
        for callback in self._listeners.get(field, []):
            callback(value)

    def read(self, field):
        with self._lock:
            return self._data.get(field)

    def write(self, field: str, value):
        with self._lock:
            if self._data.get(field) == value:
                return False

            self._data[field] = value

        self._call_listeners(field, value)
        return True

    def register(self, field: str, callback):
        with self._lock:
            if field not in self._listeners:
                self._listeners[field] = []
            self._listeners[field].append(callback)

    def queue_operation(self, op: OperationBase):
        with self._lock:
            assert "operations" in self._data

            self._data["operations"][type(op).__name__] = op
            data = deepcopy(self._data["operations"])

        self._call_listeners("operations", data)

    def pop_operations(self) -> Dict[str, OperationBase]:
        with self._lock:
            assert "operations" in self._data

            ops = self._data.pop("operations")
            self._data["operations"] = {} # add it right back

        self._call_listeners("operations", {})
        return ops