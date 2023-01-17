# window.py
#
# Copyright 2023 Lorenzo Paderi
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import Optional
from gi.repository import Adw, Gtk, Gio
from pprint import pprint
from .components.PwConnectionBox import PwConnectionBox
from .components.PwActiveConnectionBox import PwActiveConnectionBox
from .pipewire.pipewire import Pipewire, PwLink


class WhisperWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'WhisperWindow'

    def __init__(self, **kwargs):
        super().__init__(**kwargs, title='Whisper')
        self.settings: Gio.Settings = Gio.Settings.new('it.mijorus.whisper')

        self.titlebar = Adw.HeaderBar()
        self.set_titlebar(self.titlebar)
        self.viewport = Gtk.Box(halign=Gtk.Align.CENTER, orientation=Gtk.Orientation.VERTICAL, spacing=30, margin_top=20)

        if not Pipewire.check_installed():
            box = Gtk.Box(valign=Gtk.Align.CENTER, orientation=Gtk.Orientation.VERTICAL, spacing=5, vexpand=True)

            title = Gtk.Label(css_classes=['title-1'], label="Pipewire not detected")
            subt = Gtk.Label(css_classes=['dim-label'], label="Whisper requires Pipewire and the pipewire-cli in order to run")
            icon = Gtk.Image.new_from_icon_name('warning-symbolic')
            icon.set_css_classes(['dim-label'])
            icon.set_pixel_size(100)

            box.append(icon)
            box.append(title)
            box.append(subt)
            self.viewport.append(box)
        else:
            pw_connection_box = PwConnectionBox(new_connection_cb=self.on_new_connection)
            self.viewport.append(pw_connection_box)

            self.active_connections_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=30)
            self.active_connection_boxes: list[PwActiveConnectionBox] = []
            self.viewport.append(self.active_connections_list)

            self.refresh_active_connections()

        clamp = Adw.Clamp()
        clamp.set_child(self.viewport)

        self.set_child(clamp)
        self.set_default_size(700, 500)

    def _is_alsa_device(self, pw_list: dict[str, PwLink], link_id) -> Optional[PwLink]:
        for d, dev in pw_list.items():
            if (link_id in dev.channels) and dev.alsa.startswith('alsa:'):
                return dev

        return None

    def refresh_active_connections(self):
        inputs = Pipewire.list_inputs()
        outputs = Pipewire.list_outputs()

        j = 1

        # cycle on every active link
        for l, link in Pipewire.list_links().items():
            # cycle on every pw output, check if it is an alsa devide

            output_device = self._is_alsa_device(outputs, l)
            if output_device:
                for i, link_info in link.items():
                    # cycle on every active link for that output
                    input_device = self._is_alsa_device(inputs, link_info._id)
                    if input_device:
                            box = PwActiveConnectionBox(
                                link_id=i,
                                disconnect_cb=self.on_disconnect_btn_clicked,
                                connection_name=f'Connection #{j}',
                                output_link=output_device,
                                input_link=input_device
                            )

                            self.active_connection_boxes.append(box)
                            self.active_connections_list.append(box)

                            break

                j += 1

    def on_new_connection(self):
        self.refresh_active_connections()

    def on_disconnect_btn_clicked(self, link_id):
        Pipewire.unlink(link_id)

        for b in self.active_connection_boxes:
            self.active_connections_list.remove(b)
            self.active_connection_boxes.remove(b)
