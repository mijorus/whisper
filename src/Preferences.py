# create a preferences window with libadwaita

import gi

gi.require_version('Adw', '1')
gi.require_version('Gtk', '4.0')

from gi.repository import Adw, Gio, Gtk  # noqa


class WhisperPreferencesWindow(Adw.PreferencesWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.settings = Gio.Settings.new('it.mijorus.whisper')

        self.general_page = Adw.PreferencesPage()
        self.general_page_general = Adw.PreferencesGroup(title='General')

        self.show_ids = self.create_toggle_row('Show connection IDs', 'Show connection IDs in the connection list', 'show-connection-ids')
        self.start_onboot = self.create_toggle_row('Show connection IDs', 'Show connection IDs in the connection list', 'show-connection-ids')

        self.general_page_general.add(self.show_ids)
        self.general_page.add(self.general_page_general)

        self.add(self.general_page)
        
    def create_toggle_row(self, title, subtitle, key) -> Adw.ActionRow:
        row = Adw.ActionRow(title=title, subtitle=subtitle)
        switch = Gtk.Switch(valign=Gtk.Align.CENTER)
        row.add_suffix(switch)
        self.settings.bind(key, switch, 'state', Gio.SettingsBindFlags.DEFAULT)

        return row
