import os
import re
import hashlib
import smbclient as smb

class DriverBase():
    def __init__(self) -> None:
        pass

    def upload(self, source: str, filename: str, progress) -> bool:
        return False

    @property
    def error(self):
        return "No driver implementation provided."


class DriverSMB(DriverBase):
    _remote_root: str
    _chunk_size: int

    def __init__(self, remote: str, folder: str, username: str, password: str, chunk_size: int=8192) -> None:
        super().__init__()
        self._remote_root = fr"\\{remote}\{folder}"
        self._chunk_size = chunk_size
        smb.register_session(remote, username=username, password=password)

    def upload(self, source: str, filename: str, progress) -> bool:
        size = os.stat(source).st_size
        effective_file = re.sub(r"[^\w\-_\. ]", "_", filename)
        destination = fr"{self._remote_root}\{effective_file}"

        hash_src = hashlib.md5()
        hash_dst = hashlib.md5()

        with open(source, mode="rb") as src:
            with smb.open_file(destination, mode="wb") as dst:
                copied_bytes = 0
                while chunk := src.read(self._chunk_size):
                    dst.write(chunk)
                    hash_src.update(chunk)
                    copied_bytes += len(chunk)
                    progress(filename, copied_bytes, size)

        with smb.open_file(destination, mode="rb") as dst:
            while chunk := dst.read(self._chunk_size):
                hash_dst.update(chunk)

        return hash_src.hexdigest() == hash_dst.hexdigest()


def get_class(name: str):
    return {
        "smb": DriverSMB
    }[name]