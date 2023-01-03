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


class PwActiveConnectionBox(Gtk.ListBox):
    def __init__(self, input_name: str, input_id: str, output_name: str, output_id: str, **kwargs):
        super().__init__(css_classes=['boxed-list'])

        self.input_name = input_name
        self.input_id = input_id
        self.output_name = output_name
        self.output_id = output_id
        
        self.input_exp = Adw.ExpanderRow(title=input_name)
        self.output_exp = Adw.ExpanderRow(title=output_name)
        
        self.input_range = Gtk.Scale()
        self.input_range.set_range(0, 100)
        self.output_range = Gtk.Scale()
        self.output_range.set_range(0, 100)
        
        inp_r = Gtk.ListBoxRow()
        inp_r.set_child(self.input_range)
        outp_r = Gtk.ListBoxRow()
        outp_r.set_child(self.output_range)
        
        self.input_exp.add_row(inp_r)
        self.output_exp.add_row(outp_r)
        
        self.append(self.input_exp)
        self.append(self.output_exp)