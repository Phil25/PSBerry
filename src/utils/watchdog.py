import threading
from time import sleep

class Watchdog(threading.Thread):
    _should_run: bool
    _idle_threshold: int

    def __init__(self, update_filesystem, update_idle, handle_operations):
        self._should_run = True
        self._idle_threshold = 2
        self._update_filesystem = update_filesystem
        self._update_idle = update_idle
        self._handle_operations = handle_operations
        threading.Thread.__init__(self)

    def kill(self):
        self._should_run = False

    def run(self):
        cycle = 0
        fs_idle = 0
        while self._should_run:
            if cycle % 2 == 0:
                # if filesystem changed, reset the idle counter state
                fs_idle = 0 if self._update_filesystem() else fs_idle + 1
                self._update_idle(fs_idle < self._idle_threshold)

            if fs_idle >= self._idle_threshold:
                # filesystem was idle for multiple cycles, should be safe to handle ops
                fs_idle = 0 if self._handle_operations() else fs_idle
                self._update_idle(fs_idle < self._idle_threshold)

            cycle = cycle + 1
            sleep(1)