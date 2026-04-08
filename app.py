from flask import Flask, request, jsonify, render_template
import mysql.connector
import time
import os

app = Flask(__name__)

# -------- CONFIG --------
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "gateway01.ap-southeast-1.prod.aws.tidbcloud.com"),
    "port": int(os.getenv("DB_PORT", 4000)),
    "user": os.getenv("DB_USER", "ax6KHc1BNkyuaor.root"),
    "password": os.getenv("DB_PASSWORD", "EP8isIWoEOQk7DSr"),
    "database": os.getenv("DB_NAME", "sensor"),
    "connection_timeout": 5
}

API_KEY = os.getenv("API_KEY", "12b5112c62284ea0b3da0039f298ec7a85ac9a1791044052b6df970640afb1c5")

esp_connected = False
collect_data = True
last_seen = 0


# -------- DB CONNECTION --------
def get_db():
    return mysql.connector.connect(**DB_CONFIG)


# -------- HOME --------
@app.route("/")
def home():
    return render_template("index.html")


# -------- RECEIVE DATA --------
@app.route("/api/data")
def receive_data():
    global esp_connected, last_seen, collect_data

    key = request.args.get("key")
    if key != API_KEY:
        return "Invalid API Key", 403

    esp_connected = True
    last_seen = time.time()

    if not collect_data:
        return "Stopped"

    try:
        s1 = float(request.args.get("s1", 0))
        s2 = float(request.args.get("s2", 0))
        s3 = float(request.args.get("s3", 0))
    except:
        return "Invalid sensor values", 400

    try:
        db = get_db()
        cursor = db.cursor()

        cursor.execute(
            "INSERT INTO sensor_db (sensor1, sensor2, sensor3) VALUES (%s,%s,%s)",
            (s1, s2, s3)
        )

        db.commit()
        cursor.close()
        db.close()

        return "Saved"

    except Exception as e:
        return str(e), 500


# -------- START / STOP --------
@app.route("/start")
def start():
    global collect_data
    collect_data = True
    return "Started"


@app.route("/stop")
def stop():
    global collect_data
    collect_data = False
    return "Stopped"


# -------- STATUS --------
@app.route("/status")
def status():
    global esp_connected

    if time.time() - last_seen > 10:
        esp_connected = False

    return jsonify({"status": "Connected" if esp_connected else "Disconnected"})


# -------- GET DATA --------
@app.route("/data")
def get_data():
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT id, sensor1, sensor2, sensor3, timestamp
            FROM sensor_db
            ORDER BY id DESC
            LIMIT 100
        """)

        data = cursor.fetchall()

        # 🔥 FORMAT DATE
        for row in data:
            if row["timestamp"]:
                row["timestamp"] = row["timestamp"].strftime("%d/%m/%Y %H:%M:%S")

        cursor.close()
        db.close()

        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)})


# -------- SEARCH --------
@app.route("/search", methods=["POST"])
def search():
    start = request.form.get("start")
    end = request.form.get("end")

    if start:
        start = start.replace("T", " ")
    if end:
        end = end.replace("T", " ")

    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT id, sensor1, sensor2, sensor3, timestamp
            FROM sensor_db
            WHERE timestamp BETWEEN %s AND %s
            ORDER BY id DESC
        """, (start, end))

        data = cursor.fetchall()

        # 🔥 FORMAT DATE
        for row in data:
            if row["timestamp"]:
                row["timestamp"] = row["timestamp"].strftime("%d/%m/%Y %H:%M:%S")

        cursor.close()
        db.close()

        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)})


# -------- CUSTOM QUERY --------
@app.route("/query", methods=["POST"])
def run_query():
    sql = request.form.get("query")

    if not sql:
        return "No query"

    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        if sql.lower().startswith("select"):
            cursor.execute(sql)
            result = cursor.fetchall()
            return jsonify(result)

        elif sql.lower().startswith(("delete", "update")):
            cursor.execute(sql)
            db.commit()

            return jsonify({
                "message": "Query OK",
                "rows_affected": cursor.rowcount
            })

        else:
            return "Only SELECT/DELETE/UPDATE allowed"

    except Exception as e:
        return jsonify({"error": str(e)})

    finally:
        cursor.close()
        db.close()


if __name__ == "__main__":
    app.run(debug=True)