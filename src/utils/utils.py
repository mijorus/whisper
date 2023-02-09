import logging
import gi
from ..pipewire.pipewire import Pipewire

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Gio, Adw, GLib  # noqa

# thank you mate ❤️
# https://github.com/gtimelog/gtimelog/blob/6e4b07b58c730777dbdb00b3b85291139f8b10aa/src/gtimelog/main.py#L159


def make_option(long_name, short_name=None, flags=0, arg=GLib.OptionArg.NONE, arg_data=None, description=None, arg_description=None):
    # surely something like this should exist inside PyGObject itself?!
    option = GLib.OptionEntry()
    option.long_name = long_name.lstrip('-')
    option.short_name = 0 if not short_name else short_name.lstrip('-')
    option.flags = flags
    option.arg = arg
    option.arg_data = arg_data
    option.description = description
    option.arg_description = arg_description
    return option


def array_diff(listA, listB):
    return set(listA) - set(listB) | set(listB) - set(listA)


def link_output_input(output_id: str, input_id: str):
    logging.info(f'Linking {output_id} with {input_id}')
    pw_output = Pipewire.list_outputs()[output_id]
    if (len(pw_output.channels) == 1) and ('_MONO' in pw_output.channels[list(pw_output.channels.keys())[0]]):
        # handle MONO mics
        for ch_id, ch_name in Pipewire.list_inputs()[input_id].channels.items():
            if ('_FL' in ch_name) or ('_FR' in ch_name):
                Pipewire.link(list(pw_output.channels.keys())[0], ch_id)
    else:
        pw_input = Pipewire.list_inputs()[input_id]
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
