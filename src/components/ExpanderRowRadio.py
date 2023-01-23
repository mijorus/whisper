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

import pulsectl
import time
from gi.repository import Adw
from gi.repository import Gtk, GObject
from pprint import pprint
from ..utils import async_utils
from ..pipewire.pipewire import Pipewire, PwLink


class ExpanderRowRadio(Adw.ExpanderRow):
    __gsignals__ = {
        'change': (GObject.SIGNAL_RUN_FIRST, None, (str,))
    }

    def __init__(self, title, **kwargs):
        super().__init__(title=title, **kwargs)
        self.original_title = title
        self.radio_buttons = []

    def get_active_id(self):
        for r in self.radio_buttons:
            if r.get_active():
                return r._id

        return None

    def set_active_id(self, _id: str):
        for r in self.radio_buttons:
            if r._id == _id:
                return r.set_active(True)

        for r in self.radio_buttons:
            r.set_active(False)

        self.set_title(self.original_title)
        return None

    def add(self, name: str, _id: str, id_as_subtitle=False):
        radio = Gtk.CheckButton()
        radio._id = _id
        radio._name = name

        row = Adw.ActionRow(activatable_widget=radio, title=name)
        if id_as_subtitle:
            row.set_subtitle(_id)

        row.add_prefix(radio)

        self.add_row(row)
        self.radio_buttons.append(radio)

        radio.connect('toggled', self.on_toggled)

        if len(self.radio_buttons) > 1:
            radio.set_group(self.radio_buttons[0])
            
    def on_toggled(self, w):
        self.set_title(w._name)
        self.emit('change', w._id)
