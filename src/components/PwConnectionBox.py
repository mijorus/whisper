from gi.repository import Adw, Gtk, Gio
from pprint import pprint
from ..pipewire.pipewire import Pipewire


class PwConnectionBox(Gtk.Box):
    def __init__(self, new_connection_cb: callable, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.new_connection_cb = new_connection_cb
        self.settings: Gio.Settings = Gio.Settings.new('it.mijorus.whisper')

        pw_connection_box_row = Gtk.Box(spacing=10)

        self.output_select = Gtk.ComboBoxText()
        self.output_select.append('', ' -- Select a microphone --')
        self.output_select.set_active_id('')

        output_names = []
        for k, v in Pipewire.list_outputs().items():
            if v.alsa.startswith('alsa:') and ('capture' in v.alsa):
                self.output_select.append(k, v.name)
                output_names.append(v.name)

        self.input_select = Gtk.ComboBoxText()
        self.input_select.append('', ' -- Select a speaker --')
        self.input_select.set_active_id('')

        for k, v in Pipewire.list_inputs().items():
            if (v.alsa.startswith('alsa:')):
                name = v.name if (v.name) not in output_names else (v.name + ' - Output')
                self.input_select.append(k, name)

        pw_connection_box_row.append(self.output_select)
        pw_connection_box_row.append(self.input_select)
        connect_button = Gtk.Button(label='Connect')
        connect_button.connect('clicked', self.connect_source)

        self.append(pw_connection_box_row)
        self.append(connect_button)

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
