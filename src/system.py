import os
import subprocess as sp
from time import sleep
from operations import UpdateAddress
from utils.state import State
from utils.watchdog import Watchdog
from utils.mode import Mode
from utils.funcs import get_active_slot, get_save_dirs, get_save_info, get_address

class SystemBase():
    _state: State
    _block_storage: str
    _mount_point: str
    _watchdog: Watchdog

    _address_port: int
    _address_cycle: int
    _address_interval: int

    _font: str

    def __init__(self, state: State, block_storage: str, mount_point: str, port: int, font: str) -> None:
        self._state = state
        self._block_storage = block_storage
        self._mount_point = mount_point
        self._watchdog = Watchdog(self._update_filesystem, self._update_idle, self._handle_operations)

        self._address_port = port
        self._address_cycle = 0
        self._address_interval = 30
        state.register("address", self._on_address_update)

        self._font = font

    def __enter__(self):
        self._set_mode(Mode.USB)
        self._watchdog.start()
        return self

    def __exit__(self, type, value, traceback):
        self._watchdog.kill()
        self._watchdog.join()
        return True

    def _update_saves(self, fs):
        loc = os.path.join(self._mount_point, "PS4")
        save_dirs = get_save_dirs(loc)
        fs["active_slot"] = get_active_slot(save_dirs)

        for save_dir in save_dirs:
            parts = save_dir.split(".")
            slot_id = fs["active_slot"] if len(parts) < 2 else parts[1]
            save_dir = os.path.join(loc, save_dir)

            name, description = get_save_info(save_dir)
            last_access = os.stat(save_dir).st_atime_ns

            fs["slots"][slot_id] = {
                "name": name.strip(),
                "description": description.strip(),
                "last_access": last_access
            }

    def _update_media(self, fs):
        current = self._state.read("filesystem")

        def browse(directory):
            if not os.path.isdir(directory):
                return
            for game in os.listdir(directory):
                game_dir = os.path.join(directory, game)
                for media in os.listdir(game_dir):
                    file_path = os.path.join(game_dir, media)
                    data = os.stat(file_path)
                    current_data = current["media"].get(media)
                    is_active = True if current_data is None else current_data["last_access"] != data.st_atime_ns

                    fs["media"][media] = {
                        "last_access": data.st_atime_ns,
                        "is_active": is_active,
                        "size": data.st_size,
                        "game": game,
                        "path": file_path,
                    }

        browse(os.path.join(self._mount_point, "PS5", "CREATE", "Video Clips"))

    def _is_address_up_to_date(self, address: str):
        loc = os.path.join(self._mount_point, "My Address")
        if not os.path.exists(loc):
            return False

        address_file = os.path.join(loc, "address.txt")

        if \
            not os.path.exists(address_file) or \
            not os.path.exists(os.path.join(loc, "address.png")) or \
            not os.path.exists(os.path.join(loc, "address_qr.png")):
            return False

        with open(address_file, mode="r") as f:
            return f.read() == address

    def _update_address(self):
        address = self._state.read("address")

        if self._address_cycle % self._address_interval == 0:
            actual = get_address()
            if address != actual:
                # call self._on_address_update callback by writing and return
                self._state.write("address", actual)
                self._address_cycle += 1
                return

        if not self._is_address_up_to_date(address):
            self._on_address_update(address)

        self._address_cycle += 1

    def _on_address_update(self, current: str):
        self._state.queue_operation(UpdateAddress(current, self._address_port, self._font))

    def _update_filesystem(self, remount=True) -> bool:
        if remount:
            # remount the fs to have it update
            self._umount()._mount(readonly=True)

        fs = {"slots": {}, "media": {}}
        self._update_saves(fs)
        self._update_media(fs)
        self._update_address()

        # return if the write happened, i.e. filesystem changed
        return self._state.write("filesystem", fs) or self._block_storage_written_to()

    def _update_idle(self, active: bool):
        self._state.write("fs_active", active)

    def _handle_operations(self):
        if len(self._state.read("operations")) == 0:
            return False

        self._set_mode(Mode.MANAGE)

        for op in self._state.pop_operations().values():
            print("#" * 3, f"Running operation: {op.overview}", flush=True)
            op.run(self._mount_point)

        fs_changed = self._update_filesystem(remount=False)
        self._set_mode(Mode.USB)

        return fs_changed

    def _set_mode(self, mode: Mode):
        if self._state.read("mode") == mode:
            return

        print("#" * 3, f"Setting mode to {mode}...", flush=True)

        if mode == Mode.USB:
            self._umount()._load_usb()._mount(readonly=True)
        elif mode == Mode.MANAGE:
            self._umount()._unload_usb()._mount(readonly=False)
        else:
            assert False, "Invalid mode"

        self._state.write("mode", mode)

    def _block_storage_written_to(self) -> bool:
        return False

    def _mount(self, readonly: bool) -> "SystemBase":
        print(f"Mounted {self._block_storage} under {self._mount_point} as readonly={readonly}", flush=True)
        return self

    def _umount(self) -> "SystemBase":
        print(f"Unmounted {self._mount_point}", flush=True)
        return self

    def _load_usb(self) -> "SystemBase":
        print(f"Loaded mass storage kernel module with file={self._block_storage}", flush=True)
        return self

    def _unload_usb(self) -> "SystemBase":
        print(f"Unloaded mass storage kernel module", flush=True)
        return self

class System(SystemBase):
    _last_modify_time = 0

    def _block_storage_written_to(self) -> bool:
        modify_time = os.stat(self._block_storage).st_ctime_ns

        result = self._last_modify_time != modify_time
        self._last_modify_time = modify_time

        return result

    def _mount(self, readonly: bool) -> SystemBase:
        mode = "ro" if readonly else "rw"
        sp.run(f"sudo mount -o defaults,loop,{mode} {self._block_storage} {self._mount_point}", shell=True)
        return super(System, self)._mount(readonly)

    def _umount(self) -> SystemBase:
        if os.path.ismount(self._mount_point):
            sp.run(f"sudo umount {self._mount_point}", shell=True)
        return super(System, self)._umount()

    def _load_usb(self) -> SystemBase:
        sp.run(f"sudo modprobe g_mass_storage file=\"{self._block_storage}\" removable=1 ro=0 stall=0", shell=True)
        return super(System, self)._load_usb()

    def _unload_usb(self) -> SystemBase:
        sp.run(f"sudo modprobe -r g_mass_storage", shell=True)
        return super(System, self)._unload_usb()

class SystemMock(SystemBase):
    def _mount(self, readonly: bool) -> SystemBase:
        sleep(.5)
        return super(SystemMock, self)._mount(readonly)

    def _umount(self) -> SystemBase:
        sleep(.5)
        return super(SystemMock, self)._umount()

    def _load_usb(self) -> SystemBase:
        sleep(.5)
        return super(SystemMock, self)._load_usb()

    def _unload_usb(self) -> SystemBase:
        sleep(.5)
        return super(SystemMock, self)._unload_usb()