# window.py
#
# Copyright 2023 Altravia
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

from gi.repository import Adw
from gi.repository import Gtk
from pprint import pprint
from ..pipewire.pipewire import Pipewire


class PwConnectionBox(Gtk.ListBox):
    def __init__(self, **kwargs):
        super().__init__(css_classes=['boxed-list'])

        pprint(Pipewire.list_outputs())

        pw_connection_box_row = Gtk.Box(spacing=10)

        self.output_select = Gtk.ComboBoxText()
        output_names = []
        for k, v in Pipewire.list_outputs().items():
            print(k)
            if ('name' in v) and ('capture' in v['alsa']):
                self.output_select.append(k, v['name'])
                output_names.append(v['name'])

        self.input_select = Gtk.ComboBoxText()
        for k, v in Pipewire.list_inputs().items():
            name = v['name'] if (v['name']) not in output_names else (v['name'] + ' - Output')
            self.input_select.append(k, name)

        pw_connection_box_row.append(self.output_select)
        pw_connection_box_row.append(self.input_select)
        connect_button = Gtk.Button(label='Connect')
        connect_button.connect('clicked', self.connect_source)

        self.append(pw_connection_box_row)
        self.append(connect_button)

    def connect_source(self, widget):
        if not self.output_select.get_active_id() or not self.input_select.get_active_id():
            return
        
        pw_output = Pipewire.list_outputs()[self.output_select.get_active_id()]
        if (len(pw_output['channels']) == 1) and ('_MONO' in pw_output['channels'][list(pw_output['channels'].keys())[0]]):
            # handle MONO mics
            for ch_id, ch_name in Pipewire.list_inputs()[self.input_select.get_active_id()]['channels'].items():
                print(ch_name)
                if ('_FL' in ch_name) or ('_FR' in ch_name):
                    print(pw_output['channels'].keys())
                    print(ch_id)
                    Pipewire.link(list(pw_output['channels'].keys())[0], ch_id)
