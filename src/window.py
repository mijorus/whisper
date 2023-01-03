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
from .components.PwConnectionBox import PwConnectionBox
from .components.PwActiveConnectionBox import PwActiveConnectionBox
from .pipewire.pipewire import Pipewire


class WhisperWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'WhisperWindow'

    def __init__(self, **kwargs):
        super().__init__(**kwargs, title='Whisper')
        self.titlebar = Adw.HeaderBar()
        self.set_titlebar(self.titlebar)
        self.viewport = Gtk.Box(halign=Gtk.Align.CENTER, orientation=Gtk.Orientation.VERTICAL, spacing=30)

        pprint(Pipewire.list_alsa_links())

        pw_connection_box = PwConnectionBox()

        self.viewport.append(pw_connection_box)
        self.viewport.append(PwActiveConnectionBox('test', 'test', 'test', 'test'))

        clamp = Adw.Clamp()
        clamp.set_child(self.viewport)

        self.set_child(clamp)
        self.set_default_size(300, 500)
