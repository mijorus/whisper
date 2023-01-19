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
from gi.repository import Gtk
from pprint import pprint
from ..utils import async_utils
from ..pipewire.pipewire import Pipewire, PwLink


class ExpanderRowRadio(Adw.ExpanderRow):
    def __init__(self, row_id: str, **kwargs):
        super().__init__(**kwargs)
        self.row_id = row_id
        self.radio_buttons = []

    def get_active_id(self):
        pass

    def add(self, w, _id):
        radio = Gtk.CheckButton()
        radio.__id = _id

        row = Adw.ActionRow(activatable_widget=radio, title=name)
        row.add_prefix(radio)

        self.add_row(row)
        self.radio_buttons.append(radio)