import remi
from utils.mode import Mode
from operations import CreateSlot

class ModePanel(remi.gui.HBox):
    _icon: remi.gui.Image
    _text: remi.gui.Label

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
        self._icon = remi.gui.Image("", width=100, height=100)
        self._text = remi.gui.Label("", margin="10px")
        self.append(self._icon)
        self.append(self._text)

    def set_mode(self, mode: Mode):
        if mode is not None:
            icon, text = self._MODES[mode]
            self._icon.set_image(icon)
            self._text.set_text(text)

class FilesystemActivePanel(remi.gui.HBox):
    _icon: remi.gui.Label
    _text: remi.gui.Label

    def __init__(self, *args, **kwargs):
        super().__init__(width="50%", *args, **kwargs)
        self._icon = remi.gui.Label("●", margin="10px", style={"font-size": "20px"})
        self._text = remi.gui.Label("filesystem active", margin="10px")
        self.append(self._icon)
        self.append(self._text)

    def set_fs_active(self, active: bool):
        if active is not None:
            self._icon.set_text("●" if active else "○")
            self._text.set_text("filesystem active" if active else "filesystem idle")

class SlotButtonsPanel(remi.gui.HBox):
    _create: remi.gui.Button
    _clone: remi.gui.Button

    _LABEL_CREATE = "Create New"
    _LABEL_CLONE = "Clone Active"

    def __init__(self, create_op, *args, **kwargs):
        super().__init__(width="100%", height=40, *args, **kwargs)
        self._create_op = create_op

        self._create = remi.gui.Button(self._LABEL_CREATE, width="50%", height="75%", margin="20px")
        self._create.onclick.do(self._on_slot_create)
        self.append(self._create)

        self._clone = remi.gui.Button(self._LABEL_CLONE, width="50%", height="75%", margin="20px")
        self._clone.onclick.do(self._on_slot_create)
        self.append(self._clone)

    def _on_slot_create(self, button: remi.gui.Button):
        self._create_op(button.get_text() == self._LABEL_CLONE)

    def on_operations_update(self, ops):
        if ops is None:
            return

        creating = CreateSlot.__name__ in ops
        self._create.set_enabled(not creating)
        self._clone.set_enabled(not creating)

class MediaButtonsPanel(remi.gui.VBox):
    _upload: remi.gui.Button
    _configure: remi.gui.Button
    _automate: remi.gui.CheckBoxLabel

    _LABEL_UPLOAD = "Upload All"
    _LABEL_CONFIGURE = "Configure Remotes"
    _LABEL_AUTOMATE = "Automatically upload files as they come."

    def __init__(self, upload_op, configure_op, automate_op, upload_automatically, *args, **kwargs):
        super().__init__(height=80, margin="10px", *args, **kwargs)
        self._upload_op = upload_op
        self._configure_op = configure_op
        self._automate_op = automate_op

        buttons = remi.gui.HBox(width="100%", height=40)

        self._upload = remi.gui.Button(self._LABEL_UPLOAD, width="50%", height="75%", margin="20px")
        self._upload.onclick.do(self._on_upload)
        buttons.append(self._upload)

        self._configure = remi.gui.Button(self._LABEL_CONFIGURE, width="50%", height="75%", margin="20px")
        self._configure.onclick.do(self._on_configure)
        buttons.append(self._configure)

        self.append(buttons)

        self._automate = remi.gui.CheckBoxLabel(self._LABEL_AUTOMATE, checked=upload_automatically, margin="20px")
        self._automate.onchange.do(self._on_automate)
        self.append(self._automate)

    def _on_upload(self, button: remi.gui.Button):
        self._upload_op()

    def _on_configure(self, button: remi.gui.Button):
        self._configure_op()

    def _on_automate(self, checkbox: remi.gui.CheckBoxLabel, value: bool):
        self._automate_op(value)