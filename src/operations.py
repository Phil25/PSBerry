import os
import shutil
import qrcode
from PIL import Image, ImageDraw, ImageFont
from copy import deepcopy
from typing import List
from drivers import DriverBase
from utils.state import OperationBase
from utils.funcs import get_active_slot, get_save_dirs

def _rename_save(loc, current: str, desired: str):
    current = os.path.join(loc, current)
    if os.path.exists(current):
        os.rename(current, os.path.join(loc, desired))

def _delete_save(loc, save):
    directory = os.path.join(loc, save)
    if os.path.exists(directory):
        shutil.rmtree(directory)

def _get_slot_int(slot_id: str) -> int:
    assert "_" in slot_id
    parts = slot_id.split("_")
    assert len(parts) == 2
    return int(parts[1])

class ChangeSlot(OperationBase):
    _next: str

    def __init__(self, slot_id: str) -> None:
        super().__init__()
        assert "Slot_" in slot_id
        self._next = slot_id

    @property
    def overview(self) -> str:
        return f"Changing to slot \"{self._next}\"."

    @property
    def slot_id(self) -> str:
        return self._next

    def run(self, mount_point: str):
        loc = os.path.join(mount_point, "PS4")
        current = get_active_slot(get_save_dirs(loc))

        if current != self._next:
            _rename_save(loc, "SAVEDATA", f"SAVEDATA.{current}")
            _rename_save(loc, f"SAVEDATA.{self._next}", "SAVEDATA")

class EditSlot(OperationBase):
    _slot_id: str
    _name: str
    _description: str

    def __init__(self, slot_id: str, name: str, description: str) -> None:
        super().__init__()
        assert "Slot_" in slot_id
        self._slot_id = slot_id
        self._name = name.strip()
        self._description = description.strip()

    @property
    def overview(self) -> str:
        return f"Editing slot \"{self._slot_id}\" to name=\"{self._name}\", description=\"{self._description}\"."

    def run(self, mount_point: str):
        loc = os.path.join(mount_point, "PS4")
        slot_dirs = get_save_dirs(loc)
        slot_dir = f"SAVEDATA.{self._slot_id}"

        if slot_dir not in slot_dirs:
            if self._slot_id != get_active_slot(slot_dirs):
                return # our slot dir was deleted
            slot_dir = "SAVEDATA" # slot is the active one

        with open(os.path.join(loc, slot_dir, "meta.txt"), "w") as f:
            f.write(f"{self._name}\n{self._description}")

class DeleteSlot(OperationBase):
    _id: int

    def __init__(self, slot_id: str) -> None:
        super().__init__()
        assert "Slot_" in slot_id
        self._id = _get_slot_int(slot_id)

    @property
    def overview(self) -> str:
        return f"Deleting slot \"Slot_{self._id}\"."

    @property
    def slot_id(self) -> str:
        return f"Slot_{self._id}"

    def run(self, mount_point: str):
        loc = os.path.join(mount_point, "PS4")
        slot_dirs = get_save_dirs(loc)

        active_slot = get_active_slot(slot_dirs)
        next_active_int = None

        if active_slot is not None:
            _rename_save(loc, "SAVEDATA", f"SAVEDATA.{active_slot}")
            next_active_int = _get_slot_int(active_slot)
            if next_active_int == self._id:
                next_active_int = None
            elif next_active_int > self._id:
                next_active_int -= 1

        # slot_dirs now contains sorted list of SAVEDATA.x with none active
        slot_dirs = sorted(get_save_dirs(loc))
        _delete_save(loc, f"SAVEDATA.Slot_{self._id}")

        if len(slot_dirs) > 1:
            # This loop will causes issues in case power is lost at the exact wrong time
            for i in range(self._id + 1, len(slot_dirs) + 1):
                _rename_save(loc, f"SAVEDATA.Slot_{i}", f"SAVEDATA.Slot_{i - 1}")

        if next_active_int is not None:
            _rename_save(loc, f"SAVEDATA.Slot_{next_active_int}", "SAVEDATA")

class CreateSlot(OperationBase):
    _clone_active: bool

    def __init__(self, clone_active: bool) -> None:
        super().__init__()
        self._clone_active = clone_active

    @property
    def overview(self) -> str:
        return "Creating a new slot." if self._clone_active else "Cloning selected slot."

    @property
    def clone_active(self) -> bool:
        return self._clone_active

    def run(self, mount_point: str):
        loc = os.path.join(mount_point, "PS4")

        if not os.path.exists(loc):
            os.mkdir(loc)

        slot_count = len(get_save_dirs(loc))
        slot_id = f"Slot_{slot_count + 1}"

        savedata = os.path.join(loc, f"SAVEDATA.{slot_id}")
        assert not os.path.exists(savedata)

        if self._clone_active:
            active = os.path.join(loc, "SAVEDATA")
            if os.path.exists(active):
                shutil.copytree(active, savedata)
        else:
            os.mkdir(savedata)

class TransferFiles(OperationBase):
    _drivers: List[DriverBase]

    def __init__(self, media, drivers: List[DriverBase], listener) -> None:
        super().__init__()
        assert len(media), "Media count cannot be zero"
        assert len(drivers), "Driver count cannot be zero"
        self._media = media
        self._drivers = drivers
        self._listener = listener

    @property
    def overview(self) -> str:
        count = len(self._media)
        detail = f"{count} files" if count > 1 else f"file \"{list(self._media)[0]}\""
        return f"Transferring {detail} to the specified remotes."

    def run(self, mount_point: str):
        # TODO: parallelize by driver and file
        for name, data in self._media.items():
            path = data["path"]
            success = True

            for driver in self._drivers:
                success = success and driver.upload(path, name, self._listener)
                self._listener.set_media_action(name, "")

            if success:
                os.remove(path)

    # prevent deepcopy of self._listener property, because it contains
    # an instance of a remi GUI object which is not deepcopyable
    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            setattr(result, k, v if k == "_listener" else deepcopy(v, memo))
        return result

class UpdateAddress(OperationBase):
    _SIZE = 64

    _address: str
    _port: int
    _font: str

    def __init__(self, address: str, port: int, font: str) -> None:
        super().__init__()
        self._address = address
        self._port = port
        self._font = font

    @property
    def overview(self) -> str:
        return f"Updating address to \"{self._address}\"."

    def run(self, mount_point: str):
        loc = os.path.join(mount_point, "My Address")

        if not os.path.exists(loc):
            os.mkdir(loc)

        with open(os.path.join(loc, "address.txt"), mode="w") as f:
            f.write(self._address)

        font = ImageFont.truetype(self._font, self._SIZE - 4)
        width = self._SIZE * 10

        img = Image.new("L", (width, self._SIZE), color=255)
        draw = ImageDraw.Draw(img)
        w, _ = draw.textsize(self._address, font)

        draw.text(((width - w) / 2, 0), self._address, "black", font)
        img.save(os.path.join(loc, "address.png"))

        qrcode \
            .make(f"http://{self._address}:{self._port}") \
            .save(os.path.join(loc, "address_qr.png"))