import argparse
import pathlib
import remi
import gui
from drivers import DriverBase
from operations import ChangeSlot, CreateSlot, DeleteSlot, EditSlot, TransferFiles
from typing import Tuple
from system import System, SystemMock
from utils.state import State

class PSBerry(remi.App):
    _state: State
    _slot_list: gui.SlotList
    _slot_buttons: gui.SlotButtonsPanel
    _media_list: gui.MediaList

    _CONTAINER_STYLE = {"margin": "0px auto", "max-width": "400px"}

    def __init__(self, *args):
        super(PSBerry, self).__init__(*args, static_file_path={"root": "."})

    def main(self, state: State):
        self._state = state
        container = remi.gui.VBox(width="100%", style=self._CONTAINER_STYLE)

        mode_panel = gui.ModePanel()
        fs_active_panel = gui.FilesystemActivePanel()
        tab_box = gui.StaticTabBox(dict([self._save_manager(), self._media_uploader()]))

        container.append(mode_panel)
        container.append(fs_active_panel)
        container.append(tab_box)

        self._register("mode", mode_panel.set_mode)
        self._register("fs_active", fs_active_panel.set_fs_active)
        self._register("filesystem", self._on_fs_update)
        self._register("operations", self._slot_list.on_operations_update)
        self._register("operations", self._slot_buttons.on_operations_update)

        return container

    def _save_manager(self) -> Tuple[str, remi.gui.Container]:
        save_manager = remi.gui.VBox(width="100%")

        self._slot_list = gui.SlotList(self._on_slot_edit, self._on_slot_select)
        save_manager.append(self._slot_list)

        self._slot_buttons = gui.SlotButtonsPanel(self._on_slot_create)
        save_manager.append(self._slot_buttons)

        return "Save Manager", save_manager

    def _media_uploader(self) -> Tuple[str, remi.gui.Container]:
        media_uploader = remi.gui.VBox(width="100%")

        self._media_list = gui.MediaList(self._on_media_upload)
        media_uploader.append(self._media_list)

        configure_remotes = remi.gui.Button("Configure Remotes", width="60%", height=30, margin="5px 20%")
        configure_remotes.onclick.do(self._on_remotes_edit)
        media_uploader.append(configure_remotes)

        return "Media Uploader", media_uploader

    def _register(self, field: str, callback):
        "Register for state change, but also trigger if already set"
        self._state.register(field, callback)
        callback(self._state.read(field))

    def _on_fs_update(self, fs):
        if fs is None:
            return

        self._slot_list.update_items(fs["slots"])
        self._slot_list.set_active(fs["active_slot"])
        self._media_list.update_items(fs["media"])

    def _on_slot_edit(self, slot_id: str):
        fs = self._state.read("filesystem")
        dialog = gui.SlotEditDialog(slot_id, fs["slots"][slot_id], style=self._CONTAINER_STYLE)
        dialog.confirm_dialog.do(self._edit_slot)
        dialog.show(self)

    def _edit_slot(self, dialog: gui.SlotEditDialog):
        o = DeleteSlot(dialog.slot_id) if dialog.is_maked_for_deletion() else \
            EditSlot(dialog.slot_id, dialog.get_name(), dialog.get_description())
        self._state.queue_operation(o)

    def _on_slot_select(self, slot_id: str):
        self._state.queue_operation(ChangeSlot(slot_id))

    def _on_slot_create(self, clone_active: bool):
        self._state.queue_operation(CreateSlot(clone_active=clone_active))

    def _on_media_upload(self, media_data, listener):
        drivers = self._state.read("drivers")
        if len(drivers):
            self._state.queue_operation(TransferFiles(media_data, drivers, listener))

    def _on_remotes_edit(self, button: remi.gui.Button):
        config = [d.config for d in self._state.read("drivers")]
        dialog = gui.ConfigureRemotesDialog(config, DriverBase.empty_driver, style=self._CONTAINER_STYLE)
        dialog.confirm_dialog.do(self._save_remotes_configuration)
        dialog.show(self)

    def _save_remotes_configuration(self, dialog: gui.ConfigureRemotesDialog):
        self._state.options.remotes = dialog.get_configs()
        self._state.write("drivers", DriverBase.from_configs(dialog.get_configs()))

def get_args():
    parser = argparse.ArgumentParser(description="Start PSBerry.")
    parser.add_argument("--mock", "-m", default=False, action=argparse.BooleanOptionalAction, help="Use mocked system operations.")
    parser.add_argument("--debug", "-d", default=False, action=argparse.BooleanOptionalAction, help="Launch Remi web app in debug mode.")
    parser.add_argument("--browser", "-b", default=False, action=argparse.BooleanOptionalAction, help="Launch browser.")
    parser.add_argument("--block", default="/storage.bin", type=pathlib.Path, help="Block storage location.")
    parser.add_argument("--mount", default="/home/pi/storage", type=pathlib.Path, help="Local mount point directory for the USB block storage.")
    return parser.parse_args()

def main():
    args = get_args()
    state = State()

    state.write("drivers", DriverBase.from_configs(state.options.remotes))

    with (SystemMock if args.mock else System)(state, args.block, args.mount):
        remi.start(PSBerry, address="0.0.0.0", port=8080, start_browser=args.browser, debug=args.debug, userdata=(state,))

if __name__ == "__main__":
    main()