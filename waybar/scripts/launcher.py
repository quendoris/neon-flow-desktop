#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys

# Launcher configuration
APPS = [
    {"id": "terminal", "icon": "", "tooltip": "Терминал", "cmd": "kitty || alacritty || foot || wezterm", "match": ["kitty", "alacritty", "foot", "wezterm", "org.wezfurlong.wezterm", "ghostty"]},
    {"id": "files", "icon": "", "tooltip": "Файлы", "cmd": "thunar || dolphin || nautilus || nemo", "match": ["thunar", "dolphin", "org.kde.dolphin", "nautilus", "org.gnome.nautilus", "nemo", "pcmanfm"]},
    {"id": "browser", "icon": "󰈹", "tooltip": "Браузер", "cmd": "firefox", "match": ["firefox", "librewolf", "brave-browser", "chromium", "google-chrome"]},
    {"id": "tor", "icon": "󰕥", "tooltip": "Tor Browser", "cmd": "gtk-launch start-tor-browser.desktop || gtk-launch torbrowser.desktop || tor-browser", "match": ["tor browser", "torbrowser", "start-tor-browser", "org.torproject.torbrowser"]}
]

LEFT_RESERVED_PX = 320
RIGHT_RESERVED_PX = 980
SAFETY_PX = 220
ICON_WIDTH_PX = 34
MAX_VISIBLE_ICONS = 4
MIN_WIDTH_FOR_ANY_ICON = 1680


def out(text, tooltip="", css_class="launcher"):
    print(json.dumps({"text": text, "tooltip": tooltip, "class": css_class}, ensure_ascii=False))


def run_shell(command):
    subprocess.Popen(["bash", "-lc", command], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


def hyprctl_json(*args):
    try:
        result = subprocess.run(["hyprctl", *args, "-j"], capture_output=True, text=True, timeout=0.5)
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
    except Exception:
        pass
    return None


def get_monitor_width():
    monitors = hyprctl_json("monitors") or []
    output_name = os.environ.get("WAYBAR_OUTPUT_NAME") or os.environ.get("WAYBAR_OUTPUT") or os.environ.get("OUTPUT")
    if output_name:
        for mon in monitors:
            if mon.get("name") == output_name:
                return int(mon.get("width") or 1280)
    for mon in monitors:
        if mon.get("focused"):
            return int(mon.get("width") or 1280)
    if monitors:
        return int(max(mon.get("width") or 1280 for mon in monitors))
    return 1280


def visible_icon_count():
    width = get_monitor_width()
    if width < MIN_WIDTH_FOR_ANY_ICON:
        return 0
    available = width - LEFT_RESERVED_PX - RIGHT_RESERVED_PX - SAFETY_PX
    count = available // ICON_WIDTH_PX
    return max(0, min(MAX_VISIBLE_ICONS, int(count)))


def app_index(app_id):
    for i, app in enumerate(APPS):
        if app["id"] == app_id:
            return i
    return -1


def app_by_id(app_id):
    for app in APPS:
        if app["id"] == app_id:
            return app
    return None


def client_text(client):
    parts = [client.get("class", ""), client.get("initialClass", ""), client.get("title", ""), client.get("initialTitle", "")]
    return " ".join(str(x).lower() for x in parts if x)


def app_state(app):
    clients = hyprctl_json("clients") or []
    active_window = hyprctl_json("activewindow") or {}
    matches = [m.lower() for m in app.get("match", [])]
    active_text = client_text(active_window)
    opened = False
    focused = False
    for client in clients:
        text = client_text(client)
        if any(m in text for m in matches):
            opened = True
            if active_text and any(m in active_text for m in matches):
                focused = True
            break
    return opened, focused


def open_menu():
    candidates = [("wofi", "wofi --show drun"), ("rofi", "rofi -show drun"), ("fuzzel", "fuzzel"), ("bemenu-run", "bemenu-run")]
    for binary, command in candidates:
        if shutil.which(binary):
            run_shell(command)
            return
    run_shell("kitty || alacritty || foot || wezterm")


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "show"
    app_id = sys.argv[2] if len(sys.argv) > 2 else "plus"
    if action == "show":
        if app_id == "plus":
            out("", "Меню приложений", "launcher plus")
            return
        app = app_by_id(app_id)
        if not app:
            out("", "", "hidden")
            return
        opened, focused = app_state(app)
        css = f"launcher {app_id}"
        tooltip = app["tooltip"]
        if opened:
            css += " opened"
            tooltip += " · открыто"
        if focused:
            css += " focused"
            tooltip += " · активно"
        out(app["icon"], tooltip, css)
        return
    if action == "visible":
        if app_id == "plus":
            sys.exit(0)
        idx = app_index(app_id)
        if idx < 0:
            sys.exit(1)
        sys.exit(0 if idx < visible_icon_count() else 1)
    if action == "launch":
        if app_id == "plus":
            open_menu()
            return
        app = app_by_id(app_id)
        if app:
            run_shell(app["cmd"])
        return

if __name__ == "__main__":
    main()