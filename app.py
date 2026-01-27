import re
import json
import yaml
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from flask import Flask, render_template, jsonify

# 外部ライブラリのインポート（利用不可時のハンドリング）
try:
    from mcrcon import MCRcon
except ImportError:
    MCRcon = None

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.yml"


class ConfigLoader:
    """設定ファイルを読み込むクラス"""
    @staticmethod
    def load(path: Path) -> Dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"{path.name} not found. Please create it from README example.")
        
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}


class MinecraftClient:
    """MinecraftサーバーとのRCON通信を担当するクラス"""
    def __init__(self, rcon_config: Dict[str, Any]):
        self.host = rcon_config.get("host", "localhost")
        self.port = int(rcon_config.get("port", 25575))
        self.password = rcon_config.get("password", "")

    def fetch_storage_data(self, score_key: str) -> str:
        if MCRcon is None:
            logger.error("mcrcon library not installed.")
            return ""

        cmd = f"data get storage syk9lib: scoretostorage.result.{score_key}"
        
        try:
            with MCRcon(self.host, self.password, self.port) as mcr:
                response = mcr.command(cmd)
                return response
        except Exception as e:
            logger.error(f"RCON connection failed for {score_key}: {e}")
            return ""


class DataParser:
    """Minecraftの出力文字列を解析するクラス"""
    @staticmethod
    def parse_storage_output(text: str) -> List[Dict[str, Any]]:
        if not text:
            return []
        
        # 配列部分 [...] を抽出
        match = re.search(r"(\[.*\])", text, re.S)
        raw_content = match.group(1) if match else text
        
        s = raw_content.strip()
        s = s.replace("'", '"')
        
        # 引用符で囲まれていないキーをJSON形式（"key":）に変換
        # 注意: 値が文字列の場合の処理は簡易的なまま維持しています
        s = re.sub(r'([{,]\s*)([A-Za-z0-9_\-+]+)\s*:', r'\1"\2":', s)
        
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            logger.exception(f"Failed to parse storage text: {s[:100]}...")
            return []


class ScoreService:
    """スコアデータの加工・ランキング生成を担当するクラス"""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = MinecraftClient(config.get("rcon", {}))

    @staticmethod
    def format_time(ticks: float) -> str:
        seconds = ticks / 20.0
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}:{minutes:02d}:{secs:05.2f}"

    def _process_value(self, val: Any) -> Union[int, float]:
        """値を数値に変換する"""
        try:
            return int(val)
        except (ValueError, TypeError):
            try:
                return int(float(val))
            except (ValueError, TypeError):
                return 0

    def get_rankings(self) -> Dict[str, List[Dict[str, Any]]]:
        rankings = {}
        scores_config = self.config.get("scores", [])

        for score_conf in scores_config:
            key = score_conf["key"]
            title = score_conf.get("title", key)
            is_time_format = score_conf.get("time", False)
            sort_descending = score_conf.get("sort", 0) == 0  # 0 usually means descending in typical logic

            # データ取得
            raw_text = self.client.fetch_storage_data(key)
            parsed_data = DataParser.parse_storage_output(raw_text)

            items = []
            for entry in parsed_data:
                for player, val in entry.items():
                    numeric_val = self._process_value(val)
                    
                    if is_time_format:
                        formatted_val = self.format_time(numeric_val)
                    else:
                        formatted_val = str(numeric_val)

                    items.append({
                        "player": player, 
                        "value": numeric_val, 
                        "formatted_value": formatted_val
                    })

            # ソート
            items.sort(key=lambda x: x["value"], reverse=sort_descending)
            rankings[title] = items
        
        return rankings


# --- Flask Application Setup ---

def create_app():
    app = Flask(__name__)
    
    # 設定のロード
    try:
        config = ConfigLoader.load(CONFIG_PATH)
    except Exception as e:
        logger.critical(e)
        return app # 起動はするがエラーになる可能性あり（あるいはここでsys.exit）

    score_service = ScoreService(config)

    @app.route("/")
    def index():
        rankings = score_service.get_rankings()
        return render_template(
            "index.html", 
            rankings=rankings, 
            refresh_rate=config.get("refresh_rate", 0),
            page_title=config.get("page_title", "Score Rankings")
        )

    @app.route("/refresh", methods=["POST"])
    def refresh():
        # HTMLからのPOSTリフレッシュ用（indexと同じ処理）
        return index()

    @app.route('/api/refresh')
    def api_refresh():
        rankings = score_service.get_rankings()
        return jsonify({'rankings': rankings})

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000)