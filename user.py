from flask import Flask, render_template, jsonify
import subprocess
import datetime

app = Flask(__name__)

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        return str(e)

def get_mesh_status():
    nodes = [
        {"name": "Washington DC", "ip": "10.0.0.1", "ns": "ns-dc", "bat": "bat-dc"},
        {"name": "Seattle",       "ip": "10.0.0.2", "ns": "ns-seattle", "bat": "bat-seattle"},
        {"name": "San Francisco", "ip": "10.0.0.3", "ns": "ns-sf", "bat": "bat-sf"},
    ]
    result = []
    for n in nodes:
        ping = run_cmd(f"sudo ip netns exec {n['ns']} ping -c 1 -W 1 {n['ip']} 2>&1")
        alive = "1 received" in ping or "0% packet loss" in ping
        result.append({"name": n["name"], "ip": n["ip"], "online": alive})
    return result

@app.route("/")
def index():
    nodes = get_mesh_status()
    online = sum(1 for n in nodes if n["online"])
    return render_template("user.html", nodes=nodes, online=online, total=len(nodes),
                           now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

@app.route("/api/status")
def api_status():
    return jsonify(get_mesh_status())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
