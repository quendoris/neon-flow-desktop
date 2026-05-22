#!/usr/bin/env python3
import json
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

CACHE = Path.home() / ".cache" / "waybar-rates.json"
CACHE.parent.mkdir(parents=True, exist_ok=True)
CACHE_TTL = 10 * 60

def out(text, tooltip="", css_class="rates"):
    print(json.dumps({"text": text, "tooltip": tooltip, "class": css_class}, ensure_ascii=False))

def fetch_url(url, timeout=4):
    req = urllib.request.Request(url, headers={"User-Agent": "waybar-rates/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()

def get_cbr_rates():
    data = fetch_url("https://www.cbr.ru/scripts/XML_daily.asp")
    root = ET.fromstring(data)
    result = {}
    for valute in root.findall("Valute"):
        code = valute.findtext("CharCode")
        nominal = int(valute.findtext("Nominal") or "1")
        value = float((valute.findtext("Value") or "0").replace(",", ".")) / nominal
        if code in ("USD", "EUR"):
            result[code] = value
    return result

def get_btc_usdt():
    data = fetch_url("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT")
    parsed = json.loads(data.decode("utf-8"))
    return float(parsed["price"])

def load_cache():
    try:
        parsed = json.loads(CACHE.read_text())
        if time.time() - parsed.get("ts", 0) <= CACHE_TTL:
            return parsed
    except Exception:
        pass
    return None

def save_cache(data):
    try:
        CACHE.write_text(json.dumps(data, ensure_ascii=False))
    except Exception:
        pass

def format_btc(v):
    if v >= 1000:
        return f"{v/1000:.1f}K"
    return f"{v:.0f}"

def main():
    cached = load_cache()
    try:
        fiat = get_cbr_rates()
        btc = get_btc_usdt()
        data = {"ts": time.time(), "usd": fiat["USD"], "eur": fiat["EUR"], "btc": btc}
        save_cache(data)
    except Exception:
        if cached:
            data = cached
        else:
            out("RATES —", "Курсы пока недоступны", "rates error")
            return
    text = f"$ {data['usd']:.1f}  € {data['eur']:.1f}  ₿ {format_btc(data['btc'])}"
    age = int(time.time() - data["ts"])
    tooltip = (f"USD/RUB: {data['usd']:.4f}\nEUR/RUB: {data['eur']:.4f}\nBTC/USDT: {data['btc']:,.2f}\nВозраст данных: {age} сек.").replace(",", " ")
    out(text, tooltip)

if __name__ == "__main__":
    main()