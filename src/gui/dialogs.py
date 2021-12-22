import remi
from typing import Dict, List
from drivers import DriverBase
from gui.item_list import RemotesList
from gui.generic import StaticTextArea

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
    _logs: StaticTextArea

    def __init__(self, configs: List[Dict], empty_driver: str, *args, **kwargs):
        super().__init__(title="Configure remotes", message="Manage remote locations to upload media to.", *args, **kwargs)
        self._configs = configs
        self._empty_driver = empty_driver

        self.conf.set_text("Save")

        remotes = RemotesList()
        remotes.update_items(self._configs)
        self.add_field("remotes", remotes)

        self.add_field("buttons", self._manager_buttons())

        self._logs = StaticTextArea(single_line=False, hint="Test logs will appear here...", height=100)
        self.add_field("logs", self._logs)

    def _manager_buttons(self) -> remi.gui.HBox:
        buttons = remi.gui.HBox(width="100%")

        add_button = remi.gui.Button("Add new remote", width="40%", height=30)
        add_button.onclick.do(self._add_remote)
        buttons.append(add_button, "add_button")

        test_button = remi.gui.Button("Test all remotes", width="40%", height=30)
        test_button.onclick.do(self._test_remotes)
        buttons.append(test_button, "test_button")

        return buttons

    def _add_remote(self, button: remi.gui.Button):
        self._configs.append({"__description__": self._empty_driver})
        self.get_field("remotes").update_items(self._configs)

    def _test_remotes(self, button: remi.gui.Button):
        logs = ""
        sep = "\n  * "
        drivers = DriverBase.from_configs(self._configs)

        for i, driver in enumerate(drivers):
            logs += f"#{i + 1} "
            if len(driver.errors) > 0:
                logs += f"{driver.description} ERROR ({driver.destination})."
                logs += f"{sep}{sep.join(driver.errors)}\n"
            else:
                logs += f"Uploading to {driver.destination} OK.\n"

        self._logs.set_value(logs[:-1])

    def get_configs(self) -> List[Dict]:
        return self._configs

    def get_drivers(self) -> List[DriverBase]:
        return DriverBase.from_configs(self._configs)