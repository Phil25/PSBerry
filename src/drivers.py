import os
import re
import hashlib
from typing import Dict, List, Tuple
import smbclient as smb

_EMPTY_DRIVER = "None (removes driver)"

class DriverBase():
    _config: Dict

    empty_driver = _EMPTY_DRIVER
    description = "No driver implementation provided."
    fields = []

    def __init__(self, config: Dict) -> None:
        self._config = dict(config, **{"__description__": self.description})

    def upload(self, source: str, filename: str, listener) -> bool:
        return False

    @property
    def error(self) -> str:
        return "No driver implementation provided."

    @property
    def config(self):
        return self._config

    @classmethod
    def get_descriptions(cls):
        return [c.description for c in cls.__subclasses__()]

    @classmethod
    def get_fields(cls, description: str) -> List[Tuple[str, str]]:
        for c in cls.__subclasses__():
            if c.description == description:
                return c.fields
        assert False, f"Invalid description: \"{description}\"."

    @classmethod
    def from_description(cls, description: str, config: Dict) -> "DriverBase":
        if description == _EMPTY_DRIVER:
            return None

        for c in cls.__subclasses__():
            if c.description == description:
                return c(config)

        assert False, f"Invalid description: \"{description}\"."

    @classmethod
    def from_configs(cls, configs: List[Dict]) -> List["DriverBase"]:
        drivers = [cls.from_description(c["__description__"], c) for c in configs]
        return [d for d in drivers if d is not None]


class DriverRemover(DriverBase):
    description = _EMPTY_DRIVER


class DriverSMB(DriverBase):
    _remote_root: str
    _chunk_size: int

    description = "SMB/Samba server"
    fields = [
        ("remote", "text"),
        ("folder", "text"),
        ("username", "text"),
        ("password", "password"),
    ]

    def __init__(self, config: Dict) -> None:
        super().__init__(config)
        remote, folder, username, password = config["remote"], config["folder"], config["username"], config["password"]
        self._remote_root = fr"\\{remote}\{folder}"
        self._chunk_size = 8192
        smb.register_session(remote, username=username, password=password)

    def upload(self, source: str, filename: str, listener) -> bool:
        listener.set_media_size(filename, os.stat(source).st_size)
        effective_file = re.sub(r"[^\w\-_\. ]", "_", filename)
        destination = fr"{self._remote_root}\{effective_file}"

        hash_src = hashlib.md5()
        hash_dst = hashlib.md5()
        listener.set_media_action(filename, f"Uploading to {self._remote_root}...")

        with open(source, mode="rb") as src:
            with smb.open_file(destination, mode="wb") as dst:
                copied_bytes = 0
                while chunk := src.read(self._chunk_size):
                    dst.write(chunk)
                    hash_src.update(chunk)
                    copied_bytes += len(chunk)
                    listener.set_media_progress(filename, copied_bytes)

        listener.set_media_action(filename, f"Verifying checksum...")

        with smb.open_file(destination, mode="rb") as dst:
            verified_bytes = 0
            while chunk := dst.read(self._chunk_size):
                hash_dst.update(chunk)
                verified_bytes += len(chunk)
                listener.set_media_progress(filename, verified_bytes)

        return hash_src.hexdigest() == hash_dst.hexdigest()