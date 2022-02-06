import remi
from enum import IntFlag
from collections import namedtuple
from typing import Dict, Generic, List, TypeVar
from operations import ChangeSlot, DeleteSlot
from drivers import DriverBase
from utils.funcs import format_bytes

_STYLE = {
    "interactive": {
        "border-style": "none none none solid",
        "margin": "5px",
        "cursor": "pointer"
    },
    "static": {
        "border-style": "solid none none none",
        "margin": "5px",
        "padding": "5px",
    },
    "title": {"text-align": "left", "font-weight": "bold"},
    "subtitle": {"text-align": "left", "font-style": "italic", "opacity": "0.5"},
    "button": {"margin": "10px", "background": "none", "border-style": "ridge", "font-size": "26px"},
}

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

    def __init__(self, slot_id: str, on_context, on_click, *args, **kwargs):
        super().__init__(width="95%", height=70, style=_STYLE["interactive"], *args, **kwargs)
        self._flags = self.Flags(0)
        self._slot_id = slot_id
        self._name = remi.gui.Label(slot_id, width="100%", style=_STYLE["title"])
        self._desc = remi.gui.Label("", width="100%", style=_STYLE["subtitle"])
        self._update_color()

        self._menu = remi.gui.Button(text="☰", width="15%", style=_STYLE["button"])
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

class MediaItem(remi.gui.VBox):
    Size = namedtuple("Size", ["number", "string"])

    _size: Size
    _filename: str
    _active_cycle: int
    _last_percentage: int
    _marked_for_delete: bool

    _name: remi.gui.Label
    _action: remi.gui.Label
    _progress: remi.gui.Label
    _bar: remi.gui.Progress

    def __init__(self, filename: str, *args, **kwargs):
        super().__init__(width="95%", style=_STYLE["static"], *args, **kwargs)

        self.set_media_size(0)
        self._filename = filename
        self._active_cycle = 0
        self._last_percentage = 0
        self._marked_for_delete = False

        self._name = remi.gui.Label(filename, width="100%", style=_STYLE["title"])
        self._action = remi.gui.Label("", width="100%", style=_STYLE["subtitle"])

        progress_container = remi.gui.HBox(width="100%", style={"background": "none"})

        progress_info = remi.gui.VBox(width="85%", style={"background": "none"})
        self._progress = remi.gui.Label("", width="100%", style=_STYLE["subtitle"])
        self._bar = remi.gui.Progress(width="100%")
        progress_info.append(self._progress)
        progress_info.append(self._bar)

        delete_button = remi.gui.Button("X", width="15%", height=30, style=_STYLE["button"])
        delete_button.css_background_color = "#d11141"
        delete_button.css_font_size = "20"
        delete_button.onclick.do(self._delete_media)

        progress_container.append(progress_info)
        progress_container.append(delete_button)

        self.append(self._name)
        self.append(self._action)
        self.append(progress_container)

    def _delete_media(self, button: remi.gui.Button):
        self.css_background_color = "#d11141"
        self._marked_for_delete = True

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

    def is_marked_for_delete(self):
        return self._marked_for_delete

    def update_active(self, active: bool):
        self._active_cycle = self._active_cycle + 1 if active else 0
        self._name.set_text(f"{self._filename}{'.' * (self._active_cycle % 4)}")
        self._name.css_opacity = "0.5" if active else "1.0"

class RemoteItem(remi.gui.GenericDialog):
    _config: Dict

    def __init__(self, config: Dict, *args, **kwargs):
        super().__init__(width="95%", style=_STYLE["static"], *args, **kwargs)
        assert "__description__" in config
        self.remove_child(self.get_child("buttons_container"))
        self._config = config

        dropdown = remi.gui.DropDown.new_from_list(DriverBase.get_descriptions())
        dropdown.select_by_value(config["__description__"])

        self._update_fields(dropdown, config["__description__"])
        dropdown.onchange.do(self._update_fields)

    def _update_fields(self, dropdown: remi.gui.DropDown, description: str):
        self.container.empty()
        self.add_field_with_label("__description__", "Driver", dropdown)
        self._config["__description__"] = description

        for field_name, field_type in DriverBase.get_fields(description):
            default = self._config[field_name] if field_name in self._config else ""
            field = remi.gui.Input(input_type=field_type, default_value=default)
            field.onchange.do(self._on_field_update, field_name)
            self.add_field_with_label(field_name, field_name.capitalize(), field)

    def _on_field_update(self, field: remi.gui.Input, value, field_name: str):
        self._config[field_name] = value

ItemType = TypeVar("ItemType")

class _ItemList(Generic[ItemType], remi.gui.VBox):
    _list: Dict[str, ItemType]

    def __init__(self, *args, **kwargs):
        super().__init__(width="100%", *args, **kwargs)
        self._list = {}

    def _all(self, func: str, *args, **kwargs):
        for item in self._list.values():
            getattr(item, func)(*args, **kwargs)

    def _single(self, key: str, func: str, *args, **kwargs):
        if key in self._list:
            return getattr(self._list[key], func)(*args, **kwargs)
        return None

    def update_items(self, data):
        self._rebuild(data)

    def _rebuild(self, data):
        self.empty()
        self._list.clear()
        self._build(data)

    def append(self, item: ItemType, key: str):
        self._list[key] = item
        super(remi.gui.VBox, self).append(item, key)

class SlotList(_ItemList[SlotItem]):
    _active: str
    _selected: str

    def __init__(self, on_slot_edit, on_slot_select, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._on_slot_edit = on_slot_edit
        self._on_slot_select = on_slot_select
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

    def _build(self, save_data):
        for slot_id in sorted(save_data.keys()):
            item = SlotItem(slot_id, self._on_slot_edit, self._on_slot_select)
            item.set_name(save_data[slot_id]["name"])
            item.set_description(save_data[slot_id]["description"])
            self.append(item, slot_id)

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

class MediaList(_ItemList[MediaItem]):
    def __init__(self, on_media_upload, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._on_media_upload = on_media_upload

    def update_items(self, media_data):
        self._update_active(media_data)

        if len(self.children) == len(media_data):
            return

        self._rebuild(media_data)
        self._on_media_upload(media_data, self)

    def _update_active(self, media_data):
        for media, data in media_data.items():
            self._single(media, "update_active", data["is_active"])

    def _build(self, media_data):
        for name in media_data.keys():
            item = MediaItem(name)
            self.append(item, name)

        self._update_active(media_data)

    def set_media_size(self, filename: str, size: int):
        self._single(filename, "set_media_size", size)

    def set_media_progress(self, filename: str, cur: int):
        self._single(filename, "set_media_progress", cur)

    def set_media_action(self, filename: str, action: str):
        self._single(filename, "set_media_action", action)

    def is_media_marked_for_delete(self, filename: str):
        return self._single(filename, "is_marked_for_delete")

class RemotesList(_ItemList[RemoteItem]):
    def _build(self, configs: List[Dict]):
        for i, config in enumerate(configs):
            self.append(RemoteItem(config), str(i))