#!/usr/bin/env python3
import glob
import json
import subprocess

def out(text, tooltip="", css_class="gpu"):
    print(json.dumps({"text": text, "tooltip": tooltip, "class": css_class}, ensure_ascii=False))

def read_file(path):
    try:
        return open(path, "r").read().strip()
    except Exception:
        return None

def try_nvidia():
    try:
        result = subprocess.run([
            "nvidia-smi",
            "--query-gpu=utilization.gpu,temperature.gpu,memory.used,memory.total",
            "--format=csv,noheader,nounits",
        ], capture_output=True, text=True, timeout=0.5)
        if result.returncode != 0 or not result.stdout.strip():
            return None
        util, temp, mem_used, mem_total = [x.strip() for x in result.stdout.strip().splitlines()[0].split(",")]
        return {"util": int(float(util)), "temp": int(float(temp)), "mem_used": int(float(mem_used)), "mem_total": int(float(mem_total)), "name": "NVIDIA"}
    except Exception:
        return None

def try_drm_sysfs():
    busy_paths = glob.glob("/sys/class/drm/card*/device/gpu_busy_percent")
    temp_paths = glob.glob("/sys/class/drm/card*/device/hwmon/hwmon*/temp*_input")
    util = None
    temp = None
    for path in busy_paths:
        value = read_file(path)
        if value is not None:
            try:
                util = int(float(value))
                break
            except Exception:
                pass
    temps = []
    for path in temp_paths:
        value = read_file(path)
        if value is None:
            continue
        try:
            t = int(value) / 1000.0
            if 10 <= t <= 120:
                temps.append(t)
        except Exception:
            pass
    if temps:
        temp = int(max(temps))
    if util is None and temp is None:
        return None
    return {"util": util, "temp": temp, "mem_used": None, "mem_total": None, "name": "GPU"}

def main():
    data = try_nvidia() or try_drm_sysfs()
    if not data:
        out("GPU —", "GPU telemetry unavailable", "gpu unknown")
        return
    util = data["util"]
    temp = data["temp"]
    util_text = f"{util}%" if util is not None else "—%"
    temp_text = f"{temp}°C" if temp is not None else "—°C"
    text = f"󰢮  {util_text} {temp_text}"
    tooltip = f"{data['name']}\nLoad: {util_text}\nTemp: {temp_text}"
    if data.get("mem_used") is not None and data.get("mem_total") is not None:
        tooltip += f"\nVRAM: {data['mem_used']} / {data['mem_total']} MiB"
    css_class = "gpu"
    if temp is not None and temp >= 82:
        css_class += " critical"
    elif temp is not None and temp >= 72:
        css_class += " warning"
    out(text, tooltip, css_class)

if __name__ == "__main__":
    main()