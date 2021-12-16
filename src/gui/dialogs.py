import remi

class SlotEditDialog(remi.gui.GenericDialog):
    _slot_id: str

    _NAME = "key_name"
    _DESC = "key_description"
    _DEL = "key_delete_slider"

    def __init__(self, slot_id: str, data, *args, **kwargs):
        super().__init__(title=f"Edit slot properties", message=f"Editing slot {slot_id}.", *args, **kwargs)
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