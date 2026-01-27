import re
import json
import yaml
import logging
from pathlib import Path
from flask import Flask, render_template, jsonify
from mcrcon import MCRcon

logging.basicConfig(level=logging.INFO)

BASE = Path(__file__).parent
CONFIG_PATH = BASE / "config.yml"

if not CONFIG_PATH.exists():
    raise SystemExit("config.yml not found. Please create it from README example.")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

app = Flask(__name__)
DATA_CACHE = {}
RE_JSON_CONTENT = re.compile(r"(\[.*\]|\{.*\})", re.S)
RE_UNQUOTED_KEYS = re.compile(r'([{,]\s*)([A-Za-z0-9_\-+]+)\s*:')

def parse_storage_output(text: str):
    if not text:
        return []
    m = RE_JSON_CONTENT.search(text)
    s = m.group(1) if m else text
    s = s.strip()
    s = s.replace("'", '"')
    s = RE_UNQUOTED_KEYS.sub(r'\1"\2":', s)
    try:
        return json.loads(s)
    except Exception:
        logging.exception("Failed to parse storage text. Raw data: %s", text)
        return []


def fetch_storage_for_score(score_key: str):
    global DATA_CACHE
    rconf = config.get("rcon", {})
    host = rconf.get("host", "localhost")
    port = int(rconf.get("port", 25575))
    password = rconf.get("password", "")
    cmd = f"data get storage syk9lib: scoretostorage.result.{score_key}"
    try:
        with MCRcon(host, password, port, timeout=1) as m:
                resp = m.command(cmd)
                data = parse_storage_output(resp)
                if data:
                    DATA_CACHE[score_key] = data
                return data
    except Exception as e:
        logging.warning(f"RCON failed for {score_key}: {e}. Using cached data.")
        return DATA_CACHE.get(score_key, [])


def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours}:{minutes:02d}:{secs:05.2f}"


def get_rankings():
    out = {}
    scores = config.get("scores", [])
    for score in scores:
        key = score["key"]
        title = score.get("title", key)
        items = []
        data = fetch_storage_for_score(key) or []
        is_time = score.get("time", False)
        for entry in data:
            for player, val in entry.items():
                try:
                    v = int(val)
                except Exception:
                    try:
                        v = int(float(val))
                    except Exception:
                        v = 0
                if is_time:
                    seconds = v / 20.0
                    formatted_value = format_time(seconds)
                else:
                    formatted_value = f"{v:,}"
                items.append({"player": player, "value": v, "formatted_value": formatted_value})
        reverse = score.get("sort", 0) == 0
        items.sort(key=lambda x: x["value"], reverse=reverse)
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
