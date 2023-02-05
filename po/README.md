# Translating the app

If you want to make a translation, here are some instructions.

First, you need an app to manage translation files. My #1 suggestion is [Poedit](https://poedit.net/)).

Creating a translation starts by adding `<locale_code>.po` file. There is `timeswitch.pot` file which is a template you can copy to begin with.<br/>
If you have never worked with `.po` files before, you can find some help in [gettext manual](https://www.gnu.org/software/gettext/manual/html_node/PO-Files.html). 
You can also use special apps ([GTranslator](https://flathub.org/apps/details/org.gnome.Gtranslator), for example) instead of text editor.

After editing a file with translation, add language code to `LINGUAS` file. Please keep it alphabetically sorted!

You can test your translation in GNOME Builder. Press `Ctrl+Alt+T` to open a terminal inside the app's environment and run:
```
LC_ALL=<LOCALE> /app/bin/whisper
```
where `<LOCALE>` is your locale code (e.g. `it_IT.UTF-8`).


Thanks to:
https://github.com/fsobolev/timeswitch/tree/master/po

## Updating translations

When an update is released, new strings might be added to the app.
With Poedit, you can update translations by opening `<your_language>.pot` file and clicking on `Transations (in the menu bar)` > `Update from POT file`.