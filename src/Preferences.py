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

        self.show_ids = Adw.ActionRow(title=_('Show connection IDs'), subtitle=_('For the geeks out there'))
        self.show_ids_switch = Gtk.Switch(valign=Gtk.Align.CENTER)
        self.show_ids.add_suffix(self.show_ids_switch)

        self.settings.bind('show-connection-ids', self.show_ids_switch, 'state', Gio.SettingsBindFlags.DEFAULT)
        
        self.general_page_general.add(self.show_ids)
        self.general_page.add(self.general_page_general)

        self.add(self.general_page)
