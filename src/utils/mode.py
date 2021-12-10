from enum import Enum

class Mode(Enum):
    USB = 0
    MANAGE = 1

    def __str__(self) -> str:
        return "USB Mode" if self.value == 0 else "Manage Mode"

    @staticmethod
    def get(name) -> "Mode":
        for data in Mode:
            if name == str(data):
                return data
        return "Unknown Mode"