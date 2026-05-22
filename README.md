# Neon Flow Desktop

Procedural neon Wayland desktop background for Hyprland/wlroots.

`neon-flow-desktop` renders a live GTK4 layer-shell background with blue-noise particles, dynamic non-crossing graph links, mouse impulse physics, smooth downward flow, and animated neon backlight gradients.

## Features

- Wayland layer-shell background window for Hyprland/wlroots
- Blue-noise / Poisson-disc inspired particle distribution
- Dynamic planar nearest-neighbor graph with strict crossing prevention
- Persistent links: stretched connections fade instead of snapping away
- Mouse impulse interaction with trail response
- Downward flow with subtle gravity-like asymmetry
- Cached Cairo star sprites and backlight layers for better performance
- No image wallpaper required

## Dependencies on Arch Linux

```bash
sudo pacman -S --needed gtk4 gtk4-layer-shell python-gobject python-cairo
```

## Quick start

```bash
mkdir -p ~/.config/neon-desktop
cp neon-bg.py ~/.config/neon-desktop/neon-bg.py
chmod +x ~/.config/neon-desktop/neon-bg.py
python ~/.config/neon-desktop/neon-bg.py
```

For Hyprland autostart, add this to `~/.config/hypr/hyprland.conf`:

```ini
exec-once = python ~/.config/neon-desktop/neon-bg.py >/tmp/neon-bg.log 2>&1
```

If you use `hyprpaper`, disable it first so it does not cover the live background layer.

## Mathematical ideas

The visual system is based on a few core ideas:

- **Blue-noise / Poisson-disc distribution** for random-looking but visually balanced particles.
- **Overscan domain** so points and links continue beyond screen edges instead of looking clipped.
- **Dynamic planar nearest-neighbor graph** for non-crossing link structure.
- **Distance-based link brightness** so short links are brighter and long links fade into soft neon threads.
- **Impulse physics** for mouse interaction: the cursor adds velocity rather than directly pulling particles.
- **Damping and gravity-like asymmetry** to keep the flow natural and prevent weightless chaos.
- **Smoothed timestep** to reduce micro-jitter from uneven GTK/GLib frame timing.

## License

MIT License. See [LICENSE](LICENSE).
