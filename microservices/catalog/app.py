import os
import sqlite3
from flask import Flask, jsonify, request

app = Flask(__name__)
DB = os.environ.get("DB_PATH", "/data/catalog.db")


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    with get_db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL)""")
        if c.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
            c.executemany(
                "INSERT INTO products (name, price, stock) VALUES (?, ?, ?)",
                [("Clavier", 29.9, 50), ("Souris", 15.5, 100), ("Ecran 24 pouces", 139.0, 20)])


init_db()


@app.get("/health")
def health():
    return jsonify({"service": "catalog", "status": "ok"})


@app.get("/products")
def list_products():
    with get_db() as c:
        rows = c.execute("SELECT * FROM products").fetchall()
    return jsonify([dict(r) for r in rows])


@app.get("/products/<int:pid>")
def get_product(pid):
    with get_db() as c:
        row = c.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
    if row is None:
        return jsonify({"error": "Produit introuvable"}), 404
    return jsonify(dict(row))


@app.post("/products")
def add_product():
    data = request.get_json(silent=True) or {}
    if not data.get("name") or "price" not in data:
        return jsonify({"error": "name et price sont obligatoires"}), 400
    with get_db() as c:
        cur = c.execute("INSERT INTO products (name, price, stock) VALUES (?, ?, ?)",
                        (data["name"], data["price"], data.get("stock", 0)))
    return jsonify({"id": cur.lastrowid, **data}), 201


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
