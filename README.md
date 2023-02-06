# Whisper - Listen to your microphone

<p align="center">
<img src="docs/it.mijorus.whisper.svg">
</p>

Whisper allows you to listen to your microphone through your speakers. It's useful for testing your microphone or for listening to your voice.

This app requires both PulseAudio and Pipewire to be installed on your system.

Pirewire is available as the default audio server on 
- Fedora 34 and later
- Ubuntu 22.04 and later


## Installation

```bash
flatpak kill it.mijorus.smile
flatpak-builder build/ it.mijorus.whisper.json --user --install --force-clean
```

## Building

Whisper can be built with Flatpak Builder

## Source
<a href="https://github.com/mijorus/whisper" align="center">
  <img width="100" src="https://github.githubassets.com/images/modules/logos_page/GitHub-Logo.png">
</a>

## Credits

- Icon: Jakub Steiner (jimmac)

## Similar apps

- [Helvum](https://gitlab.freedesktop.org/pipewire/helvum)
- [qpwgraph](https://flathub.org/apps/details/org.rncbc.qpwgraph)

## Under the hood
This app does more or less the same thing as Helvum does, but with a simple UI: when you have more than a couple of apps playing audio, it gets quite hard to use Helvum.

Futhermore, Whisper shows only phisical inputs, while the afroamentioned show all inputs, including audio streams created by apps and virtual ones.

Whisper can also control the microphone gain and the speaker volume.
## Screenshots

<p align="center">
<img src="docs/img1.png">
</p>
<p align="center">
<img src="docs/img4.png">
</p>
<p align="center">
<img src="docs/img3.png">
</p>
