import gi
import dbus
import logging

gi.require_version('Adw', '1')
gi.require_version('Gtk', '4.0')

from gi.repository import Adw, Gio, Gtk  # noqa


class WhisperPreferencesWindow(Adw.PreferencesWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.settings = Gio.Settings.new('it.mijorus.whisper')

        self.general_page = Adw.PreferencesPage()
        self.general_page_general = Adw.PreferencesGroup(title=_('General'))
        self.autostart_page = Adw.PreferencesGroup(title=_('Autostart'))

        self.show_ids = self.create_toggle_row(_('Show connection IDs'), _('For the geeks out there'), 'show-connection-ids')

        self.start_onboot = self.create_toggle_row(_('Start on boot'), _('Open Whisper when the system starts'), 'start-on-boot')
        self.release_conn_on_exit = self.create_toggle_row(_('Release connections on close'), _('Closes all the connections created with Whisper when leaving the app'), 'release-links-on-quit')
        self.load_last_conf = self.create_toggle_row(_('Reconnect all the devices at startup'), _('Reload all the connections if they are no longer active. Unplugged devices will be skipped'), 'load-last-config')

        self.autostart_page.add(self.start_onboot)
        self.autostart_page.add(self.load_last_conf)

        self.general_page_general.add(self.show_ids)
        self.general_page_general.add(self.release_conn_on_exit)

        self.general_page.add(self.general_page_general)
        self.general_page.add(self.autostart_page)
        self.settings.connect('changed', self.on_settings_changes)

        self.add(self.general_page)

    def create_toggle_row(self, title, subtitle, key) -> Adw.ActionRow:
        row = Adw.ActionRow(title=title, subtitle=subtitle)
        switch = Gtk.Switch(valign=Gtk.Align.CENTER)
        row.add_suffix(switch)
        self.settings.bind(key, switch, 'state', Gio.SettingsBindFlags.DEFAULT)

        return row

    def on_start_on_boot_changed(self, settings, key: str):
        value: bool = settings.get_boolean(key)

        try:
            bus = dbus.SessionBus()
            obj = bus.get_object("org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop")
            inter = dbus.Interface(obj, "org.freedesktop.portal.Background")
            res = inter.RequestBackground('', {
                'reason': 'Whisper autostart',
                'autostart': value, 'background': value,
                'commandline': dbus.Array(['whisper', '--autostart'])
            })
            
            logging.info(f"Autostart set to {value}")
        except Exception as e:
            settings.set_boolean(key, False)
            logging.error(e)

    def on_settings_changes(self, settings, key: str):
        callback = getattr(self, f"on_{key.replace('-', '_')}_changed", None)

        if callback:
            callback(settings, key)
