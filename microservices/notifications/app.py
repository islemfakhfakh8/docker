import os
import sqlite3
from datetime import datetime, timezone
from flask import Flask, jsonify, request

app = Flask(__name__)
DB = os.environ.get("DB_PATH", "/data/notifications.db")


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    with get_db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipient TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL)""")


init_db()


@app.get("/health")
def health():
    return jsonify({"service": "notifications", "status": "ok"})


@app.post("/notify")
def notify():
    data = request.get_json(silent=True) or {}
    if not data.get("recipient") or not data.get("message"):
        return jsonify({"error": "recipient et message sont obligatoires"}), 400
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as c:
        cur = c.execute(
            "INSERT INTO notifications (recipient, message, created_at) VALUES (?, ?, ?)",
            (data["recipient"], data["message"], now))
    print(f"[NOTIFICATION] to={data['recipient']} : {data['message']}", flush=True)
    return jsonify({"id": cur.lastrowid, "status": "sent"}), 201


@app.get("/notifications")
def list_notifications():
    with get_db() as c:
        rows = c.execute("SELECT * FROM notifications ORDER BY id DESC").fetchall()
    return jsonify([dict(r) for r in rows])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
