import remi
from enum import IntFlag
from collections import namedtuple
from typing import Dict
from operations import ChangeSlot, DeleteSlot
from utils.funcs import format_bytes

class SlotItem(remi.gui.HBox):
    class Flags(IntFlag):
        SELECTED = 1
        ACTIVE = 2
        DELETE = 4

    _flags: Flags
    _slot_id: str
    _name: remi.gui.Label
    _desc: remi.gui.Label
    _menu: remi.gui.Button

    _STYLE = {
        "border-style": "none none none solid",
        "margin": "5px",
        "cursor": "pointer"
    }

    def __init__(self, slot_id: str, on_context, on_click, *args, **kwargs):
        super().__init__(width="95%", height=70, style=self._STYLE, *args, **kwargs)
        self._flags = self.Flags(0)
        self._slot_id = slot_id
        self._name = remi.gui.Label(slot_id, width="100%", style={"text-align": "left", "font-weight": "bold"})
        self._desc = remi.gui.Label("", width="100%", style={"text-align": "left", "font-style": "italic", "opacity": "0.5"})
        self._update_color()

        self._menu = remi.gui.Button(text="☰", width="15%", style={"margin": "10px", "background": "none", "border-style": "ridge", "font-size": "26px"})
        self._menu.onclick.do(lambda c : on_context(slot_id))
        self.append(self._menu)

        info = remi.gui.VBox(width="85%", height="80%", style={"background": "none"})
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

class SlotList(remi.gui.VBox):
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

class MediaItem(remi.gui.VBox):
    Size = namedtuple("Size", ["number", "string"])

    _size: Size
    _filename: str
    _active_cycle: int
    _last_percentage: int
    _name: remi.gui.Label
    _action: remi.gui.Label
    _progress: remi.gui.Label
    _bar: remi.gui.Progress

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

        self._name = remi.gui.Label(filename, width="100%", style={"text-align": "left", "font-weight": "bold"})
        self._action = remi.gui.Label("", width="100%", style={"text-align": "left", "opacity": "0.5"})
        self._progress = remi.gui.Label("", width="100%", style={"text-align": "left", "opacity": "0.5"})
        self._bar = remi.gui.Progress(width="100%")

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
class MediaList(remi.gui.VBox):
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