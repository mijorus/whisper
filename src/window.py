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

from .pipewire.pipewire import Pipewire, PwLink, PwLowLatencyNode, LOW_LATENCY_NODE_NAME
from .components.PwActiveConnectionBox import PwActiveConnectionBox
from .components.NoLinksPlaceholder import NoLinksPlaceholder
from .components.PwConnectionBox import PwConnectionBox
from .utils import async_utils
from .utils.utils import link_output_input, array_diff
from typing import Optional
import json
import pprint
import threading
import pulsectl
import logging
import json
import time
import os
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Adw, Gtk, Gio, GLib  # noqa: E402


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
        self.settings.set_boolean('stand-by', False)
        
        self.is_changing_volume = False

        self.titlebar = Adw.HeaderBar()
        self.titlebar_title = Adw.WindowTitle(title='Whisper')
        self.titlebar.set_title_widget(self.titlebar_title)

        menu_obj = Gtk.Builder.new_from_resource('/it/mijorus/whisper/gtk/main-menu.ui')
        self.menu_button = Gtk.MenuButton(icon_name='open-menu', menu_model=menu_obj.get_object('primary_menu'))
        self.refresh_button = Gtk.Button(icon_name='view-refresh-symbolic')
        self.refresh_button.connect('clicked', self.on_refresh_button_clicked)

        self.titlebar.pack_end(self.menu_button)
        self.titlebar.pack_start(self.refresh_button)

        self.set_titlebar(self.titlebar)
        self.viewport = Gtk.Box(halign=Gtk.Align.CENTER, orientation=Gtk.Orientation.VERTICAL, spacing=30, margin_top=20, width_request=500)

        self.rendered_links = []
        self.manually_created_links = []

        self.auto_refresh = False
        pulse_connection_ok = False

        try:
            with pulsectl.Pulse() as pulse:
                pulse.connect()
                pulse_connection_ok = True
            
            logging.info('PulseAudio connection OK')
        except Exception as e:
            logging.error(e)

        pw_installed = Pipewire.check_installed()
        logging.info('Pipewire is installed: ' + str(pw_installed))

        # Start a thread to log
        threading.Thread(target=self._startup_logs, daemon=False).start()

        if (not pw_installed) or (not pulse_connection_ok):
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
            self.connection_box_slot = Gtk.Box()
            self.connection_box = self.create_connection_box()
            self.connection_box_slot.append(self.connection_box)
            self.viewport.append(self.connection_box_slot)

            self.active_connections_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=30)
            self.active_connection_boxes: list[PwActiveConnectionBox] = []
            self.viewport.append(self.active_connections_list)

            self.nolinks_placeholder = NoLinksPlaceholder(visible=False)
            self.viewport.append(self.nolinks_placeholder)
            self.refresh_active_connections(force_refresh=True)

            self.pulse_listener: Optional[pulsectl.Pulse] = None
            threading.Thread(target=self.create_pulse_events_listener).start()

            self.connect('close-request', self.on_close_request)

        clamp = Adw.Clamp(tightening_threshold=700)
        clamp.set_child(self.viewport)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_child(clamp)

        self.set_child(scrolled)
        self.set_default_size(700, 800)
        self.set_size_request(650, 300)

        return None

    def _startup_logs(self):
        logging.info(Pipewire.get_info_raw())

        logging.info('=======Listing outputs=======')
        for k, v in Pipewire.list_outputs().items():
            logging.info(f'Pipewire output {k}: ' + pprint.pformat(v.__dict__))

        logging.info('=======Listing inputs=======')
        for k, v in Pipewire.list_inputs().items():
            logging.info(f'Pipewire input {k}: ' + pprint.pformat(v.__dict__))

        logging.info('=======Listing active links=======')
        for k, v in Pipewire.list_links().items():
            for kk, vv in v.items():
                logging.info(f'Pipewire link {k}: ' + pprint.pformat(vv.__dict__))

    def _is_supported_device(self, pw_list: dict[str, PwLink], link_id) -> Optional[PwLink]:
        for d, dev in pw_list.items():
            if (link_id in dev.channels) and (dev.alsa.startswith('alsa:') \
                or dev.resource_name.startswith('bluez_output')) or \
                LOW_LATENCY_NODE_NAME in dev.resource_name:
                return dev

        return None

    def create_connection_box(self):
        pw_connection_box = PwConnectionBox()
        pw_connection_box.connect('new_connection', self.on_new_connection)

        return pw_connection_box

    def on_settings_changed(self, _, key: str):
        if key == 'show-connection-ids':
            self.refresh_active_connections(force_refresh=True)
            self.connection_box_slot.remove(self.connection_box)

            self.connection_box = self.create_connection_box()
            self.connection_box_slot.append(self.connection_box)

    def pulse_event_listener_unsubscribe(self):
        if self.pulse_listener is not None:
            logging.debug('Stopping event listener...')
            self.pulse_listener.event_listen_stop()
            self.pulse_listener.close()
            self.pulse_listener = None

            try:
                raise pulsectl.PulseLoopStop()
            except pulsectl.PulseLoopStop as e:
                logging.debug('PulseAudio event listener unsubscribed')

    def pulse_event_listener(self, ev):
        if self.is_changing_volume:
            return

        if ev.t == 'change':
            logging.debug(msg=f'PulseAudio event: change')
            self.pulse_event_listener_unsubscribe()

            GLib.idle_add(self.refresh_active_connections)
            GLib.idle_add(self.refresh_active_connections_volumes)

            self.create_pulse_events_listener()

    def pulse_change_volume(self, ev, sink, volume):
        if not self.pulse_listener:
            return

        self.is_changing_volume = True
        with pulsectl.Pulse() as pulse_client:
            pulse_client.volume_set_all_chans(sink, (volume / 100))
            self.is_changing_volume = False

    # @async_utils._async
    # def create_pw_top_listener():

    @async_utils._async
    def create_pulse_events_listener(self):
        self.pulse_event_listener_unsubscribe()

        logging.debug(msg=f'Creating PulseAudio event listener')
        with pulsectl.Pulse('whisper-event-listen') as listener:
            self.pulse_listener = listener
            self.pulse_listener.event_mask_set('sink')
            self.pulse_listener.event_callback_set(self.pulse_event_listener)
            self.pulse_listener.event_listen(raise_on_disconnect=False)

    def refresh_active_connections(self, force_refresh=False):
        list_links = Pipewire.list_links(quiet=(not force_refresh))

        new_links_to_render = []
        for l, link in list_links.items():
            for i, link_info in link.items():
                new_links_to_render.append(i)

        if force_refresh or array_diff(self.rendered_links, new_links_to_render):
            logging.info('Refreshing active connections')

            # recheck if there are new links
            inputs = Pipewire.list_inputs()
            outputs = Pipewire.list_outputs()
            dump = Pipewire.list_objects()

            j = 1
            device_links: dict[str, dict] = {}

            # cycle on every active link
            new_links_to_render = []
            for l, link in list_links.items():
                # cycle on every pw output, check if it is an alsa device

                output_device = self._is_supported_device(outputs, l)
                if output_device:
                    for i, link_info in link.items():
                        # cycle on every active link for that output
                        input_device = self._is_supported_device(inputs, link_info._id)
                        if input_device:
                            if not output_device.resource_name in device_links:
                                device_links[output_device.resource_name] = {}

                            if not input_device.resource_name in device_links[output_device.resource_name]:
                                
                                if LOW_LATENCY_NODE_NAME in input_device.resource_name:
                                    device_links[output_device.resource_name][input_device.resource_name] = {
                                        'device_link': DeviceLink(None, output_device, -1),
                                        'low_latency_node': True,
                                        'link_ids': []
                                    }
                                else:
                                    device_links[output_device.resource_name][input_device.resource_name] = {
                                        'device_link': DeviceLink(input_device, output_device, 0),
                                        'low_latency_node': False,
                                        'link_ids': []
                                    }

                            device_links[output_device.resource_name][input_device.resource_name]['link_ids'].append(i)
                            new_links_to_render.append(i)

            if (not force_refresh) and (not array_diff(self.rendered_links, new_links_to_render)):
                return

            for b in self.active_connection_boxes:
                self.active_connections_list.remove(b)

            self.active_connection_boxes = []
            self.rendered_links = []
            
            for output_device_resource_name, connected_devices in device_links.items():

                low_latency_nodes = {}
                connected_devices_without_lln = {}

                for d, dev in connected_devices.items():
                    if dev['low_latency_node']:
                        low_latency_nodes[d] = dev
                    else:
                        connected_devices_without_lln[d] = dev

                for d, dev in connected_devices_without_lln.items():
                    is_manually_created = False

                    for manually_created_link in self.manually_created_links:
                        if manually_created_link['output'] == dev['device_link'].output_device.resource_name and \
                                manually_created_link['input'] == dev['device_link'].input_device.resource_name:
                            is_manually_created = True
                            break

                    lln = None
                    for n, lln in low_latency_nodes.items():
                        ddev: DeviceLink = lln['device_link']
                        
                        if ddev.output_device.resource_name == dev['device_link'].output_device.resource_name:
                            node = Pipewire.find_node_by_name(dump, n)
                            lln = PwLowLatencyNode(node['id'], node['info']['props']['node.name'])

                    box = PwActiveConnectionBox(
                        link_ids=dev['link_ids'],
                        initial_lln=lln,
                        connection_name=f'Connection #{j}',
                        output_link=dev['device_link'].output_device,
                        input_link=dev['device_link'].input_device,
                        has_manual_link_indicator=is_manually_created,
                        show_link_ids=self.settings.get_boolean('show-connection-ids')
                    )

                    box.connect('disconnect', self.on_disconnect_btn_clicked)
                    box.connect('change-volume', self.pulse_change_volume)

                    self.rendered_links.extend(dev['link_ids'])
                    self.active_connection_boxes.append(box)
                    self.active_connections_list.append(box)

                    j += 1

            active_links = []
            for l in self.active_connections_list:
                active_links.append({'input': l.input_link.resource_name, 'output': l.output_link.resource_name})

            with open(GLib.get_user_data_dir() + '/last_connections.json', 'w+') as f:
                f.write(json.dumps(active_links))

        self.nolinks_placeholder.set_visible(not self.active_connection_boxes)

    def on_new_connection(self, widget, output_id, input_id):
        self.manually_created_links.append({
            'output': output_id,
            'input': input_id
        })

        self.refresh_active_connections()

    def on_disconnect_btn_clicked(self, event, link_ids: list[str], output_link: PwLink, input_link: PwLink, low_latency_node: PwLowLatencyNode=None):
        for l in link_ids:
            Pipewire.unlink(l)

        if low_latency_node:
            Pipewire.destroy_node(low_latency_node)


        for i, l in enumerate(self.manually_created_links):
            if l['output'] == output_link.resource_name and l['input'] == input_link.resource_name:
                del self.manually_created_links[i]
                break

        self.refresh_active_connections()

    @async_utils.debounce(0.5)
    def refresh_active_connections_volumes(self):
        if self.active_connection_boxes:
            logging.info('Refreshing active connections volumes')
            for b in self.active_connection_boxes:
                b.refresh_volume_levels()
                # pass

        if not self.pulse_listener:
            self.create_pulse_events_listener()

    def on_refresh_button_clicked(self, _):
        self.connection_box_slot.remove(self.connection_box)
        self.connection_box = self.create_connection_box()
        self.connection_box_slot.append(self.connection_box)

        self.refresh_active_connections(force_refresh=True)
        self.create_pulse_events_listener()

    def start_with_config(self, config: list):
        if not self.settings.get_boolean('load-last-config'):
            return

        def countdown():
            title = self.titlebar_title.get_title()

            i = 5
            while i != 0:
                print('Reloading configuration in ' + str(i) + ' seconds...')
                GLib.idle_add(lambda: self.titlebar_title.set_title(_('Reloading last connections in {0} seconds...'.format(i))))

                time.sleep(1)
                i -= 1

            GLib.idle_add(lambda: self.titlebar_title.set_title(title))

            if self.settings.get_boolean('stand-by'):
                return

            self.settings.set_boolean('stand-by', True)
            for link in config:
                try:
                    logging.info('Resuming link ' + str(link))
                    link_output_input(link['output'], link['input'])
                except Exception as e:
                    logging.warn(str(link) + ' is not linkable (devices might be disconnected)')

            time.sleep(1)
            self.settings.set_boolean('stand-by', False)
            self.refresh_active_connections(force_refresh=True)
            self.refresh_active_connections_volumes()

        t = threading.Thread(target=countdown, daemon=False).start()

        with open(GLib.get_user_data_dir() + '/last_connections.json', 'w+') as f:
            f.write('[]')

    def on_close_request(self, event):
        print('Closing...')

        if self.settings.get_boolean('release-links-on-quit'):
            try:
                for connection_box in self.active_connection_boxes:
                    for manually_created_link in self.manually_created_links:
                        if manually_created_link['output'] == connection_box.output_link.resource_name and \
                                manually_created_link['input'] == connection_box.input_link.resource_name:
                            connection_box.on_disconnect_btn_clicked(None)
            except:
                pass

        dump = Pipewire.list_objects()

        for obj in dump:
            if obj['type'] == 'PipeWire:Interface:Node' and \
                'info' in obj and \
                'props' in obj['info'] and \
                'node.name' in obj['info']['props'] and \
                LOW_LATENCY_NODE_NAME in obj['info']['props']['node.name']:

                node = PwLowLatencyNode(obj['id'], obj['info']['props']['node.name'])
                Pipewire.destroy_node(node)

        try:
            self.pulse_event_listener_unsubscribe()
        except:
            logging.warn(msg='Error while unsubscribing from pulse events')
        finally:
            return False
