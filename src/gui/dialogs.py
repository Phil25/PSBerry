import remi
from typing import Dict, List
from gui.item_list import RemotesList

class SlotEditDialog(remi.gui.GenericDialog):
    _slot_id: str

    _NAME = "key_name"
    _DESC = "key_description"
    _DEL = "key_delete_slider"

    def __init__(self, slot_id: str, data, *args, **kwargs):
        super().__init__(title="Edit slot properties", message=f"Editing slot {slot_id}.", *args, **kwargs)
        self.conf.set_text("Apply")
        self._slot_id = slot_id

        name = remi.gui.TextInput(hint=f"Name of {slot_id}...")
        name.set_text(data["name"])

        description = remi.gui.TextInput(single_line=False, hint=f"Description of {slot_id}...")
        description.set_text(data["description"])

        self.add_field_with_label(self._NAME, "Name", name)
        self.add_field_with_label(self._DESC, "Description", description)
        self.add_field_with_label(self._DEL, "Slide to delete", remi.gui.Slider(default_value=0, min=0, max=100))
    
    @property
    def slot_id(self) -> str:
        return self._slot_id

    def get_name(self) -> str:
        return self.get_field(self._NAME).get_value()

    def get_description(self) -> str:
        return self.get_field(self._DESC).get_value()

    def is_maked_for_deletion(self) -> bool:
        return self.get_field(self._DEL).get_value() == "100"

class ConfigureRemotesDialog(remi.gui.GenericDialog):
    _configs: List[Dict]
    _empty_driver: str

    def __init__(self, configs: List[Dict], empty_driver: str, *args, **kwargs):
        super().__init__(title="Configure remotes", message="Manage remote locations to upload media to.", *args, **kwargs)
        self._configs = configs
        self._empty_driver = empty_driver

        self.conf.set_text("Save")

        remotes = RemotesList()
        remotes.update_items(self._configs)
        self.add_field("remotes", remotes)

        add_button = remi.gui.Button("Add new remote configuration", width="60%", height=30, margin="5px 20%")
        add_button.onclick.do(self._add_remote)
        self.add_field("add_button", add_button)

    def _add_remote(self, button: remi.gui.Button):
        self._configs.append({"__description__": self._empty_driver})
        self.get_field("remotes").update_items(self._configs)

    def get_configs(self) -> List[Dict]:
        return self._configs