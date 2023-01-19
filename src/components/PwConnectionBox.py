import pulsectl
from gi.repository import Adw, Gtk, Gio
from pprint import pprint
from .ExpanderRowRadio import ExpanderRowRadio
from ..pipewire.pipewire import Pipewire


class PwConnectionBox(Adw.PreferencesGroup):
    def __init__(self, new_connection_cb: callable, **kwargs):
        super().__init__(title='Create a connection')
        self.new_connection_cb = new_connection_cb
        self.settings: Gio.Settings = Gio.Settings.new('it.mijorus.whisper')

        self.output_select = Adw.ExpanderRow(title=' -- Select a microphone --')

        output_names = []
        radio_buttons = []
        for k, v in Pipewire.list_outputs().items():
            if v.alsa.startswith('alsa:') and ('capture' in v.alsa):
                radio_buttons.append(Gtk.CheckButton())
                row = Adw.ActionRow(activatable_widget=radio_buttons[-1], title=v.name)
                row.add_prefix(radio_buttons[-1])

                output_names.append(v.name)
                self.output_select.add_row(row)

        self.input_select = Adw.ExpanderRow(title=' -- Select a speaker --')

        if len(radio_buttons) > 1:
            for r in radio_buttons[1:]:
                r.set_group(radio_buttons[0])

        radio_buttons = []
        for k, v in Pipewire.list_inputs().items():
            if (v.alsa.startswith('alsa:')):
                name = v.name if (v.name not in output_names) else (v.name + ' - Output')

                radio_buttons.append(Gtk.CheckButton()) 
                row = Adw.ActionRow(activatable_widget=radio_buttons[-1], title=name)
                row.add_prefix(radio_buttons[-1])
                self.input_select.add_row(row)

        if len(radio_buttons) > 1:
            for r in radio_buttons[1:]:
                r.set_group(radio_buttons[0])

        self.add(self.output_select)
        self.add(self.input_select)

        connect_btn = Gtk.Button(label='Connect', css_classes=['suggested-action'])
        connect_btn.connect('clicked', self.connect_source)
        self.set_header_suffix(connect_btn)

    def connect_source(self, widget):
        if self.settings.get_boolean('stand-by'):
            return

        self.settings.set_boolean('stand-by', True)

        try:
            if not self.output_select.get_active_id() or not self.input_select.get_active_id():
                return

            pw_output = Pipewire.list_outputs()[self.output_select.get_active_id()]
            if (len(pw_output.channels) == 1) and ('_MONO' in pw_output.channels[list(pw_output.channels.keys())[0]]):
                # handle MONO mics
                for ch_id, ch_name in Pipewire.list_inputs()[self.input_select.get_active_id()].channels.items():
                    if ('_FL' in ch_name) or ('_FR' in ch_name):
                        Pipewire.link(list(pw_output.channels.keys())[0], ch_id)
            else:
                pw_input = Pipewire.list_inputs()[self.input_select.get_active_id()]
                fl_fr = [None, None]

                for c, channel in pw_input.channels.items():
                    if (channel.endswith('_FL')):
                        fl_fr[0] = c
                    elif (channel.endswith('_FR')):
                        fl_fr[1] = c

                for c, channel in pw_output.channels.items():
                    if (channel.endswith('_FL')) and fl_fr[0]:
                        Pipewire.link(c, fl_fr[0])
                    elif (channel.endswith('_FR')) and fl_fr[1]:
                        Pipewire.link(c, fl_fr[1])

            self.new_connection_cb()
        except Exception as e:
            print(e)
        finally:
            self.settings.set_boolean('stand-by', False)
            self.input_select.set_active_id('')
            self.output_select.set_active_id('')
