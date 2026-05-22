# Waybar addon

This directory contains an optional Waybar setup that pairs with `neon-flow-desktop`.

The idea is simple: keep the animated background clean and move practical information into Waybar.

## Included modules

- Existing left-side clock can be kept as-is.
- Center adaptive launcher capsule:
  - terminal
  - files
  - browser
  - Tor Browser
  - plus button for the application menu
- Right-side telemetry and rates:
  - BTC/USDT
  - USD/RUB
  - EUR/RUB
  - GPU usage and temperature
  - CPU usage
  - RAM usage
  - temperature
  - battery / charging state
  - network state
  - volume
  - tray

## Install dependencies on Arch Linux

```bash
sudo pacman -S --needed waybar curl python lm_sensors ttf-jetbrains-mono-nerd
```

For the plus menu button, install one launcher:

```bash
sudo pacman -S --needed wofi
```

## Copy example files

```bash
mkdir -p ~/.config/waybar/scripts
cp waybar/config.jsonc ~/.config/waybar/config.jsonc
cp waybar/style.css ~/.config/waybar/style.css
cp waybar/scripts/*.py ~/.config/waybar/scripts/
chmod +x ~/.config/waybar/scripts/*.py
```

Restart Waybar:

```bash
pkill waybar 2>/dev/null || true
waybar >/tmp/waybar.log 2>&1 &
```

Check errors:

```bash
cat /tmp/waybar.log
```

## Notes

The launcher uses `hyprctl` to detect open and focused applications. It is tuned for Hyprland.

The rates module uses:

- CBR XML feed for USD/RUB and EUR/RUB.
- Binance public ticker for BTC/USDT.
- Local cache to avoid hitting APIs too often.

The GPU module supports NVIDIA through `nvidia-smi` and AMD/Intel through common DRM sysfs paths.
