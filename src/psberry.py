import argparse
import pathlib
from drivers import DriverSMB
from operations import ChangeSlot, CreateSlot, DeleteSlot, EditSlot, TransferFiles
from typing import Dict, Tuple
from enum import IntFlag
from collections import namedtuple
from system import System, SystemMock
from remi import gui, start, App
from utils.mode import Mode
from utils.state import State
from utils.funcs import format_bytes

class ModePanel(gui.HBox):
    _icon: gui.Image
    _text: gui.Label

    _MODES = {
        Mode.USB: (
            "/root:assets/usb.png",
            "PSBerry is connected to the console. Any changes will be queued for a later time."
        ),
        Mode.MANAGE: (
            "/root:assets/manage.png",
            "PSBerry is disconnected. Applying changes..."
        )
    }

    def __init__(self, *args, **kwargs):
        super().__init__(width="100%", *args, **kwargs)
        self._icon = gui.Image("", width=100, height=100)
        self._text = gui.Label("", margin="10px")
        self.append(self._icon)
        self.append(self._text)

    def set_mode(self, mode: Mode):
        if mode is not None:
            icon, text = self._MODES[mode]
            self._icon.set_image(icon)
            self._text.set_text(text)

class FilesystemActivePanel(gui.HBox):
    _icon: gui.Label
    _text: gui.Label

    def __init__(self, *args, **kwargs):
        super().__init__(width="50%", *args, **kwargs)
        self._icon = gui.Label("●", margin="10px", style={"font-size": "20px"})
        self._text = gui.Label("filesystem active", margin="10px")
        self.append(self._icon)
        self.append(self._text)

    def set_fs_active(self, active: bool):
        if active is not None:
            self._icon.set_text("●" if active else "○")
            self._text.set_text("filesystem active" if active else "filesystem idle")

class SlotItem(gui.HBox):
    class Flags(IntFlag):
        SELECTED = 1
        ACTIVE = 2
        DELETE = 4

    _flags: Flags
    _slot_id: str
    _name: gui.Label
    _desc: gui.Label
    _menu: gui.Button

    _STYLE = {
        "border-style": "none none none solid",
        "margin": "5px",
        "cursor": "pointer"
    }

    def __init__(self, slot_id: str, on_context, on_click, *args, **kwargs):
        super().__init__(width="95%", height=70, style=self._STYLE, *args, **kwargs)
        self._flags = self.Flags(0)
        self._slot_id = slot_id
        self._name = gui.Label(slot_id, width="100%", style={"text-align": "left", "font-weight": "bold"})
        self._desc = gui.Label("", width="100%", style={"text-align": "left", "font-style": "italic", "opacity": "0.5"})
        self._update_color()

        self._menu = gui.Button(text="☰", width="15%", style={"margin": "10px", "background": "none", "border-style": "ridge", "font-size": "26px"})
        self._menu.onclick.do(lambda c : on_context(slot_id))
        self.append(self._menu)

        info = gui.VBox(width="85%", height="80%", style={"background": "none"})
        info.append(self._name)
        info.append(self._desc)
        info.onclick.do(lambda c : on_click(slot_id))
        self.append(info)

    def _update_color(self):
        # follows Metro UI palette by furielex
        # https://www.color-hex.com/color-palette/700
        if (self.Flags.ACTIVE | self.Flags.DELETE) in self._flags:
            self.style["background-color"] = "#d11155" # delete but shifted towards blue
        elif self.Flags.ACTIVE in self._flags:
            self.style["background-color"] = "#00aedb"
        elif self.Flags.DELETE in self._flags:
            self.style["background-color"] = "#d11141"
        elif self.Flags.SELECTED in self._flags:
            self.style["background-color"] = "#ffc425"
        else:
            self.style["background-color"] = "#cccccc"

    @property
    def flags(self):
        return self._flags

    def select(self):
        self._flags |= self.Flags.SELECTED
        self._update_color()

    def deselect(self):
        self._flags &= ~self.Flags.SELECTED
        self._update_color()

    def activate(self):
        self._flags |= self.Flags.ACTIVE
        self._update_color()

    def deactivate(self):
        self._flags &= ~self.Flags.ACTIVE
        self._update_color()

    def mark_for_deletion(self):
        self._flags |= self.Flags.DELETE
        self._update_color()

    def unmark_for_deletion(self):
        self._flags &= ~self.Flags.DELETE
        self._update_color()

    def enable_editing(self):
        self._menu.set_enabled(True)

    def disable_editing(self):
        self._menu.set_enabled(False)

    def set_name(self, name: str):
        name = f": {name}" if name else ""
        self._name.set_text(f"{self._slot_id}{name}")

    def set_description(self, desc: str):
        self._desc.set_text(desc)

class SlotList(gui.VBox):
    _list: Dict[str, SlotItem]
    _active: str
    _selected: str

    def __init__(self, on_slot_edit, on_slot_select, *args, **kwargs):
        super().__init__(width="100%", *args, **kwargs)
        self._on_slot_edit = on_slot_edit
        self._on_slot_select = on_slot_select
        self._list = {}
        self._active = None
        self._selected = None

    def update_items(self, save_data):
        if len(self.children) != len(save_data):
            self._rebuild(save_data)
            return
        
        for slot_id, item in self._list.items():
            data = save_data.get(slot_id, {"name": "", "description": ""})
            item.set_name(data["name"])
            item.set_description(data["description"])

    def _rebuild(self, save_data):
        self.empty()
        self._list.clear()

        for slot_id in sorted(save_data.keys()):
            item = SlotItem(slot_id, self._on_slot_edit, self._on_slot_select)
            item.set_name(save_data[slot_id]["name"])
            item.set_description(save_data[slot_id]["description"])
            self._list[slot_id] = item
            self.append(item)

    def _all(self, func: str):
        for item in self._list.values():
            getattr(item, func)()

    def _single(self, slot_id: str, func: str):
        if slot_id in self._list:
            getattr(self._list[slot_id], func)()

    def set_active(self, slot_id: str):
        self._all("deactivate")
        self._single(slot_id, "activate")

    def on_operations_update(self, ops):
        if ops is None:
            return

        self._all("deselect")
        self._all("unmark_for_deletion")
        self._all("enable_editing")

        if ChangeSlot.__name__ in ops:
            self._single(ops[ChangeSlot.__name__].slot_id, "select")

        if DeleteSlot.__name__ in ops:
            self._single(ops[DeleteSlot.__name__].slot_id, "mark_for_deletion")
            self._all("disable_editing") # slot_ids might change and desync

class SlotEditDialog(gui.GenericDialog):
    _slot_id: str

    _NAME = "key_name"
    _DESC = "key_description"
    _DEL = "key_delete_slider"

    def __init__(self, slot_id: str, data, *args, **kwargs):
        super().__init__(title=f"Edit slot properties", message=f"Editing slot {slot_id}.", *args, **kwargs)
        self.conf.set_text("Apply")
        self._slot_id = slot_id

        name = gui.TextInput(hint=f"Name of {slot_id}...")
        name.set_text(data["name"])

        description = gui.TextInput(single_line=False, hint=f"Description of {slot_id}...")
        description.set_text(data["description"])

        self.add_field_with_label(self._NAME, "Name", name)
        self.add_field_with_label(self._DESC, "Description", description)
        self.add_field_with_label(self._DEL, "Slide to delete", gui.Slider(default_value=0, min=0, max=100))
    
    @property
    def slot_id(self) -> str:
        return self._slot_id

    def get_name(self) -> str:
        return self.get_field(self._NAME).get_value()

    def get_description(self) -> str:
        return self.get_field(self._DESC).get_value()

    def is_maked_for_deletion(self) -> bool:
        return self.get_field(self._DEL).get_value() == "100"

class SlotButtons(gui.HBox):
    _create: gui.Button
    _clone: gui.Button

    _LABEL_CREATE = "Create New"
    _LABEL_CLONE = "Clone Active"

    def __init__(self, create_op, *args, **kwargs):
        super().__init__(width="100%", height=40, *args, **kwargs)
        self._create_op = create_op

        self._create = gui.Button(self._LABEL_CREATE, width="50%", height="75%", margin="20px")
        self._create.onclick.do(self._on_slot_create)
        self.append(self._create)

        self._clone = gui.Button(self._LABEL_CLONE, width="50%", height="75%", margin="20px")
        self._clone.onclick.do(self._on_slot_create)
        self.append(self._clone)

    def _on_slot_create(self, button: gui.Button):
        self._create_op(button.get_text() ==self._LABEL_CLONE)

    def on_operations_update(self, ops):
        if ops is None:
            return

        creating = CreateSlot.__name__ in ops
        self._create.set_enabled(not creating)
        self._clone.set_enabled(not creating)

class StaticTabBox(gui.VBox):
    _containers: Dict[str, gui.Container]
    _active_button: gui.Button

    _ITEM_STYLE = {
        "border-style": "none",
        "border-color": "black",
        "color": "black",
        "background-color": "#cceef7",
        "margin": "5px",
        "box-shadow": "none",
    }

    def __init__(self, containers: Dict[str, gui.Container], *args, **kwargs):
        super().__init__(width="100%", *args, **kwargs)
        assert containers, "No tabs specified"

        self._containers = containers
        self._active_button = None

        tabs = gui.HBox(width="100%")
        self.append(tabs)

        width = 100.0 / len(containers)
        for name, container in containers.items():
            button = gui.Button(name, style=self._ITEM_STYLE)
            button.set_size(f"{width:.1f}%", "30px")
            button.onclick.do(self._on_tab_change)
            tabs.append(button, name)
            self.append(container)

        self._on_tab_change(tabs.get_child(list(containers)[0]))

    def _on_tab_change(self, button: gui.Button):
        for container in self._containers.values():
            container.css_display = "none"

        assert button.get_text() in self._containers
        del self._containers[button.get_text()].css_display

        if self._active_button is not None:
            self._disable_button(self._active_button)

        self._active_button = button
        self._enable_button(self._active_button)

    def _enable_button(self, button: gui.Button):
        button.style["background-color"] = "#66cee9"
        button.style["border-style"] = "none none solid none"

    def _disable_button(self, button: gui.Button):
        button.style["background-color"] = "#cceef7"
        button.style["border-style"] = "none"

class MediaItem(gui.VBox):
    Size = namedtuple("Size", ["number", "string"])

    _size: Size
    _filename: str
    _active_cycle: int
    _last_percentage: int
    _name: gui.Label
    _action: gui.Label
    _progress: gui.Label
    _bar: gui.Progress

    _STYLE = {
        "border-style": "none none none solid",
        "margin": "5px",
        "padding": "5px",
    }

    def __init__(self, filename: str, *args, **kwargs):
        super().__init__(width="95%", style=self._STYLE, *args, **kwargs)

        self.set_media_size(0)
        self._filename = filename
        self._active_cycle = 0
        self._last_percentage = 0

        self._name = gui.Label(filename, width="100%", style={"text-align": "left", "font-weight": "bold"})
        self._action = gui.Label("", width="100%", style={"text-align": "left", "opacity": "0.5"})
        self._progress = gui.Label("", width="100%", style={"text-align": "left", "opacity": "0.5"})
        self._bar = gui.Progress(width="100%")

        self.append(self._name)
        self.append(self._action)
        self.append(self._progress)
        self.append(self._bar)

    def set_media_size(self, size: int):
        self._size = self.Size(size, format_bytes(size))

    def set_media_progress(self, current: int):
        percentage = int(current / self._size.number * 100)
        if self._last_percentage == percentage:
            # this function can be called a bit too often for my taste
            return

        self._progress.set_text(f"{percentage}%: {format_bytes(current)}/{self._size.string}")
        self._bar.set_value(percentage)
        self._last_percentage = percentage

    def set_media_action(self, action: str):
        self._action.set_text(action)

    def update_active(self, active: bool):
        self._active_cycle = self._active_cycle + 1 if active else 0
        self._name.set_text(f"{self._filename}{'.' * (self._active_cycle % 4)}")
        self._name.css_opacity = "0.5" if active else "1.0"

# TODO: commonize with SlotList
class MediaList(gui.VBox):
    _list: Dict[str, MediaItem]
    _active: str
    _selected: str

    def __init__(self, on_media_upload, *args, **kwargs):
        super().__init__(width="100%", *args, **kwargs)
        self._list = {}
        self._on_media_upload = on_media_upload

    def update_items(self, media_data):
        self._update_active(media_data)

        if len(self.children) == len(media_data):
            return

        self._rebuild(media_data)

        if len(media_data):
            self._on_media_upload(media_data, self)

    def _update_active(self, media_data):
        for media, data in media_data.items():
            self._single(media, "update_active", data["is_active"])

    def _rebuild(self, media_data):
        self.empty()
        self._list.clear()

        for name in media_data.keys():
            item = MediaItem(name)
            self._list[name] = item
            self.append(item)

        self._update_active(media_data)

    def _all(self, func: str, *args, **kwargs):
        for item in self._list.values():
            getattr(item, func)(*args, **kwargs)

    def _single(self, key: str, func: str, *args, **kwargs):
        if key in self._list:
            getattr(self._list[key], func)(*args, **kwargs)

    def set_media_size(self, filename: str, size: int):
        self._single(filename, "set_media_size", size)

    def set_media_progress(self, filename: str, cur: int):
        self._single(filename, "set_media_progress", cur)

    def set_media_action(self, filename: str, action: str):
        self._single(filename, "set_media_action", action)

class PSBerry(App):
    _state: State
    _slot_list: SlotList
    _slot_buttons: SlotButtons
    _media_list: MediaList

    _CONTAINER_STYLE = {"margin": "0px auto", "max-width": "400px"}

    def __init__(self, *args):
        super(PSBerry, self).__init__(*args, static_file_path={"root": "."})

    def main(self, state: State):
        self._state = state
        container = gui.VBox(width="100%", style=self._CONTAINER_STYLE)

        mode_panel = ModePanel()
        fs_active_panel = FilesystemActivePanel()
        tab_box = StaticTabBox(dict([self._save_manager(), self._media_uploader()]))

        container.append(mode_panel)
        container.append(fs_active_panel)
        container.append(tab_box)

        self._register("mode", mode_panel.set_mode)
        self._register("fs_active", fs_active_panel.set_fs_active)
        self._register("filesystem", self._on_fs_update)
        self._register("operations", self._slot_list.on_operations_update)
        self._register("operations", self._slot_buttons.on_operations_update)

        return container

    def _save_manager(self) -> Tuple[str, gui.Container]:
        save_manager = gui.VBox(width="100%")

        self._slot_list = SlotList(self._on_slot_edit, self._on_slot_select)
        save_manager.append(self._slot_list)

        self._slot_buttons = SlotButtons(self._on_slot_create)
        save_manager.append(self._slot_buttons)

        return "Save Manager", save_manager

    def _media_uploader(self) -> Tuple[str, gui.Container]:
        media_uploader = gui.VBox(width="100%")

        self._media_list = MediaList(self._on_media_upload)
        media_uploader.append(self._media_list)

        media_uploader.append(gui.Button("Configure Remotes", width="60%", height=30, margin="5px 20%"))

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
        dialog = SlotEditDialog(slot_id, fs["slots"][slot_id], style=self._CONTAINER_STYLE)
        dialog.confirm_dialog.do(self._edit_slot)
        dialog.show(self)

    def _edit_slot(self, dialog: SlotEditDialog):
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

    state.write("drivers", [
        # TODO: move this to UI configuration
        DriverSMB("remote", "folder", "username", "password")
    ])

    with (SystemMock if args.mock else System)(state, args.block, args.mount):
        start(PSBerry, address="0.0.0.0", port=8080, start_browser=args.browser, debug=args.debug, userdata=(state,))

if __name__ == "__main__":
    main()