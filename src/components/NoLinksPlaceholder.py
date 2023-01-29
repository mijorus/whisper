from gi.repository import Adw
from gi.repository import Gtk, GObject


class NoLinksPlaceholder(Gtk.Box):
    def __init__(self, **kwargs):
        # BTW Github Copilot did this widget for me, without even asking, crazy uh?
        super().__init__(valign=Gtk.Align.CENTER, orientation=Gtk.Orientation.VERTICAL, spacing=5, vexpand=True)

        title = Gtk.Label(css_classes=['title-1'], label=_("No active connections"))
        subt = Gtk.Label(css_classes=['dim-label'], label=_("To get started, connect a microphone and a speaker"))
        icon = Gtk.Image.new_from_icon_name('whisper-info-symbolic')
        icon.set_css_classes(['dim-label'])
        icon.set_pixel_size(100)

        self.append(icon)
        self.append(title)
        self.append(subt)