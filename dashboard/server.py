import os
import json
import sqlite3
import hmac as _hmac
import hashlib
from datetime import datetime, date
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="gevent", manage_session=False)

_DATA_DIR = os.getenv("DATA_DIR", os.path.dirname(__file__))
DB_PATH = os.path.join(_DATA_DIR, "orders.db")
DASHBOARD_PIN = os.getenv("DASHBOARD_PIN", "password")
_TOKEN_SECRET = os.getenv("SECRET_KEY", "gsm-tok-secret").encode()


def _make_token():
    return _hmac.new(_TOKEN_SECRET, DASHBOARD_PIN.encode(), hashlib.sha256).hexdigest()


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not DASHBOARD_PIN:
            return f(*args, **kwargs)
        token = request.headers.get("X-Auth-Token", "")
        if not _hmac.compare_digest(token, _make_token()):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


def categorize_service(svc):
    name = svc.get("name", "").lower()
    if any(k in name for k in ["resoftare", "update", "salvare date", "verificare", "diagnoz"]):
        return "Software & Diagnostic"
    if any(k in name for k in ["display", "sticla lcd"]):
        return "Reparatii"
    if any(k in name for k in ["acumulator", "sticla spate", "sticla", "capac", "carcasa", "reconditionare", "curatare", "oxid"]):
        return "Inlocuiri & Daune"
    if any(k in name for k in ["difuzor", "buzzer", "modul", "mufa", "microfon", "jack", "casca", "sita", "camera", "geam", "buton", "flex", "montaj", "folii"]):
        return "Reparatii"
    return "Altele"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id              TEXT PRIMARY KEY,
            services        TEXT NOT NULL,
            date            TEXT NOT NULL,
            time_slot       TEXT NOT NULL,
            amount          REAL NOT NULL,
            status          TEXT NOT NULL DEFAULT 'in_lucru',
            notes           TEXT DEFAULT '',
            customer_phone  TEXT DEFAULT '',
            customer_name   TEXT DEFAULT '',
            model           TEXT DEFAULT '',
            brand           TEXT DEFAULT '',
            description     TEXT DEFAULT '',
            created_at      TEXT NOT NULL,
            completed_at    TEXT
        )
    """)
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(orders)").fetchall()]
    for col, typedef in [
        ("notes",          "TEXT DEFAULT ''"),
        ("completed_at",   "TEXT"),
        ("customer_phone", "TEXT DEFAULT ''"),
        ("customer_name",  "TEXT DEFAULT ''"),
        ("model",          "TEXT DEFAULT ''"),
        ("brand",          "TEXT DEFAULT ''"),
        ("description",    "TEXT DEFAULT ''"),
    ]:
        if col not in cols:
            conn.execute(f"ALTER TABLE orders ADD COLUMN {col} {typedef}")
    conn.execute("UPDATE orders SET status = 'in_lucru' WHERE status IN ('pending', 'confirmed')")
    conn.execute("UPDATE orders SET status = 'completed' WHERE status = 'rejected'")
    conn.commit()
    conn.close()


init_db()


def row_to_dict(row):
    d = dict(row)
    d["services"] = json.loads(d["services"])
    d.pop("confirmed_at", None)
    return d


def get_stats():
    today = date.today().isoformat()
    conn = get_db()
    today_count = conn.execute("SELECT COUNT(*) FROM orders WHERE date(created_at) = ?", (today,)).fetchone()[0]
    in_lucru_count = conn.execute("SELECT COUNT(*) FROM orders WHERE status = 'in_lucru'").fetchone()[0]
    completed_today = conn.execute(
        "SELECT COUNT(*) FROM orders WHERE status = 'completed' AND date(completed_at) = ?", (today,)
    ).fetchone()[0]
    revenue_today = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM orders WHERE status = 'completed' AND date(completed_at) = ?", (today,)
    ).fetchone()[0]
    avg_order = conn.execute(
        "SELECT COALESCE(AVG(amount), 0) FROM orders WHERE date(created_at) = ?", (today,)
    ).fetchone()[0]
    busiest_slot = conn.execute(
        "SELECT time_slot, COUNT(*) as cnt FROM orders WHERE date(created_at) = ? GROUP BY time_slot ORDER BY cnt DESC LIMIT 1", (today,)
    ).fetchone()
    conn.close()
    return {
        "today_count": today_count,
        "in_lucru_count": in_lucru_count,
        "completed_today": completed_today,
        "revenue_today": round(revenue_today, 2),
        "avg_order_today": round(avg_order, 2),
        "busiest_slot": busiest_slot["time_slot"] if busiest_slot else "-",
    }


def get_all_orders():
    conn = get_db()
    rows = conn.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    conn.close()
    return [row_to_dict(r) for r in rows]


SLOTS = ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00"]


def get_analytics():
    conn = get_db()
    rows = conn.execute("SELECT services, amount, status, created_at, completed_at, time_slot FROM orders").fetchall()
    conn.close()

    cat_revenue = {"Reparatii": 0, "Inlocuiri & Daune": 0, "Software & Diagnostic": 0}
    cat_count = {"Reparatii": 0, "Inlocuiri & Daune": 0, "Software & Diagnostic": 0}
    cat_completed = {"Reparatii": 0, "Inlocuiri & Daune": 0, "Software & Diagnostic": 0}
    weekday_revenue = [0.0] * 7
    monthly_revenue = {}
    slot_count = {s: 0 for s in SLOTS}

    for row in rows:
        services = json.loads(row["services"])
        created = row["created_at"] or ""
        month_key = created[:7] if created else "unknown"

        ts = row["time_slot"] or ""
        if ts in slot_count:
            slot_count[ts] += 1

        for svc in services:
            cat = categorize_service(svc)
            price = svc.get("price", 0) or 0
            if cat in cat_count:
                cat_count[cat] += 1
            if row["status"] == "completed" and cat in cat_revenue:
                cat_revenue[cat] += price
                cat_completed[cat] += 1

        if row["status"] == "completed":
            monthly_revenue[month_key] = monthly_revenue.get(month_key, 0) + row["amount"]
            if created:
                try:
                    wd = datetime.fromisoformat(created).weekday()
                    weekday_revenue[wd] += row["amount"]
                except Exception:
                    pass

    return {
        "category_revenue": {k: round(v, 2) for k, v in cat_revenue.items()},
        "category_count": cat_count,
        "category_completed": cat_completed,
        "weekday_revenue": [round(v, 2) for v in weekday_revenue],
        "monthly_revenue": {k: round(v, 2) for k, v in sorted(monthly_revenue.items())},
        "slot_count": slot_count,
    }


def broadcast():
    socketio.emit("refresh", {
        "orders": get_all_orders(),
        "stats": get_stats(),
        "analytics": get_analytics(),
    })


@app.route("/api/auth", methods=["POST"])
def auth():
    pin = (request.json or {}).get("pin", "")
    if not DASHBOARD_PIN:
        return jsonify({"ok": True, "token": ""})
    if pin == DASHBOARD_PIN:
        return jsonify({"ok": True, "token": _make_token()})
    return jsonify({"error": "PIN incorect"}), 401


@app.route("/api/me")
def me():
    if not DASHBOARD_PIN:
        return jsonify({"authenticated": True, "token": ""})
    token = request.headers.get("X-Auth-Token", "")
    ok = _hmac.compare_digest(token, _make_token())
    return jsonify({"authenticated": ok})


@app.route("/api/logout", methods=["POST"])
def logout():
    return jsonify({"ok": True})


@app.route("/api/orders", methods=["POST"])
@require_auth
def create_order():
    data = request.json
    order_id = data.get("order_id")
    if not order_id:
        return jsonify({"error": "order_id is required"}), 400

    services       = data.get("services", [])
    order_date     = data.get("date", "")
    time_slot      = data.get("timeSlot", "")
    amount         = data.get("amount", 0)
    customer_phone = data.get("customer_phone", "")
    customer_name  = data.get("customer_name", "")
    model          = data.get("model", "")
    brand          = data.get("brand", "")
    description    = data.get("description", "")

    conn = get_db()
    conn.execute(
        """INSERT OR IGNORE INTO orders
           (id, services, date, time_slot, amount, status, notes,
            customer_phone, customer_name, model, brand, description, created_at)
           VALUES (?, ?, ?, ?, ?, 'in_lucru', '', ?, ?, ?, ?, ?, ?)""",
        (order_id, json.dumps(services), order_date, time_slot, amount,
         customer_phone, customer_name, model, brand, description,
         datetime.utcnow().isoformat()),
    )
    conn.commit()
    print(f"[Dashboard] Order {order_id} — {model} — RON {amount}")
    conn.close()

    broadcast()
    return jsonify({"success": True, "order_id": order_id}), 201


@app.route("/api/orders", methods=["GET"])
@require_auth
def list_orders():
    status = request.args.get("status")
    conn = get_db()
    if status:
        rows = conn.execute("SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC", (status,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([row_to_dict(r) for r in rows])


@app.route("/api/orders/stats", methods=["GET"])
@require_auth
def order_stats():
    return jsonify(get_stats())


@app.route("/api/analytics", methods=["GET"])
@require_auth
def analytics():
    return jsonify(get_analytics())


@app.route("/api/orders/<order_id>", methods=["DELETE"])
@require_auth
def delete_order(order_id):
    conn = get_db()
    conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()
    print(f"[Dashboard] Order {order_id} deleted")
    broadcast()
    return jsonify({"ok": True})


@app.route("/api/orders/<order_id>", methods=["PATCH"])
@require_auth
def update_order(order_id):
    data = request.json
    new_status = data.get("status")
    if new_status not in ("completed", "in_lucru"):
        return jsonify({"error": "status must be 'completed' or 'in_lucru'"}), 400

    conn = get_db()
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "order not found"}), 404

    if new_status == "completed":
        conn.execute(
            "UPDATE orders SET status = 'completed', completed_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), order_id),
        )
    else:
        conn.execute(
            "UPDATE orders SET status = 'in_lucru', completed_at = NULL WHERE id = ?",
            (order_id,),
        )
    conn.commit()
    updated = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()
    print(f"[Dashboard] Order {order_id} -> {new_status}")
    broadcast()
    return jsonify(row_to_dict(updated))


@app.route("/api/orders/<order_id>/notes", methods=["PATCH"])
@require_auth
def update_notes(order_id):
    data = request.json
    notes = data.get("notes", "")

    conn = get_db()
    row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "order not found"}), 404

    conn.execute("UPDATE orders SET notes = ? WHERE id = ?", (notes, order_id))
    conn.commit()
    updated = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()
    print(f"[Dashboard] Order {order_id} notes updated")
    broadcast()
    return jsonify(row_to_dict(updated))


@socketio.on("connect")
def on_connect():
    print("[WS] Client connected")
    socketio.emit("refresh", {
        "orders": get_all_orders(),
        "stats": get_stats(),
        "analytics": get_analytics(),
    })


@app.route("/")
def dashboard():
    return send_from_directory(".", "dashboard.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    print("\n  Mobile Concept GSM — Dashboard")
    print(f"  Database: {DB_PATH}")
    print(f"\n  Open http://localhost:{port}\n")
    socketio.run(app, debug=False, host="0.0.0.0", port=port)
