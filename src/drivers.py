import os
import re
import hashlib
from typing import Dict, List, Tuple
import smbclient as smb

_EMPTY_DRIVER = "None (removes driver)"

class DriverBase():
    _config: Dict
    _errors: List[str]

    empty_driver = _EMPTY_DRIVER
    description = "No driver implementation provided."
    fields = []
    required_fields = []

    def __init__(self, config: Dict) -> None:
        self._config = dict(config, **{"__description__": self.description})
        self._errors = []

        for field in self.required_fields:
            if field not in config or not config[field]:
                self._errors.append(f"Missing field \"{field}\".")

        if not self._errors:
            self._errors.extend(self._connect())

    @property
    def errors(self) -> List[str]:
        return self._errors

    def _connect(self) -> List[str]:
        """
        Individual drivers attempt connecting and testing here,
        returning list of errors. Performing any action is optional,
        but implementation must be specified. This won't be called
        if required fields are missing.
        """
        return ["No driver implementation provided."]

    @property
    def destination(self) -> str:
        """
        Human-readable destination which this driver uploads files to.
        """
        return "No driver implementation provided."

    def upload(self, source: str, filename: str, listener) -> bool:
        return False if self._errors else self._upload(source, filename, listener)

    def _upload(self, source: str, filename: str, listener):
        """
        Individual drivers upload file from source to {remote}/filename here.
        """
        return False

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
    required_fields = ["remote", "folder"]

    def __init__(self, config: Dict) -> None:
        remote, folder = config.get("remote", ""), config.get("folder", "")
        self._remote_root = fr"\\{remote}\{folder}"
        self._chunk_size = 8192
        super().__init__(config)

    def _connect(self) -> List[str]:
        try:
            smb.register_session(self._config["remote"], username=self._config.get("username"), password=self._config.get("password"))
            smb.stat(self._remote_root) # test
        except Exception as e:
            return [str(e)]
        return []

    @property
    def destination(self) -> str:
        return self._remote_root

    def _upload(self, source: str, filename: str, listener) -> bool:
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