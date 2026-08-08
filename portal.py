from flask import Flask
import socket, datetime

app = Flask(__name__)

SERVICES = [
    {
        'id':'admin', 'name':'NodeNet NOC',
        'desc':'ISP Network Operations Center — mesh routing, firewall rules, AI security, node management.',
        'port':5000, 'icon':'⬡', 'color':'#38bdf8', 'path':'/', 'tag':'INTERNAL'
    },
    {
        'id':'vault', 'name':'VaultNet',
        'desc':'Secure cloud file storage. Upload, share, and manage files across all three data centers.',
        'port':5002, 'icon':'◈', 'color':'#22d3ee', 'path':'/', 'tag':'STORAGE'
    },
    {
        'id':'bank', 'name':'SecureMesh National Bank',
        'desc':'Private mesh banking portal. DC, Seattle, and SF branch operations with inter-node wire transfers.',
        'port':5003, 'icon':'🏦', 'color':'#c9a227', 'path':'/', 'tag':'FINANCE'
    },
    {
        'id':'nexus', 'name':'NexusComm',
        'desc':'Enterprise business messaging platform. Secure channels, real-time alerts, and team collaboration.',
        'port':5006, 'icon':'✦', 'color':'#7c3aed', 'path':'/', 'tag':'MESSAGING · DC'
    },
    {
        'id':'cast', 'name':'ClearCast',
        'desc':'Professional video streaming platform. Upload, host, and stream MP4 content across the mesh.',
        'port':5004, 'icon':'▶', 'color':'#059669', 'path':'/', 'tag':'VIDEO · SEATTLE'
    },
    {
        'id':'edu', 'name':'EduSphere',
        'desc':'Learning management system. Courses, assignments, grading, and materials for teams.',
        'port':5005, 'icon':'◈', 'color':'#d97706', 'path':'/', 'tag':'EDTECH · SF'
    },
]

MGMT_IPS = {5006: "10.100.0.2", 5004: "10.100.1.2", 5005: "10.100.2.2"}
NS_MAP   = {5006: "ns-dc",      5004: "ns-seattle",  5005: "ns-sf"}

def check_port(port):
    import socket, subprocess
    # Method 1: check inside namespace with ss (works without management network)
    ns = NS_MAP.get(port)
    if ns:
        try:
            r = subprocess.run(
                ["sudo", "ip", "netns", "exec", ns, "ss", "-tlnp"],
                capture_output=True, text=True, timeout=2
            )
            if f":{port}" in r.stdout:
                return True
        except Exception:
            pass
    # Method 2: try management IP and localhost
    for addr in [MGMT_IPS.get(port, ""), "127.0.0.1"]:
        if not addr:
            continue
        try:
            s = socket.socket(); s.settimeout(0.5)
            s.connect((addr, port)); s.close(); return True
        except: continue
    return False


HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NodeNet ISP — Customer Portal</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:"Segoe UI",Arial,sans-serif;background:#050a14;color:#e2e8f0;min-height:100vh;}}
/* ISP HEADER */
.isp-header{{
  background:linear-gradient(135deg,#071428 0%,#0a1e3a 100%);
  border-bottom:2px solid #0ea5e9;
  padding:0 36px;
  height:64px;
  display:flex;
  align-items:center;
  justify-content:space-between;
}}
.isp-brand{{display:flex;align-items:center;gap:14px;}}
.isp-logo{{
  width:38px;height:38px;border-radius:8px;
  background:linear-gradient(135deg,#0ea5e9,#6366f1);
  display:flex;align-items:center;justify-content:center;
  font-size:18px;font-weight:900;color:#fff;
}}
.isp-name{{font-size:18px;font-weight:800;color:#fff;letter-spacing:.3px;}}
.isp-tagline{{font-size:11px;color:#0ea5e9;letter-spacing:2px;text-transform:uppercase;margin-top:2px;}}
.isp-right{{font-family:monospace;font-size:12px;color:#1e4a7a;display:flex;flex-direction:column;align-items:flex-end;gap:3px;}}
.isp-status{{display:flex;align-items:center;gap:6px;font-size:11px;color:#4ade80;}}
.isp-dot{{width:6px;height:6px;border-radius:50%;background:#4ade80;box-shadow:0 0 6px #4ade80;}}
/* HERO */
.hero{{
  background:linear-gradient(180deg,#071428 0%,#050a14 100%);
  padding:52px 36px 40px;
  text-align:center;
  border-bottom:1px solid #0a1e3a;
}}
.hero-eyebrow{{font-size:11px;letter-spacing:3px;text-transform:uppercase;color:#0ea5e9;margin-bottom:14px;}}
.hero h1{{font-size:34px;font-weight:800;color:#fff;line-height:1.2;margin-bottom:12px;}}
.hero p{{font-size:14px;color:#475569;max-width:560px;margin:0 auto 28px;line-height:1.7;}}
/* NODE STATUS BAR */
.node-bar{{display:flex;justify-content:center;gap:10px;flex-wrap:wrap;}}
.node-pill{{
  display:flex;align-items:center;gap:8px;padding:7px 16px;border-radius:6px;
  background:#0a1e3a;border:1px solid #1e3a5c;font-size:11px;font-family:monospace;
}}
.nd-on{{width:7px;height:7px;border-radius:50%;background:#4ade80;box-shadow:0 0 6px #4ade80;}}
.nd-off{{width:7px;height:7px;border-radius:50%;background:#f87171;}}
/* GRID */
.section{{max-width:1080px;margin:0 auto;padding:40px 24px 60px;}}
.section-label{{
  font-size:10px;letter-spacing:3px;text-transform:uppercase;color:#1e4a7a;
  margin-bottom:20px;display:flex;align-items:center;gap:12px;
}}
.section-label::after{{content:"";flex:1;height:1px;background:#0a1e3a;}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:16px;}}
.card{{
  background:#071428;border:1px solid #0a1e3a;border-radius:12px;
  overflow:hidden;transition:transform .2s,border-color .2s,box-shadow .2s;
}}
.card:hover{{transform:translateY(-3px);box-shadow:0 14px 36px rgba(0,0,0,.6);}}
.card-top{{padding:22px 22px 16px;display:flex;align-items:flex-start;gap:14px;}}
.c-icon{{
  width:46px;height:46px;border-radius:10px;display:flex;align-items:center;
  justify-content:center;font-size:20px;font-weight:800;flex-shrink:0;
}}
.c-name{{font-size:15px;font-weight:700;color:#fff;margin-bottom:4px;}}
.c-tag{{font-size:9px;letter-spacing:2px;text-transform:uppercase;font-family:monospace;margin-bottom:6px;}}
.c-desc{{font-size:12px;color:#475569;line-height:1.6;}}
.card-footer{{
  padding:12px 22px;border-top:1px solid #0a1e3a;
  display:flex;align-items:center;justify-content:space-between;
}}
.port-tag{{font-size:10px;font-family:monospace;color:#1e3a5c;}}
.status-on{{font-size:10px;padding:2px 9px;border-radius:10px;letter-spacing:1px;
            background:rgba(74,222,128,.08);color:#4ade80;border:1px solid rgba(74,222,128,.2);}}
.status-off{{font-size:10px;padding:2px 9px;border-radius:10px;letter-spacing:1px;
             background:rgba(248,113,113,.08);color:#f87171;border:1px solid rgba(248,113,113,.2);}}
.launch-btn{{
  padding:7px 18px;border-radius:7px;font-size:12px;font-weight:700;
  cursor:pointer;text-decoration:none;border:none;transition:all .2s;
}}
.launch-off{{background:#0a1e3a;color:#334155;cursor:not-allowed;}}
/* ISP FOOTER */
.isp-footer{{
  border-top:1px solid #0a1e3a;padding:24px 36px;
  display:flex;align-items:center;justify-content:space-between;
  font-size:11px;color:#1e3a5c;font-family:monospace;
}}
</style></head><body>

<header class="isp-header">
  <div class="isp-brand">
    <div class="isp-logo">N</div>
    <div>
      <div class="isp-name">NodeNet ISP</div>
      <div class="isp-tagline">Enterprise Mesh Connectivity</div>
    </div>
  </div>
  <div class="isp-right">
    <div class="isp-status"><span class="isp-dot"></span>All Systems Operational</div>
    <span id="clock">{now}</span>
  </div>
</header>

<div class="hero">
  <div class="hero-eyebrow">Customer Portal · Service Directory</div>
  <h1>Your NodeNet Services</h1>
  <p>Secure, mesh-routed applications hosted across our Washington DC, Seattle, and San Francisco data centers — all protected by AI-powered zero-trust security.</p>
  <div class="node-bar">
    {node_pills}
  </div>
</div>

<div class="section">
  <div class="section-label">Active Services</div>
  <div class="grid">
    {service_cards}
  </div>
</div>

<footer class="isp-footer">
  <span>NodeNet ISP · B.A.T.M.A.N.-adv Mesh Network · nftables Zero-Trust Firewall</span>
  <span>3 nodes · 6 services · AES-256 encrypted</span>
</footer>

<script>
setInterval(() => {{
  document.getElementById("clock").textContent = new Date().toLocaleString();
}}, 1000);
</script>
</body></html>"""

@app.route("/")
def index():
    node_pills = "".join(f"""
<div class="node-pill">
  <span class="nd-on"></span> {name} &nbsp;·&nbsp; {ip}
</div>""" for name, ip in [("Washington DC","10.0.0.1"),("Seattle","10.0.0.2"),("San Francisco","10.0.0.3")])

    cards = ""
    for svc in SERVICES:
        online = check_port(svc["port"])
        if online:
            launch = f'''<a href="http://127.0.0.1:{svc["port"]}{svc["path"]}" target="_blank" class="launch-btn" style="background:{svc["color"]};color:#050a14;">Launch</a>'''
        else:
            launch = '<span class="launch-btn launch-off">Offline</span>'
        border = f'border-color:{svc["color"]}33;' if online else ""
        cards += f"""
<div class="card" style="{border}">
  <div class="card-top">
    <div class="c-icon" style="background:{svc["color"]}18;color:{svc["color"]};">{svc["icon"]}</div>
    <div>
      <div class="c-name">{svc["name"]}</div>
      <div class="c-tag" style="color:{svc["color"]};">{svc["tag"]}</div>
      <div class="c-desc">{svc["desc"]}</div>
    </div>
  </div>
  <div class="card-footer">
    <span class="port-tag">:{svc["port"]}</span>
    <span class="{"status-on" if online else "status-off"}">{"Online" if online else "Offline"}</span>
    {launch}
  </div>
</div>"""

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return HTML.format(now=now, node_pills=node_pills, service_cards=cards)

if __name__ == "__main__":
    print("NodeNet ISP Customer Portal — starting on http://127.0.0.1:5001")
    app.run(host="0.0.0.0", port=5001, debug=True)
