from flask import Flask, request, redirect, session, jsonify
import json, datetime, os, time

app = Flask(__name__)
app.secret_key = 'nexuscomm_dc_2025'

DATA_DIR = os.path.expanduser('~/nexuscomm')
os.makedirs(DATA_DIR, exist_ok=True)
MSGS_FILE = os.path.join(DATA_DIR, 'messages.json')
SEEN_FILE = os.path.join(DATA_DIR, 'seen.json')

NODE = {'name': 'Washington DC', 'ip': '10.0.0.1', 'color': '#38bdf8'}

USERS = {
    'admin': {'name': 'Network Admin', 'avatar': '🛡️', 'role': 'admin'},
    'jdoe':  {'name': 'Jane Doe',      'avatar': '👩‍💻', 'role': 'staff'},
    'mlee':  {'name': 'Michael Lee',   'avatar': '👨‍💻', 'role': 'staff'},
    'achan': {'name': 'Alice Chan',    'avatar': '👩‍🔬', 'role': 'staff'},
}
PASSWORDS = {'admin':'admin','jdoe':'pass','mlee':'pass','achan':'pass'}

CHANNELS = {
    'general':     {'desc': 'Network-wide announcements',        'icon': '#️⃣'},
    'mesh-alerts': {'desc': 'AI firewall and security alerts',   'icon': '🚨'},
    'dc-ops':      {'desc': 'Washington DC node operations',     'icon': '🏛️'},
    'seattle-ops': {'desc': 'Seattle node operations',           'icon': '🌧️'},
    'sf-ops':      {'desc': 'San Francisco node operations',     'icon': '🌉'},
    'random':      {'desc': 'Off-topic chat',                    'icon': '💬'},
}

SEED = {
    'general': [
        ('admin','SecureMesh network is live. All 3 nodes online and batman-adv routing active.','2025-06-15 08:00:00'),
        ('jdoe', 'Good morning. DC node zero-trust ruleset applied — 4 categories pre-approved.','2025-06-15 08:05:00'),
        ('mlee', 'Seattle node up. MeshStream running on 10.0.0.2:5004.','2025-06-15 08:07:00'),
        ('achan','SF node online. MeshLearn active on 10.0.0.3:5005.','2025-06-15 08:09:00'),
    ],
    'mesh-alerts': [
        ('admin','🚨 BLOCK: instagram.com requested by mlee@seattle. Risk: social_media. ML score: 3%. Pending admin review.','2025-06-15 09:10:00'),
        ('admin','🔒 GEO-BLOCK: Inbound connection from 193.42.x.x dropped at DC node (high-risk range).','2025-06-15 09:30:00'),
        ('admin','⚠️ AI Engine: Anomalous traffic pattern detected. Domain xk29fj.tk scored 87% suspicious (DGA pattern).','2025-06-15 10:15:00'),
    ],
    'dc-ops': [
        ('jdoe', 'DC nftables base ruleset applied. Default-deny on all chains.','2025-06-15 10:00:00'),
        ('admin','NexusComm service started on DC node (port 5006).','2025-06-15 10:01:00'),
    ],
    'seattle-ops': [
        ('mlee', 'MeshStream video service running. Upload an MP4 to test streaming.','2025-06-15 10:05:00'),
        ('mlee', 'Seattle node firewall active. Geo-blocking enabled.','2025-06-15 10:06:00'),
    ],
    'sf-ops': [
        ('achan','MeshLearn online. 3 courses loaded. Teachers: jdoe/admin. Students: mlee/achan.','2025-06-15 10:10:00'),
    ],
    'random': [
        ('mlee', 'Batman-adv mesh routing is genuinely impressive. Zero packet loss on all 3 nodes.','2025-06-15 12:00:00'),
        ('achan','The ML domain risk model hit 94% test accuracy. Not bad for a char n-gram Random Forest.','2025-06-15 12:03:00'),
        ('jdoe', 'Reminder: all traffic goes through zero-trust policy engine. No exceptions.','2025-06-15 12:30:00'),
    ],
}

# ── data helpers ──────────────────────────────────────────────────────────────

def load_msgs():
    if os.path.exists(MSGS_FILE):
        try:
            with open(MSGS_FILE) as f: return json.load(f)
        except: pass
    # seed on first run
    seed = {ch: [{'id':i+1,'user':u,'text':t,'ts':ts} for i,(u,t,ts) in enumerate(msgs)]
            for ch, msgs in SEED.items()}
    for ch in CHANNELS:
        if ch not in seed: seed[ch] = []
    save_msgs(seed)
    return seed

def save_msgs(m):
    with open(MSGS_FILE,'w') as f: json.dump(m,f,indent=2)

def load_seen():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE) as f: return json.load(f)
        except: pass
    return {}

def save_seen(s):
    with open(SEEN_FILE,'w') as f: json.dump(s,f,indent=2)

def mark_online(username):
    seen = load_seen()
    seen[username] = time.time()
    save_seen(seen)

def get_online():
    seen = load_seen()
    now = time.time()
    return [u for u, t in seen.items() if now - t < 120]  # online if active last 2 min

def now_ts():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# ── CSS ───────────────────────────────────────────────────────────────────────
CSS = """
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',Arial,sans-serif;background:#120d1c;color:#d1d2d3;height:100vh;display:flex;flex-direction:column;}
a{text-decoration:none;color:inherit;}
/* LOGIN */
.login-wrap{min-height:100vh;display:flex;align-items:center;justify-content:center;background:#120d1c;}
.login-card{width:400px;background:#1c1525;border-radius:8px;padding:40px;box-shadow:0 8px 40px rgba(0,0,0,.6);}
.login-logo{text-align:center;margin-bottom:28px;}
.login-logo .ico{font-size:44px;}
.login-logo .nm{font-size:20px;font-weight:700;color:#fff;margin-top:10px;}
.login-logo .sub{font-size:12px;color:#616061;margin-top:4px;}
.f{margin-bottom:16px;}
.f label{display:block;font-size:12px;color:#ccc;margin-bottom:6px;font-weight:600;}
.f input,.f select{width:100%;background:#120d1c;border:1px solid #3b2f52;color:#d1d2d3;
                   padding:11px 12px;border-radius:6px;font-size:14px;outline:none;}
.f input:focus,.f select:focus{border-color:#7c3aed;}
.f select option{background:#120d1c;}
.btn-login{width:100%;background:#7c3aed;color:#fff;border:none;padding:12px;border-radius:6px;
           font-size:15px;font-weight:700;cursor:pointer;}
.btn-login:hover{background:#6d28d9;}
.err{background:rgba(229,75,75,.15);border:1px solid rgba(229,75,75,.4);color:#e54b4b;
     padding:10px 13px;border-radius:6px;font-size:13px;margin-bottom:16px;}
.demo-hint{font-size:11px;color:#3b2f52;text-align:center;margin-top:12px;}
/* MAIN APP LAYOUT */
.app{display:flex;height:100vh;overflow:hidden;}
/* SIDEBAR */
.sb{width:220px;background:#110d1a;display:flex;flex-direction:column;flex-shrink:0;border-right:1px solid #231b30;}
.sb-header{padding:14px 16px 10px;border-bottom:1px solid #231b30;}
.workspace-name{font-size:15px;font-weight:800;color:#fff;margin-bottom:2px;}
.node-badge{display:inline-flex;align-items:center;gap:5px;font-size:10px;
            background:rgba(56,189,248,.15);color:#38bdf8;padding:2px 8px;border-radius:10px;font-family:monospace;}
.sb-section{padding:16px 8px 4px;}
.sb-section-title{font-size:11px;font-weight:700;color:#616061;letter-spacing:.5px;
                  padding:0 8px;margin-bottom:4px;text-transform:uppercase;}
.channel-item{display:flex;align-items:center;gap:8px;padding:6px 10px;border-radius:6px;
              font-size:14px;color:#9a9b9c;cursor:pointer;transition:all .15s;}
.channel-item:hover{background:#231b30;color:#d1d2d3;}
.channel-item.active{background:#7c3aed;color:#fff;}
.channel-icon{font-size:13px;width:16px;text-align:center;}
.channel-name{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.unread-dot{width:7px;height:7px;border-radius:50%;background:#e54b4b;flex-shrink:0;}
.sb-user{margin-top:auto;padding:12px 14px;border-top:1px solid #231b30;
         display:flex;align-items:center;gap:10px;}
.user-ava{font-size:22px;}
.user-name{font-size:13px;color:#d1d2d3;font-weight:600;}
.user-status{font-size:11px;color:#616061;}
.btn-out-small{margin-left:auto;background:none;border:1px solid #3b2f52;color:#616061;
               padding:3px 8px;border-radius:4px;font-size:11px;cursor:pointer;text-decoration:none;}
.btn-out-small:hover{border-color:#e54b4b;color:#e54b4b;}
/* MAIN CHAT AREA */
.chat-area{flex:1;display:flex;flex-direction:column;overflow:hidden;}
.chat-header{padding:12px 20px;border-bottom:1px solid #231b30;background:#120d1c;
             display:flex;align-items:center;gap:10px;}
.chat-header-icon{font-size:18px;}
.chat-header-name{font-size:16px;font-weight:700;color:#fff;}
.chat-header-desc{font-size:13px;color:#616061;margin-left:8px;}
.messages{flex:1;overflow-y:auto;padding:16px 20px;display:flex;flex-direction:column;gap:2px;}
.messages::-webkit-scrollbar{width:6px;}
.messages::-webkit-scrollbar-thumb{background:#3b2f52;border-radius:3px;}
.msg{display:flex;gap:12px;padding:4px 8px;border-radius:6px;transition:background .1s;}
.msg:hover{background:#1e2124;}
.msg.new-user{margin-top:12px;}
.msg-ava{font-size:22px;flex-shrink:0;width:36px;text-align:center;margin-top:2px;}
.msg-body{}
.msg-header{display:flex;align-items:baseline;gap:8px;margin-bottom:3px;}
.msg-author{font-size:14px;font-weight:700;color:#fff;}
.msg-time{font-size:11px;color:#616061;}
.msg-text{font-size:14px;color:#d1d2d3;line-height:1.5;word-break:break-word;}
.msg-continue .msg-ava{visibility:hidden;}
.msg-continue .msg-header{display:none;}
/* INPUT */
.input-area{padding:12px 20px 16px;background:#120d1c;}
.input-box{background:#231b30;border:1px solid #3b2f52;border-radius:8px;
           display:flex;align-items:flex-end;gap:8px;padding:8px 12px;}
.input-box textarea{flex:1;background:none;border:none;color:#d1d2d3;font-size:14px;
                    outline:none;resize:none;max-height:120px;min-height:22px;
                    font-family:inherit;line-height:1.5;}
.input-box textarea::placeholder{color:#616061;}
.send-btn{background:#7c3aed;color:#fff;border:none;padding:7px 14px;border-radius:6px;
          font-size:13px;font-weight:600;cursor:pointer;flex-shrink:0;transition:background .15s;}
.send-btn:hover{background:#6d28d9;}
/* RIGHT SIDEBAR */
.right-sb{width:200px;background:#120d1c;border-left:1px solid #231b30;padding:16px 12px;flex-shrink:0;}
.rs-title{font-size:12px;font-weight:700;color:#616061;text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px;}
.online-user{display:flex;align-items:center;gap:8px;padding:4px 0;font-size:13px;color:#9a9b9c;margin-bottom:4px;}
.online-dot{width:8px;height:8px;border-radius:50%;background:#2bac76;flex-shrink:0;box-shadow:0 0 5px #2bac76;}
.offline-dot{width:8px;height:8px;border-radius:50%;background:#3b2f52;flex-shrink:0;}
.node-info{margin-top:20px;background:#110d1a;border-radius:6px;padding:10px;}
.ni-title{font-size:10px;color:#616061;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px;}
.ni-row{display:flex;justify-content:space-between;font-size:11px;margin-bottom:4px;}
.ni-label{color:#616061;}
.ni-val{color:#38bdf8;font-family:monospace;}
"""

def nav_html(user, channel):
    u = USERS.get(user, {})
    online = get_online()
    # channel list
    ch_items = ''
    for cname, cinfo in CHANNELS.items():
        act = 'active' if cname == channel else ''
        ch_items += f'<a href="/chat/{cname}" class="channel-item {act}" id="ch-{cname}"><span class="channel-icon">{cinfo["icon"]}</span><span class="channel-name">{cname}</span></a>'
    # right sidebar users
    user_rows = ''
    for uname, uinfo in USERS.items():
        if uname in online:
            user_rows += f'<div class="online-user"><span class="online-dot"></span>{uinfo["avatar"]} {uinfo["name"]}</div>'
        else:
            user_rows += f'<div class="online-user"><span class="offline-dot"></span><span style="opacity:.4;">{uinfo["avatar"]} {uinfo["name"]}</span></div>'
    return ch_items, user_rows

def render_msg(m, prev_user=None):
    u = USERS.get(m['user'], {'name': m['user'], 'avatar': '👤'})
    is_continue = (m['user'] == prev_user)
    cls = 'msg-continue' if is_continue else 'msg new-user'
    header = '' if is_continue else f'<div class="msg-header"><span class="msg-author">{u["name"]}</span><span class="msg-time">{m["ts"]}</span></div>'
    return f'<div class="msg {cls}" data-id="{m["id"]}"><div class="msg-ava">{u["avatar"]}</div><div class="msg-body">{header}<div class="msg-text">{m["text"]}</div></div></div>'

def render_app(user, channel):
    ch_items, user_rows = nav_html(user, channel)
    u = USERS.get(user, {})
    msgs = load_msgs().get(channel, [])
    msgs_html = ''
    prev_user = None
    for m in msgs[-80:]:
        msgs_html += render_msg(m, prev_user)
        prev_user = m['user']
    ch_info = CHANNELS.get(channel, {'desc':'','icon':'#️⃣'})
    online_count = len([un for un in USERS if un in get_online()])
    last_id = msgs[-1]['id'] if msgs else 0

    html  = "<!DOCTYPE html><html lang=\"en\"><head>"
    html += "<meta charset=\"UTF-8\"><title>NexusComm — #" + channel + "</title>"
    html += "<style>" + CSS + "</style></head><body>"
    html += """<div class="app">
  <aside class="sb">
    <div class="sb-header">
      <div class="workspace-name">NexusComm</div>
      <div class="node-badge">🟢 DC Data Center · 10.0.0.1</div>
    </div>
    <div class="sb-section">
      <div class="sb-section-title">Channels</div>
      """ + ch_items + """
    </div>
    <div class="sb-user">
      <span class="user-ava">""" + u.get('avatar','👤') + """</span>
      <div><div class="user-name">""" + u.get('name', user) + """</div>
      <div class="user-status">🟢 active</div></div>
      <a href="/logout" class="btn-out-small">out</a>
    </div>
  </aside>

  <div class="chat-area">
    <div class="chat-header">
      <span class="chat-header-icon">""" + ch_info['icon'] + """</span>
      <span class="chat-header-name">#""" + channel + """</span>
      <span class="chat-header-desc">""" + ch_info['desc'] + """</span>
    </div>
    <div class="messages" id="messages">""" + msgs_html + """</div>
    <div class="input-area">
      <div class="input-box">
        <textarea id="msg-input" placeholder="Message #""" + channel + """" rows="1"
                  onkeydown="handleKey(event)" oninput="autoResize(this)"></textarea>
        <button class="send-btn" onclick="sendMsg()">Send</button>
      </div>
    </div>
  </div>

  <aside class="right-sb">
    <div class="rs-title">Online (""" + str(online_count) + """)</div>
    <div id="online-list">""" + user_rows + """</div>
    <div class="node-info">
      <div class="ni-title">Node Info</div>
      <div class="ni-row"><span class="ni-label">Node</span><span class="ni-val">DC</span></div>
      <div class="ni-row"><span class="ni-label">IP</span><span class="ni-val">10.0.0.1</span></div>
      <div class="ni-row"><span class="ni-label">Service</span><span class="ni-val">NexusComm</span></div>
      <div class="ni-row"><span class="ni-label">Port</span><span class="ni-val">5006</span></div>
    </div>
  </aside>
</div>
"""
    html += "<script>"
    html += "const channel = " + repr(channel) + ";"
    html += "const user = " + repr(user) + ";"
    html += "let lastId = " + str(last_id) + ";"
    html += """
function scrollBottom() {
  const el = document.getElementById('messages');
  el.scrollTop = el.scrollHeight;
}
function autoResize(ta) {
  ta.style.height = 'auto';
  ta.style.height = Math.min(ta.scrollHeight, 120) + 'px';
}
function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMsg(); }
}
async function sendMsg() {
  const inp = document.getElementById('msg-input');
  const text = inp.value.trim();
  if (!text) return;
  inp.value = ''; inp.style.height = 'auto';
  await fetch('/api/send', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({channel, text})
  });
  pollMessages();
}
async function pollMessages() {
  const res = await fetch('/api/messages/' + channel + '?since=' + lastId);
  const data = await res.json();
  if (data.messages && data.messages.length > 0) {
    const box = document.getElementById('messages');
    data.messages.forEach(m => {
      box.insertAdjacentHTML('beforeend', m.html);
      lastId = Math.max(lastId, m.id);
    });
    scrollBottom();
  }
}
async function pollUsers() {
  const res = await fetch('/api/users');
  const data = await res.json();
  document.getElementById('online-list').innerHTML = data.html;
}
scrollBottom();
setInterval(pollMessages, 3000);
setInterval(pollUsers, 15000);
"""
    html += "</script></body></html>"
    return html

# ── ROUTES ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user' not in session: return redirect('/login')
    return redirect('/chat/general')

@app.route('/chat/<channel>')
def chat(channel):
    if 'user' not in session: return redirect('/login')
    if channel not in CHANNELS: return redirect('/chat/general')
    mark_online(session['user'])
    return render_app(session['user'], channel)

@app.route('/api/messages/<channel>')
def api_messages(channel):
    if 'user' not in session: return jsonify({'messages': []})
    mark_online(session['user'])
    since = int(request.args.get('since', 0))
    msgs = load_msgs().get(channel, [])
    new_msgs = [m for m in msgs if m['id'] > since]
    result = []
    for m in new_msgs:
        u = USERS.get(m['user'], {'name': m['user'], 'avatar': '👤'})
        result.append({
            'id': m['id'],
            'html': f'<div class="msg new-user" data-id="{m["id"]}"><div class="msg-ava">{u["avatar"]}</div><div class="msg-body"><div class="msg-header"><span class="msg-author">{u["name"]}</span><span class="msg-time">{m["ts"]}</span></div><div class="msg-text">{m["text"]}</div></div></div>'
        })
    return jsonify({'messages': result})

@app.route('/api/send', methods=['POST'])
def api_send():
    if 'user' not in session: return jsonify({'error': 'not logged in'}), 401
    data = request.json or {}
    channel = data.get('channel', 'general')
    text = (data.get('text') or '').strip()
    if not text or channel not in CHANNELS:
        return jsonify({'error': 'invalid'}), 400
    msgs = load_msgs()
    if channel not in msgs: msgs[channel] = []
    new_id = max((m['id'] for m in msgs[channel]), default=0) + 1
    msgs[channel].append({'id': new_id, 'user': session['user'], 'text': text, 'ts': now_ts()})
    save_msgs(msgs)
    return jsonify({'ok': True, 'id': new_id})

@app.route('/api/users')
def api_users():
    if 'user' not in session: return jsonify({'html': ''})
    mark_online(session['user'])
    online = get_online()
    html = ''
    for uname, uinfo in USERS.items():
        if uname in online:
            html += f'<div class="online-user"><span class="online-dot"></span>{uinfo["avatar"]} {uinfo["name"]}</div>'
        else:
            html += f'<div class="online-user"><span class="offline-dot"></span><span style="opacity:.4;">{uinfo["avatar"]} {uinfo["name"]}</span></div>'
    return jsonify({'html': html, 'count': len(online)})

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        u = request.form.get('username','')
        p = request.form.get('password','')
        if u in PASSWORDS and PASSWORDS[u] == p:
            session['user'] = u
            mark_online(u)
            return redirect('/chat/general')
        err = '<div class="err">Invalid credentials.</div>'
    else:
        err = ''
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>NexusComm — Sign In</title><style>{CSS}</style></head><body>
<div class="login-wrap"><div class="login-card">
  <div class="login-logo"><div class="ico">💬</div>
    <div class="nm">NexusComm</div>
    <div class="sub">Secure Business Messaging · DC Data Center</div></div>
  {err}
  <form method="POST">
    <div class="f"><label>Username</label><input name="username" placeholder="e.g. jdoe" autocomplete="off" required></div>
    <div class="f"><label>Password</label><input type="password" name="password" required></div>
    <button type="submit" class="btn-login">Sign in to NexusComm</button>
  </form>
  <div style='font-size:10px;color:#3b2f52;text-align:center;margin-top:8px;'>Powered by NodeNet ISP · DC Data Center</div>
  <div class="demo-hint">admin/admin · jdoe/pass · mlee/pass · achan/pass</div>
</div></div></body></html>"""

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    print("NexusComm — DC Node — starting on http://0.0.0.0:5006")
    app.run(host='0.0.0.0', port=5006, debug=False)
