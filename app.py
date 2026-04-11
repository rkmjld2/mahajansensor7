from flask import Flask, request, jsonify, render_template, send_file
import csv, os, time

app = Flask(__name__)

# -------- CONFIG --------
DATA_FILE = "sensor_data.csv"
API_KEY = "12b5112c62284ea0b3da0039f298ec7a85ac9a1791044052b6df970640afb1c5"

last_seen = 0
collect_data = True
latest_cmd = ""
view_mode = "live"   # live / full

# -------- INIT FILE --------
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id","sensor1","sensor2","sensor3","time"])

# -------- RECEIVE DATA --------
@app.route("/api/data")
def receive():
    global last_seen

    key = request.args.get("key")
    if key != API_KEY:
        return "Invalid Key", 403

    last_seen = time.time()

    try:
        id_val = request.args.get("id")
        s1 = request.args.get("s1")
        s2 = request.args.get("s2")
        s3 = request.args.get("s3")
        now = request.args.get("time")

        # ✅ Allow all data (NO rejection)
        if not (id_val and s1 and s2 and s3 and now):
            return "OK"

        # -------- READ EXISTING --------
        with open(DATA_FILE, "r") as f:
            rows = list(csv.DictReader(f))

        # -------- SKIP DUPLICATE --------
        for r in rows:
            if r["time"] == now:
                return "OK"   # ⭐ DO NOT RETURN 400

        # -------- SAVE SAME ID --------
        with open(DATA_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([id_val, s1, s2, s3, now])

        print("Saved:", id_val)

        return "OK"

    except Exception as e:
        print("Error:", e)
        return "OK"   # ⭐ NEVER RETURN 400
# -------- VIEW MODES --------
@app.route("/api/reset")
def reset_view():
    global view_mode
    view_mode = "live"
    return "OK"

@app.route("/api/fullview")
def full_view():
    global view_mode
    view_mode = "full"
    return "OK"


# -------- GET DATA --------
@app.route("/api/all")
def all_data():
    global view_mode

    try:
        with open(DATA_FILE, "r") as f:
            rows = list(csv.DictReader(f))

        rows.reverse()   # latest first

        if view_mode == "live":
            return jsonify(rows[:50])   # latest 50
        else:
            return jsonify(rows)       # full

    except:
        return jsonify([])


# -------- DOWNLOAD --------
@app.route("/download")
def download():
    return send_file(DATA_FILE, as_attachment=True)


# -------- STATUS --------
@app.route("/status")
def status():
    global last_seen

    try:
        if time.time() - last_seen < 15:
            return jsonify({"status": "Connected"})
        else:
            return jsonify({"status": "Disconnected"})
    except:
        return jsonify({"status": "Checking"})

# -------- CONTROL --------
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


# -------- COMMAND SYSTEM --------
# -------- COMMAND SYSTEM --------
last_command = ""

@app.route("/sendcmd")
def sendcmd():
    global last_command

    cmd = request.args.get("cmd")

    if not cmd:
        return "No command"

    last_command = cmd.strip()
    print("Command received from web:", last_command)

    return "Command Sent: " + last_command


@app.route("/api/cmd")
def get_cmd():
    global last_command

    cmd = last_command
    last_command = ""   # clear after sending

    return cmd


# -------- QUERY --------
@app.route("/query")
def query():
    global latest_cmd

    cmd = request.args.get("cmd")

    try:
        if not cmd:
            return "No command"

        parts = cmd.strip().split()

        # DELETE SERVER DATA
        if parts[0].lower() == "delete" and len(parts) == 3:
            start = int(parts[1])
            end = int(parts[2])

            with open(DATA_FILE, "r") as f:
                rows = list(csv.DictReader(f))

            rows = [r for r in rows if not (start <= int(r["id"]) <= end)]

            with open(DATA_FILE, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["id","sensor1","sensor2","sensor3","time"])
                writer.writeheader()
                writer.writerows(rows)

            return "Deleted (Server)"

        # CLEAR SD
        elif parts[0].lower() == "clear_sd":
            latest_cmd = "CLEAR_SD"
            return "SD Clear Command Sent"

        # SYNC SD
        elif parts[0].lower() == "sync_sd":
            latest_cmd = "SYNC"
            return "Sync started"

        else:
            return "Unknown Command"

    except Exception as e:
        return "Error: " + str(e)


# -------- HOME --------
@app.route("/")
def home():
    return render_template("index.html")


# -------- RUN --------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
