from flask import Flask, render_template, request, jsonify
import subprocess, datetime, os, sys, time

# AI Security module
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_security"))
import ai_policy
import notify
import apply_ruleset

app = Flask(__name__)

NODES = {
    "dc":      {"name": "Washington DC", "ns": "ns-dc",      "bat": "bat-dc",      "ip": "10.0.0.1", "ifaces": ["veth-dc-sea", "veth-dc-sf"]},
    "seattle": {"name": "Seattle",       "ns": "ns-seattle", "bat": "bat-seattle", "ip": "10.0.0.2", "ifaces": ["veth-sea-dc", "veth-sea-sf"]},
    "sf":      {"name": "San Francisco", "ns": "ns-sf",      "bat": "bat-sf",      "ip": "10.0.0.3", "ifaces": ["veth-sf-sea", "veth-sf-dc"]},
}

# Service that lives on each node
NODE_SERVICES = {
    "dc":      {"name": "NexusComm",  "script": "messaging.py",  "port": 5006, "mgmt_ip": "10.100.0.2", "url": "http://127.0.0.1:5006"},
    "seattle": {"name": "ClearCast",  "script": "streaming.py",  "port": 5004, "mgmt_ip": "10.100.1.2", "url": "http://127.0.0.1:5004"},
    "sf":      {"name": "EduSphere",  "script": "classroom.py",  "port": 5005, "mgmt_ip": "10.100.2.2", "url": "http://127.0.0.1:5005"},
}

PYTHON  = os.path.expanduser("~/project-env/bin/python")
APP_DIR = os.path.expanduser("~/router-gui")
PID_DIR = "/tmp/meshsvc"
os.makedirs(PID_DIR, exist_ok=True)

GEO_BLOCK_RANGES = ["193.0.0.0/8", "185.0.0.0/8"]

def run(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return r.stdout.strip(), r.returncode
    except Exception as e:
        return str(e), 1

def mesh_exists():
    out, _ = run("ip netns list")
    return "ns-dc" in out

def is_node_online(key):
    n = NODES[key]
    out, _ = run(f"sudo ip netns exec {n['ns']} ip link show {n['bat']} 2>&1")
    return "LOWER_UP" in out

def is_service_running(key):
    """
    Check if a node service is running.
    Primary method: inspect the namespace directly with ss (works without
    management network or NAT). Falls back to socket connections.
    """
    import socket as _sock
    svc  = NODE_SERVICES.get(key, {})
    port = svc.get("port", 0)
    n    = NODES.get(key, {})
    ns   = n.get("ns", "")
    if not port:
        return False

    # Method 1 (most reliable): check if anything listens on that port
    # inside the namespace using ss — no NAT/management network required
    if ns:
        out, code = run(f"sudo ip netns exec {ns} ss -tlnp 2>/dev/null")
        if f":{port}" in out:
            return True

    # Method 2: management IP (only works if setup-mgmt.sh was run)
    for addr in [svc.get("mgmt_ip",""), "127.0.0.1"]:
        if not addr:
            continue
        try:
            s = _sock.socket()
            s.settimeout(0.5)
            s.connect((addr, port))
            s.close()
            return True
        except Exception:
            continue
    return False

def start_node_service(key):
    """Start the service for a node inside its namespace."""
    svc = NODE_SERVICES.get(key)
    n   = NODES.get(key)
    if not svc or not n:
        return False, "Unknown node"
    script = os.path.join(APP_DIR, svc["script"])
    ns     = n["ns"]
    # Kill any existing instance first
    stop_node_service(key)
    time.sleep(0.5)
    # Run inside namespace if it exists, else fall back to main namespace
    ns_list, _ = run("ip netns list")
    if ns in ns_list:
        cmd = ["sudo", "ip", "netns", "exec", ns, PYTHON, script]
    else:
        cmd = ["sudo", PYTHON, script]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        with open(os.path.join(PID_DIR, f"{key}.pid"), "w") as pf:
            pf.write(str(proc.pid))
    except Exception:
        pass
    # Wait up to 5 seconds for the service to come up
    for _ in range(10):
        time.sleep(0.5)
        if is_service_running(key):
            return True, f"{svc['name']} is running on {n['name']} node"
    return False, f"{svc['name']} started but not yet reachable — check logs"

def stop_node_service(key):
    """Stop the service running inside a node namespace."""
    svc = NODE_SERVICES.get(key)
    n   = NODES.get(key)
    if not svc or not n:
        return
    ns   = n["ns"]
    port = svc["port"]
    # Kill by PID file
    pid_file = os.path.join(PID_DIR, f"{key}.pid")
    if os.path.exists(pid_file):
        try:
            with open(pid_file) as f:
                pid = int(f.read().strip())
            run(f"sudo kill -9 {pid} 2>/dev/null")
        except Exception:
            pass
        try:
            os.remove(pid_file)
        except Exception:
            pass
    # Also kill anything using that port inside the namespace
    run(f"sudo ip netns exec {ns} fuser -k {port}/tcp 2>/dev/null")
    # Kill all python processes in that namespace as final fallback
    out, _ = run(f"sudo ip netns pids {ns} 2>/dev/null")
    if out.strip():
        for pid in out.strip().split():
            run(f"sudo kill -9 {pid} 2>/dev/null")

def get_neighbor_count(key):
    n = NODES[key]
    out, _ = run(f"sudo ip netns exec {n['ns']} batctl -m {n['bat']} n 2>&1")
    return len([l for l in out.splitlines() if ":" in l and "IF" not in l])

def firewall_active(ns):
    out, _ = run(f"sudo ip netns exec {ns} nft list ruleset 2>&1")
    return "filter" in out

def geo_block_active(ns):
    out, _ = run(f"sudo ip netns exec {ns} nft list ruleset 2>&1")
    return "193.0.0.0/8" in out

def get_all_status():
    exists = mesh_exists()
    nodes = []
    for key, n in NODES.items():
        if exists:
            online = is_node_online(key)
            neighbors = get_neighbor_count(key) if online else 0
            fw = firewall_active(n["ns"])
            geo = geo_block_active(n["ns"])
        else:
            online = False
            neighbors = 0
            fw = False
            geo = False
        svc = NODE_SERVICES.get(key, {})
        svc_running = is_service_running(key) if exists and online else False
        nodes.append({
            "key": key, "name": n["name"], "ip": n["ip"],
            "online": online, "neighbors": neighbors,
            "firewall": fw, "geo": geo,
            "service_name": svc.get("name", ""),
            "service_port": svc.get("port", 0),
            "service_url":  svc.get("url", ""),
            "service_running": svc_running,
        })
    return {"mesh_running": exists, "nodes": nodes}

# ── MESH START / STOP ──────────────────────────────────────────────

@app.route("/api/mesh/start", methods=["POST"])
def mesh_start():
    if mesh_exists():
        return jsonify({"result": "Mesh already running"})
    cmds = [
        "modprobe batman-adv",
        "ip netns add ns-dc", "ip netns add ns-seattle", "ip netns add ns-sf",
        "ip link add veth-dc-sea type veth peer name veth-sea-dc",
        "ip link add veth-sea-sf type veth peer name veth-sf-sea",
        "ip link add veth-sf-dc type veth peer name veth-dc-sf",
        "ip link set veth-dc-sea netns ns-dc", "ip link set veth-dc-sf netns ns-dc",
        "ip link set veth-sea-dc netns ns-seattle", "ip link set veth-sea-sf netns ns-seattle",
        "ip link set veth-sf-sea netns ns-sf", "ip link set veth-sf-dc netns ns-sf",
        # DC
        "ip netns exec ns-dc modprobe batman-adv",
        "ip netns exec ns-dc ip link set veth-dc-sea up",
        "ip netns exec ns-dc ip link set veth-dc-sf up",
        "ip netns exec ns-dc batctl -m bat-dc if add veth-dc-sea",
        "ip netns exec ns-dc batctl -m bat-dc if add veth-dc-sf",
        "ip netns exec ns-dc ip link set bat-dc up",
        "ip netns exec ns-dc ip addr add 10.0.0.1/24 dev bat-dc",
        # Seattle
        "ip netns exec ns-seattle modprobe batman-adv",
        "ip netns exec ns-seattle ip link set veth-sea-dc up",
        "ip netns exec ns-seattle ip link set veth-sea-sf up",
        "ip netns exec ns-seattle batctl -m bat-seattle if add veth-sea-dc",
        "ip netns exec ns-seattle batctl -m bat-seattle if add veth-sea-sf",
        "ip netns exec ns-seattle ip link set bat-seattle up",
        "ip netns exec ns-seattle ip addr add 10.0.0.2/24 dev bat-seattle",
        # SF
        "ip netns exec ns-sf modprobe batman-adv",
        "ip netns exec ns-sf ip link set veth-sf-sea up",
        "ip netns exec ns-sf ip link set veth-sf-dc up",
        "ip netns exec ns-sf batctl -m bat-sf if add veth-sf-sea",
        "ip netns exec ns-sf batctl -m bat-sf if add veth-sf-dc",
        "ip netns exec ns-sf ip link set bat-sf up",
        "ip netns exec ns-sf ip addr add 10.0.0.3/24 dev bat-sf",
    ]
    errors = []
    for cmd in cmds:
        out, code = run("sudo " + cmd)
        if code != 0 and out:
            errors.append(out)
    if errors:
        return jsonify({"result": "Started with warnings", "warnings": errors})
    return jsonify({"result": "Mesh started successfully"})

@app.route("/api/mesh/stop", methods=["POST"])
def mesh_stop():
    if not mesh_exists():
        return jsonify({"result": "Mesh not running"})
    run("sudo ip netns delete ns-dc")
    run("sudo ip netns delete ns-seattle")
    run("sudo ip netns delete ns-sf")
    return jsonify({"result": "Mesh stopped"})

# ── NODE POWER ─────────────────────────────────────────────────────

@app.route("/api/power/<key>", methods=["POST"])
def power_node(key):
    if key not in NODES:
        return jsonify({"error": "Unknown node"}), 404
    n = NODES[key]
    action = request.json.get("action")
    if action == "off":
        # Stop service first then bring node down
        stop_node_service(key)
        run(f"sudo ip netns exec {n['ns']} ip link set {n['bat']} down")
        for iface in n["ifaces"]:
            run(f"sudo ip netns exec {n['ns']} ip link set {iface} down")
        svc = NODE_SERVICES.get(key, {})
        return jsonify({
            "result": f"{n['name']} powered off — {svc.get('name','')} stopped",
            "online": False, "service_running": False
        })
    elif action == "on":
        run(f"sudo ip netns exec {n['ns']} modprobe batman-adv")
        for iface in n["ifaces"]:
            run(f"sudo ip netns exec {n['ns']} ip link set {iface} up")
            run(f"sudo ip netns exec {n['ns']} batctl -m {n['bat']} if add {iface} 2>/dev/null || true")
        run(f"sudo ip netns exec {n['ns']} ip link set {n['bat']} up")
        run(f"sudo ip netns exec {n['ns']} ip addr replace {n['ip']}/24 dev {n['bat']}")
        # Start service in namespace
        ok, msg = start_node_service(key)
        svc = NODE_SERVICES.get(key, {})
        return jsonify({
            "result": f"{n['name']} powered on — {msg}",
            "online": True, "service_running": ok,
            "service_url": svc.get("url", "")
        })
    return jsonify({"error": "Invalid action"}), 400

@app.route("/api/service/<key>/start", methods=["POST"])
def service_start(key):
    """Start a node service independently of node power toggle."""
    ok, msg = start_node_service(key)
    return jsonify({"result": msg, "running": ok})

@app.route("/api/service/<key>/stop", methods=["POST"])
def service_stop(key):
    """Stop a node service independently."""
    stop_node_service(key)
    svc = NODE_SERVICES.get(key, {})
    return jsonify({"result": f"{svc.get('name','Service')} stopped", "running": False})


# ── FIREWALL ───────────────────────────────────────────────────────

@app.route("/api/firewall/<key>", methods=["POST"])
def toggle_firewall(key):
    if key not in NODES:
        return jsonify({"error": "Unknown node"}), 404
    n = NODES[key]
    action = request.json.get("action")
    if action == "on":
        other_ips = [v["ip"] for k, v in NODES.items() if k != key]
        rules = f"""table inet filter {{
    chain input {{
        type filter hook input priority 0; policy drop;
        iif lo accept
        ct state established,related accept
        ip saddr {other_ips[0]} accept
        ip saddr {other_ips[1]} accept
        log prefix "{key.upper()}-DROP: " drop
    }}
    chain forward {{
        type filter hook forward priority 0; policy drop;
        ct state established,related accept
    }}
    chain output {{
        type filter hook output priority 0; policy accept;
    }}
}}"""
        run(f"sudo ip netns exec {n['ns']} nft flush ruleset")
        out, code = run(f"sudo ip netns exec {n['ns']} nft -f - << 'NFT'\n{rules}\nNFT")
        return jsonify({"result": f"Firewall enabled on {n['name']}", "active": True})
    elif action == "off":
        run(f"sudo ip netns exec {n['ns']} nft flush ruleset")
        return jsonify({"result": f"Firewall disabled on {n['name']}", "active": False})
    return jsonify({"error": "Invalid action"}), 400

# ── GEO-BLOCK ──────────────────────────────────────────────────────

@app.route("/api/geoblock/<key>", methods=["POST"])
def toggle_geoblock(key):
    if key not in NODES:
        return jsonify({"error": "Unknown node"}), 404
    n = NODES[key]
    action = request.json.get("action")
    if action == "on":
        for cidr in GEO_BLOCK_RANGES:
            run(f"sudo ip netns exec {n['ns']} nft add rule inet filter input ip saddr {cidr} drop 2>/dev/null || true")
        return jsonify({"result": f"Geo-blocking enabled on {n['name']}", "active": True})
    elif action == "off":
        # Flush and rebuild without geo rules
        out, _ = run(f"sudo ip netns exec {n['ns']} nft list ruleset 2>&1")
        if "filter" in out:
            for cidr in GEO_BLOCK_RANGES:
                run(f"sudo ip netns exec {n['ns']} nft delete rule inet filter input ip saddr {cidr} drop 2>/dev/null || true")
        return jsonify({"result": f"Geo-blocking disabled on {n['name']}", "active": False})
    return jsonify({"error": "Invalid action"}), 400

# ── OTHER ──────────────────────────────────────────────────────────

@app.route("/api/status")
def api_status():
    return jsonify(get_all_status())

@app.route("/api/rules/<key>")
def api_rules(key):
    if key not in NODES:
        return jsonify({"rules": "Unknown node"}), 404
    out, _ = run(f"sudo ip netns exec {NODES[key]['ns']} nft list ruleset 2>&1")
    return jsonify({"rules": out or "No rules loaded."})

@app.route("/api/block", methods=["POST"])
def block_ip():
    data = request.json
    ip = data.get("ip")
    node = data.get("node", "all")
    targets = [node] if node != "all" else list(NODES.keys())
    results = []
    for k in targets:
        if k in NODES:
            out, _ = run(f"sudo ip netns exec {NODES[k]['ns']} nft add rule inet filter input ip saddr {ip} drop 2>&1")
            results.append(f"{NODES[k]['name']}: {'OK' if out == '' else out}")
    return jsonify({"result": results})

@app.route("/api/ping/<node>/<target>")
def ping_node(node, target):
    if node not in NODES:
        return jsonify({"output": "Unknown node"}), 404
    out, _ = run(f"sudo ip netns exec {NODES[node]['ns']} ping -c 3 {target} 2>&1")
    return jsonify({"output": out})

# ── AI SECURITY (Zero-Trust Policy Engine) ──────────────────────────

@app.route("/api/ai-security/alerts")
def ai_alerts():
    """Return all alerts (pending + resolved), newest first."""
    return jsonify(ai_policy.load_alerts())

@app.route("/api/ai-security/allowlist")
def ai_allowlist():
    """Return the current zero-trust allowlist."""
    return jsonify(ai_policy.load_allowlist())

@app.route("/api/ai-security/log")
def ai_log():
    """Return the full decision log (last 500 requests, allow + block)."""
    log = ai_policy._load_json(ai_policy.LOG_FILE, [])
    return jsonify(log[:100])

@app.route("/api/ai-security/simulate", methods=["POST"])
def ai_simulate():
    """
    Simulate an employee requesting a domain. Triggers the same
    classify -> log -> (notify if blocked) flow as a real DNS monitor.
    """
    data = request.json or {}
    domain   = (data.get("domain") or "").strip()
    node     = data.get("node", "dc")
    employee = (data.get("employee") or "unknown").strip()

    if not domain:
        return jsonify({"error": "domain required"}), 400

    result = ai_policy.classify_domain(domain, node=node, employee=employee)

    notify_result = None
    if result["decision"] == "BLOCK":
        alerts = ai_policy.load_alerts()
        alert = next((a for a in alerts if a["domain"] == result["domain"] and a["status"] == "pending"), None)
        if alert:
            ok, msg = notify.notify_blocked_request(alert)
            notify_result = msg

    return jsonify({"result": result, "notification": notify_result})

@app.route("/api/ai-security/approve", methods=["POST"])
def ai_approve():
    """Admin approves a previously-blocked domain -- adds to allowlist."""
    data = request.json or {}
    domain = (data.get("domain") or "").strip()
    if not domain:
        return jsonify({"error": "domain required"}), 400
    ai_policy.approve_domain(domain)
    return jsonify({"result": f"{domain} approved and added to allowlist"})

@app.route("/api/ai-security/deny", methods=["POST"])
def ai_deny():
    """Admin denies a previously-blocked domain -- stays blocked."""
    data = request.json or {}
    domain = (data.get("domain") or "").strip()
    if not domain:
        return jsonify({"error": "domain required"}), 400
    ai_policy.deny_domain(domain)
    return jsonify({"result": f"{domain} denied -- remains blocked"})

@app.route("/api/ai-security/generate-ruleset/<node_or_all>", methods=["POST"])
def ai_generate_ruleset(node_or_all):
    """
    Generate (and optionally apply) the zero-trust base ruleset.
    node_or_all = 'dc' | 'seattle' | 'sf' | 'all'
    Query param ?preview=1 returns the ruleset text without applying it.
    """
    preview = request.args.get("preview") == "1"

    if preview:
        if node_or_all == "all":
            text = "\n".join(ai_policy.generate_base_ruleset(k) for k in apply_ruleset.NS_MAP)
        else:
            if node_or_all not in apply_ruleset.NS_MAP:
                return jsonify({"error": "Unknown node"}), 404
            text = ai_policy.generate_base_ruleset(node_or_all)
        return jsonify({"ruleset": text})

    targets = list(apply_ruleset.NS_MAP.keys()) if node_or_all == "all" else [node_or_all]
    if any(t not in apply_ruleset.NS_MAP for t in targets):
        return jsonify({"error": "Unknown node"}), 404

    results = []
    for node_key in targets:
        ok, msg = apply_ruleset.apply_to_node(node_key)
        results.append({"node": node_key, "ok": ok, "message": msg})
    return jsonify({"results": results})

@app.route("/")
def index():
    data = get_all_status()
    return render_template("admin.html",
                           nodes=data["nodes"],
                           mesh_running=data["mesh_running"],
                           now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
