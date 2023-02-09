import pulsectl
from gi.repository import Adw, Gtk, Gio, GObject
from pprint import pprint
from .ExpanderRowRadio import ExpanderRowRadio
from ..pipewire.pipewire import Pipewire
from ..utils.utils import link_output_input


class PwConnectionBox(Adw.PreferencesGroup):
    __gsignals__ = {
        'new_connection': (GObject.SIGNAL_RUN_FIRST, None, (str, str, ))
    }

    def __init__(self, **kwargs):
        super().__init__(title=_('Create a connection'))
        self.settings: Gio.Settings = Gio.Settings.new('it.mijorus.whisper')

        self.output_select = ExpanderRowRadio(title=_(' -- Select a microphone --'))
        self.output_select.connect('change', self.on_output_select_change)

        output_names = []
        for k, v in Pipewire.list_outputs().items():
            # Hardcoded, there as some issues with bluetooth mics for now
            is_bluetooth = False 
            if (v.alsa.startswith('alsa:') or is_bluetooth):
                if is_bluetooth or (('capture' in v.alsa) and (v.name != 'Midi Through')):
                    output_names.append(v.name)

                    if self.settings.get_boolean('show-connection-ids'):
                        self.output_select.add(v.name, k, v.alsa)
                    else:
                        self.output_select.add(v.name, k)

        self.input_select = ExpanderRowRadio(title=_(' -- Select a speaker --'))
        self.input_select.connect('change', self.on_input_select_change)

        for k, v in Pipewire.list_inputs().items():
            is_bluetooth = v.resource_name.startswith('bluez_output')
            if (v.alsa.startswith('alsa:') or is_bluetooth):
                if is_bluetooth or (v.name != 'Midi Through'):
                    name = v.name if (v.name not in output_names) else (v.name + ' - Output')

                    if self.settings.get_boolean('show-connection-ids'):
                        self.input_select.add(name, k, v.alsa)
                    else:
                        self.input_select.add(name, k)

        self.add(self.output_select)
        self.add(self.input_select)

        self.connect_btn = Gtk.Button(label=_('Connect'), css_classes=['suggested-action'], sensitive=False)
        self.connect_btn.connect('clicked', self.connect_source)
        self.set_header_suffix(self.connect_btn)

    def connect_source(self, widget):
        if self.settings.get_boolean('stand-by'):
            return

        self.settings.set_boolean('stand-by', True)

        try:
            if not self.output_select.get_active_id() or not self.input_select.get_active_id():
                return

            link_output_input(self.output_select.get_active_id(), self.input_select.get_active_id())

            self.emit('new_connection', self.output_select.get_active_id(), self.input_select.get_active_id())
        except Exception as e:
            print(e)
        finally:
            self.settings.set_boolean('stand-by', False)
            self.input_select.set_active_id('')
            self.output_select.set_active_id('')

            self.input_select.set_expanded(False)
            self.output_select.set_expanded(False)

            for radio in self.input_select.radio_buttons:
                radio.set_sensitive(True)
                radio.get_parent().get_parent().set_opacity(1)

    def on_output_select_change(self, _, _id: str):
        links = Pipewire.list_links()
        pw_output = Pipewire.list_outputs()[_id]

        for radio in self.input_select.radio_buttons:
            radio.set_sensitive(True)
            radio.get_parent().get_parent().set_opacity(1)

        for o in pw_output.channels:
            if not o in links:
                continue

            for i, active_c_link in links[o].items():
                for radio in self.input_select.radio_buttons:
                    if radio._id == active_c_link.connected_tag:
                        radio.set_sensitive(False)
                        radio.get_parent().get_parent().set_opacity(0.5)
                        self.input_select.set_active_id('')
                        break

        self.on_any_select_change()

    def on_input_select_change(self, _, _id: str):
        self.on_any_select_change()

    def on_any_select_change(self):
        if self.input_select.get_active_id() and self.output_select.get_active_id():
            self.connect_btn.set_sensitive(True)
        else:
            self.connect_btn.set_sensitive(False)
