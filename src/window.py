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
from .pipewire.pipewire import Pipewire

class WhisperWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'WhisperWindow'

    def __init__(self, **kwargs):
        super().__init__(**kwargs, title='Whisper')
        self.titlebar = Adw.HeaderBar()
        self.set_titlebar(self.titlebar)
        self.viewport = Gtk.Viewport(halign=Gtk.Align.CENTER)
        
        pprint(Pipewire.list_outputs())
        
        pw_connection_box = Gtk.ListBox(css_classes=['boxed-list'])
        pw_connection_box_row = Gtk.Box(spacing=10)
        
        output_select = Gtk.ComboBoxText()
        output_names = []
        for k, v in  Pipewire.list_outputs().items():  
            if ('name' in v) and ('capture' in v['alsa']): 
                output_select.append(k, v['name'])
                output_names.append(v['name'])
                
        input_select = Gtk.ComboBoxText()
        for k, v in  Pipewire.list_inputs().items():
            name = v['name'] if (v['name']) not in output_names else (v['name'] + ' - Output')
            input_select.append(k, name)
        
        pw_connection_box_row.append(output_select)
        pw_connection_box_row.append(input_select)
        pw_connection_box.append(pw_connection_box_row)
        
        self.viewport.set_child(pw_connection_box)
        clamp = Adw.Clamp()
        clamp.set_child(self.viewport)
        
        self.set_child(clamp)



