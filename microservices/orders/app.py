import os
import sqlite3
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)
DB = os.environ.get("DB_PATH", "/data/orders.db")
CATALOG_URL = os.environ.get("CATALOG_URL", "http://catalog:5000")
NOTIFICATIONS_URL = os.environ.get("NOTIFICATIONS_URL", "http://notifications:5000")


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    with get_db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            total REAL NOT NULL)""")


init_db()


@app.get("/health")
def health():
    return jsonify({"service": "orders", "status": "ok"})


@app.post("/orders")
def create_order():
    data = request.get_json(silent=True) or {}
    customer = data.get("customer")
    product_id = data.get("product_id")
    quantity = data.get("quantity", 1)
    if not customer or not product_id or quantity < 1:
        return jsonify({"error": "customer, product_id et quantity (>=1) sont obligatoires"}), 400

    # 1) Appel au service Catalogue
    try:
        r = requests.get(f"{CATALOG_URL}/products/{product_id}", timeout=5)
    except requests.RequestException:
        return jsonify({"error": "Service Catalogue indisponible"}), 503
    if r.status_code == 404:
        return jsonify({"error": "Produit introuvable"}), 404
    product = r.json()
    total = round(product["price"] * quantity, 2)

    # 2) Enregistrement de la commande (base propre au service)
    with get_db() as c:
        cur = c.execute(
            "INSERT INTO orders (customer, product_id, product_name, quantity, total) "
            "VALUES (?, ?, ?, ?, ?)",
            (customer, product_id, product["name"], quantity, total))
    order_id = cur.lastrowid

    # 3) Appel au service Notifications (sans bloquer la commande en cas d'echec)
    notified = True
    try:
        requests.post(f"{NOTIFICATIONS_URL}/notify", timeout=5, json={
            "recipient": customer,
            "message": f"Commande {order_id} confirmee : {quantity} x {product['name']} = {total} EUR"})
    except requests.RequestException:
        notified = False

    return jsonify({"id": order_id, "customer": customer, "product": product["name"],
                    "quantity": quantity, "total": total, "notified": notified}), 201


@app.get("/orders")
def list_orders():
    with get_db() as c:
        rows = c.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    return jsonify([dict(r) for r in rows])


@app.get("/orders/<int:oid>")
def get_order(oid):
    with get_db() as c:
        row = c.execute("SELECT * FROM orders WHERE id = ?", (oid,)).fetchone()
    if row is None:
        return jsonify({"error": "Commande introuvable"}), 404
    return jsonify(dict(row))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
