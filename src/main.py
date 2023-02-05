# main.py
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

from .pipewire.pipewire import Pipewire
from .Preferences import WhisperPreferencesWindow
from .window import WhisperWindow
from .utils.utils import make_option, link_output_input
from gi.repository import Gtk, Gio, Adw, GLib
import json
import sys
import logging
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

LOG_FILE = GLib.get_user_cache_dir() + '/logs/whisper.log'


class WhisperApplication(Adw.Application):
    """The main application singleton class."""

    def __init__(self, version):
        super().__init__(application_id='it.mijorus.whisper', flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.version = version
        self.create_action('about', self.on_about_action)
        self.create_action('preferences', self.on_preferences_action)
        self.create_action('opendebuglog', self.on_opendebuglog_action)
        self.create_action('translate', lambda w, _: Gio.AppInfo.launch_default_for_uri('https://github.com/mijorus/whisper/tree/master/po', None))

        self.add_main_option_entries([
            make_option('autostart'),
            make_option('version')
        ])

        self.connect('shutdown', self.on_query_end)

    def on_query_end(self, app):
        pass

    def do_activate(self):
        """Called when the application is activated.

        We raise the application's main window, creating it if
        necessary.
        """
        win = self.props.active_window
        if not win:
            last_config = []
            with open(GLib.get_user_data_dir() + '/last_connections.json', 'r') as f:
                try:
                    last_config = json.loads(f.read())
                    last_config = last_config if last_config else []
                except Exception as e:
                    pass

            win = WhisperWindow(application=self)
            win.start_with_config(last_config)

            # with open(GLib.get_user_data_dir() + '/last_connections.json', 'w+') as f:
            #     f.write('[]')

        win.present()

    def do_handle_local_options(self, options):
        if options.contains('version'):
            print(self.version)
            return 0

        self.autostarting = options.contains('autostart')
        if self.autostarting:
            logging.info('Starting whisper with --autostart (usually after reboot)')

        return -1

    def on_about_action(self, widget, _):
        """Callback for the app.about action."""
        about = Adw.AboutWindow(
            transient_for=self.props.active_window,
            application_name='Whisper',
            website='https://github.com/mijorus/whisper',
            issue_url='https://github.com/mijorus/whisper/issues',
            comments='Listen to your mic',
            application_icon='it.mijorus.whisper',
            developer_name='Lorenzo Paderi',
            version=self.version,
            developers=['Lorenzo Paderi'],
            copyright='© 2023 Lorenzo Paderi'
        )

        about.add_credit_section('Icon', ['Jakub Steiner (jimmac)'])

        about.present()

    def on_preferences_action(self, widget, _):
        """Callback for the app.preferences action."""
        window = WhisperPreferencesWindow(transient_for=self.props.active_window)
        window.present()

    def on_opendebuglog_action(self, widget, _):
        Gio.AppInfo.launch_default_for_uri(
            f'file://' + LOG_FILE.split("/whisper.log")[0],
            None
        )

    def create_action(self, name, callback, shortcuts=None):
        """Add an application action.

        Args:
            name: the name of the action
            callback: the function to be called when the action is activated
            shortcuts: an optional list of accelerators
        """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)


def main(version):
    """The application's entry point."""
    app = WhisperApplication(version=version)

    if not GLib.file_test(GLib.get_user_cache_dir() + '/logs', GLib.FileTest.EXISTS):
        GLib.mkdir_with_parents(GLib.get_user_cache_dir() + '/logs', 0o755)

    with open(LOG_FILE, 'w+') as f:
        f.write('')

    logging.basicConfig(
        filename=LOG_FILE,
        filemode='a',
        encoding='utf-8',
        level=logging.DEBUG,
        format='%(levelname)s - %(message)s\n',
        force=True
    )

    print('Logging to file: ' + LOG_FILE)
    return app.run(sys.argv)
