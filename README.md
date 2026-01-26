# Minecraft storage → Web ranking

これは `mcrcon` を使って Minecraft の `storage` に保存されたデータを取得し、スコアボードごとにランキング表示する簡易 Flask アプリです。

セットアップ

1. `config.yaml` を編集して RCON 接続情報、`storages`（storage 名の配列）、`scores`（表示したいキー一覧）を設定します。

例:

```yaml
rcon:
  host: "127.0.0.1"
  port: 25575
  password: "change_me"

storages:
  - storage1
  - storage2

scores:
  - key: kill
    title: "～KILL RANKING～"
  - key: damage
    title: "～DAMAGE RANKING～"
```

2. ローカル実行

```bash
python -m pip install -r requirements.txt
python app.py
# ブラウザで http://localhost:5000 を開く
```

3. Docker で実行

```bash
docker build -t mc-rankings .
docker run -p 5000:5000 --env-file .env -v $(pwd)/config.yaml:/app/config.yaml mc-rankings
```

挙動
- `data get storage <storage> syk9lib:scoretostorage.result.<score>` を各 `storage` と `score` に対して叩きます。
- 返却される配列（例: [{steve:100,...}, {...}]）はキーがクオートされていないことがあるため、パーサで整形して JSON として読み込みます。
- 各エントリは個別にランキング項目として扱い、値でソートして表示します（プレイヤーを合算しません）。

注意
- `mcrcon` の Python パッケージを利用しています。RCON 接続情報を正しく設定してください。
- 実環境では RCON のパスワードを安全に管理してください。
