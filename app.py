import re
import json
import yaml
import logging
from pathlib import Path

from flask import Flask, render_template
from flask import request, redirect, url_for, jsonify

try:
    from mcrcon import MCRcon
except Exception:
    MCRcon = None

logging.basicConfig(level=logging.INFO)

BASE = Path(__file__).parent
CONFIG_PATH = BASE / "config.yaml"

if not CONFIG_PATH.exists():
    raise SystemExit("config.yaml not found. Please create it from README example.")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

app = Flask(__name__)


def parse_storage_output(text: str):
    if not text:
        return []
    m = re.search(r"(\[.*\])", text, re.S)
    s = m.group(1) if m else text
    s = s.strip()
    s = s.replace("'", '"')
    s = re.sub(r'([{,]\s*)([A-Za-z0-9_\-+]+)\s*:', r'\1"\2":', s)
    try:
        return json.loads(s)
    except Exception:
        logging.exception("Failed to parse storage text: %s", s)
        return []


def fetch_storage_for_score(score_key: str):
    if MCRcon is None:
        logging.error("mcrcon library not available. Install via requirements.txt")
        return []
    rconf = config.get("rcon", {})
    host = rconf.get("host", "localhost")
    port = int(rconf.get("port", 25575))
    password = rconf.get("password", "")
    cmd = f"data get storage syk9lib: scoretostorage.result.{score_key}"
    try:
        try:
            with MCRcon(host, password, port) as m:
                try:
                    resp = m.command(cmd)
                except AttributeError:
                    resp = m.sendCommand(cmd)
        except SystemExit:
            logging.error("mcrcon raised SystemExit (likely connection failure) for %s:%s", host, port)
            return []
    except Exception:
        logging.exception("Failed mcrcon for score %s", score_key)
        return []
    return parse_storage_output(resp)


def get_rankings():
    out = {}
    scores = config.get("scores", [])
    for score in scores:
        key = score["key"]
        title = score.get("title", key)
        items = []
        data = fetch_storage_for_score(key) or []
        for entry in data:
            for player, val in entry.items():
                try:
                    v = int(val)
                except Exception:
                    try:
                        v = int(float(val))
                    except Exception:
                        v = 0
                items.append({"player": player, "value": v})
        items.sort(key=lambda x: x["value"], reverse=True)
        out[title] = items
    return out


@app.route("/")
def index():
    rankings = get_rankings()
    refresh_rate = config.get("refresh_rate", 0)
    page_title = config.get("page_title", "Score Rankings")
    return render_template("index.html", rankings=rankings, refresh_rate=refresh_rate, page_title=page_title)


@app.route("/refresh", methods=["POST"])
def refresh():
    rankings = get_rankings()
    refresh_rate = config.get("refresh_rate", 0)
    page_title = config.get("page_title", "Score Rankings")
    return render_template("index.html", rankings=rankings, refresh_rate=refresh_rate, page_title=page_title)


@app.route('/api/refresh')
def api_refresh():
    rankings = get_rankings()
    return jsonify({'rankings': rankings})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
