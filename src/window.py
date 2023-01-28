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

from .pipewire.pipewire import Pipewire, PwLink
from .components.PwActiveConnectionBox import PwActiveConnectionBox
from .components.NoLinksPlaceholder import NoLinksPlaceholder
from .components.PwConnectionBox import PwConnectionBox
from .utils import async_utils
from pprint import pprint
from typing import Optional
import pulsectl
import time
import os
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Adw, Gtk, Gio  # noqa: E402


class DeviceLink:
    def __init__(self, input_device, output_device, link_id):
        self.link_id: str = link_id
        self.input_device: PwLink = input_device
        self.output_device: PwLink = output_device


class WhisperWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'WhisperWindow'

    def __init__(self, **kwargs):
        super().__init__(**kwargs, title='Whisper')
        self.settings: Gio.Settings = Gio.Settings.new('it.mijorus.whisper')
        self.settings.connect('changed', self.on_settings_changed)

        self.titlebar = Adw.HeaderBar()

        menu_obj = Gtk.Builder.new_from_resource('/it/mijorus/whisper/gtk/main-menu.xml')
        self.menu_button = Gtk.MenuButton(icon_name='open-menu', menu_model=menu_obj.get_object('primary_menu'))

        self.titlebar.pack_end(self.menu_button)

        self.set_titlebar(self.titlebar)
        self.viewport = Gtk.Box(halign=Gtk.Align.CENTER, orientation=Gtk.Orientation.VERTICAL, spacing=30, margin_top=20, width_request=500)

        self.rendered_links = []

        self.auto_refresh = False
        pulse_connection_ok = False

        try:
            with pulsectl.Pulse() as pulse:
                pulse.connect()
                pulse_connection_ok = True
            print('PulseAudio connection OK')
        except:
            pass

        if (not Pipewire.check_installed()) or (not pulse_connection_ok):
            box = Gtk.Box(valign=Gtk.Align.CENTER, orientation=Gtk.Orientation.VERTICAL, spacing=5, vexpand=True)

            title = Gtk.Label(css_classes=['title-1'], label="Pipewire not detected")
            subt = Gtk.Label(css_classes=['dim-label'], label="Whisper requires Pipewire and the pipewire-cli in order to run")
            icon = Gtk.Image.new_from_icon_name('whisper-warning-symbolic')
            icon.set_css_classes(['dim-label'])
            icon.set_pixel_size(100)

            box.append(icon)
            box.append(title)
            box.append(subt)
            self.viewport.append(box)
        else:
            pulse.disconnect()
            pw_connection_box = PwConnectionBox()
            pw_connection_box.connect('new_connection', self.on_new_connection)

            self.viewport.append(pw_connection_box)

            self.active_connections_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=30)
            self.active_connection_boxes: list[PwActiveConnectionBox] = []
            self.viewport.append(self.active_connections_list)

            self.nolinks_placeholder = NoLinksPlaceholder()
            self.refresh_active_connections()
            
            self.auto_refresh = True
            self.start_auto_refresh()

        clamp = Adw.Clamp(tightening_threshold=700)
        clamp.set_child(self.viewport)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(clamp)

        self.set_child(scrolled)
        self.set_default_size(700, 800)
        self.set_size_request(650, 300)

        return None

    def _is_alsa_device(self, pw_list: dict[str, PwLink], link_id) -> Optional[PwLink]:
        for d, dev in pw_list.items():
            if (link_id in dev.channels) and dev.alsa.startswith('alsa:'):
                return dev

    def on_settings_changed(self, _, key: str):
        if key == 'show-connection-ids':
            self.refresh_active_connections(force_refresh=True)

    @async_utils._async
    def start_auto_refresh(self):
        while self.auto_refresh:
            time.sleep(5)
            self.refresh_active_connections()

    def refresh_active_connections(self, force_refresh=False):
        inputs = Pipewire.list_inputs()
        outputs = Pipewire.list_outputs()

        j = 1
        device_links: dict[str, dict] = {}

        # cycle on every active link
        for l, link in Pipewire.list_links().items():
            # cycle on every pw output, check if it is an alsa device

            output_device = self._is_alsa_device(outputs, l)
            if output_device:
                for i, link_info in link.items():
                    # cycle on every active link for that output
                    input_device = self._is_alsa_device(inputs, link_info._id)
                    if input_device:
                        if not output_device.resource_name in device_links:
                            device_links[output_device.resource_name] = {}

                        if not input_device.resource_name in device_links[output_device.resource_name]:
                            device_links[output_device.resource_name][input_device.resource_name] = {
                                'device_link': DeviceLink(input_device, output_device, 0),
                                'link_ids': []
                            }

                        device_links[output_device.resource_name][input_device.resource_name]['link_ids'].append(i)

        links_to_render = []
        for output_device_resource_name, connected_devices in device_links.items():
            for d, dev in connected_devices.items():
                links_to_render.extend(dev['link_ids'])

        self.active_connections_list.remove(self.nolinks_placeholder)

        skip_recheck = False
        if (not list(set(self.rendered_links) - set(links_to_render))) and (not list(set(links_to_render) - set(self.rendered_links))):
            if not force_refresh:
                skip_recheck = True

        if not skip_recheck:
            for b in self.active_connection_boxes:
                self.active_connections_list.remove(b)

            self.active_connection_boxes = []
            self.rendered_links = []

            for output_device_resource_name, connected_devices in device_links.items():
                for d, dev in connected_devices.items():

                    box = PwActiveConnectionBox(
                        link_ids=dev['link_ids'],
                        connection_name=f'Connection #{j}',
                        output_link=dev['device_link'].output_device,
                        input_link=dev['device_link'].input_device,
                        show_link_ids=self.settings.get_boolean('show-connection-ids')
                    )

                    box.connect('disconnect', self.on_disconnect_btn_clicked)
                    box.connect('change-volume', lambda a, b: self.refresh_active_connections_volumes())

                    self.rendered_links.extend(dev['link_ids'])
                    self.active_connection_boxes.append(box)
                    self.active_connections_list.append(box)

                    j += 1

        if not self.active_connection_boxes:
            self.active_connections_list.append(self.nolinks_placeholder)

    def on_new_connection(self, _, status):
        self.refresh_active_connections()

    def on_disconnect_btn_clicked(self, _, link_ids: list[str]):
        for l in link_ids:
            Pipewire.unlink(l)

        self.refresh_active_connections()

    def refresh_active_connections_volumes(self):
        for b in self.active_connection_boxes:
            b.refresh_volume_levels()
