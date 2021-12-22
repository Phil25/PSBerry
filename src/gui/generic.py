import remi
from typing import Dict

class StaticTabBox(remi.gui.VBox):
    _containers: Dict[str, remi.gui.Container]
    _active_button: remi.gui.Button

    _ITEM_STYLE = {
        "border-style": "none",
        "border-color": "black",
        "color": "black",
        "background-color": "#cceef7",
        "margin": "5px",
        "box-shadow": "none",
    }

    def __init__(self, containers: Dict[str, remi.gui.Container], *args, **kwargs):
        super().__init__(width="100%", *args, **kwargs)
        assert containers, "No tabs specified"

        self._containers = containers
        self._active_button = None

        tabs = remi.gui.HBox(width="100%")
        self.append(tabs)

        width = 100.0 / len(containers)
        for name, container in containers.items():
            button = remi.gui.Button(name, style=self._ITEM_STYLE)
            button.set_size(f"{width:.1f}%", "30px")
            button.onclick.do(self._on_tab_change)
            tabs.append(button, name)
            self.append(container)

        self._on_tab_change(tabs.get_child(list(containers)[0]))

    def _on_tab_change(self, button: remi.gui.Button):
        for container in self._containers.values():
            container.css_display = "none"

        assert button.get_text() in self._containers
        del self._containers[button.get_text()].css_display

        if self._active_button is not None:
            self._disable_button(self._active_button)

        self._active_button = button
        self._enable_button(self._active_button)

    def _enable_button(self, button: remi.gui.Button):
        button.style["background-color"] = "#66cee9"
        button.style["border-style"] = "none none solid none"

    def _disable_button(self, button: remi.gui.Button):
        button.style["background-color"] = "#cceef7"
        button.style["border-style"] = "none"

class StaticTextArea(remi.gui.TextInput):
    def __init__(self, single_line=True, hint="", *args, **kwargs):
        super().__init__(single_line=single_line, hint=hint, *args, **kwargs)
        self.type = "textarea readonly wrap=\"off\""