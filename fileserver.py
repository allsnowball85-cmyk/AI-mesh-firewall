from flask import Flask, render_template_string, request, redirect, send_from_directory, jsonify
import os, json, datetime

app = Flask(__name__)

VAULT_DIR = os.path.expanduser('~/meshvault')
META_FILE = os.path.join(VAULT_DIR, '.meta.json')
os.makedirs(VAULT_DIR, exist_ok=True)

NODES = {
    'dc':      {'name': 'Washington DC', 'ip': '10.0.0.1', 'color': '#38bdf8'},
    'seattle': {'name': 'Seattle',       'ip': '10.0.0.2', 'color': '#c084fc'},
    'sf':      {'name': 'San Francisco', 'ip': '10.0.0.3', 'color': '#4ade80'},
}

def load_meta():
    if os.path.exists(META_FILE):
        try:
            with open(META_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_meta(meta):
    with open(META_FILE, 'w') as f:
        json.dump(meta, f, indent=2)

def fmt_size(b):
    for u in ['B','KB','MB','GB']:
        if b < 1024:
            return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} TB"

def get_files():
    meta = load_meta()
    files = []
    for name in sorted(os.listdir(VAULT_DIR)):
        if name.startswith('.'):
            continue
        path = os.path.join(VAULT_DIR, name)
        m = meta.get(name, {})
        files.append({
            'name':     name,
            'size':     fmt_size(os.path.getsize(path)),
            'node':     m.get('node', 'dc'),
            'uploaded': m.get('uploaded', 'Unknown'),
            'uploader': m.get('uploader', 'System'),
        })
    return files

# ── TEMPLATE ───────────────────────────────────────────────────────────────────

HTML = """
<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><title>VaultNet — Secure Cloud Storage</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',Arial,sans-serif;background:#050c14;color:#c4cdd8;min-height:100vh;}
/* NAV */
.nav{background:#0d1219;border-bottom:1px solid #1e2a3a;height:58px;display:flex;
     align-items:center;justify-content:space-between;padding:0 28px;position:sticky;top:0;z-index:100;}
.nav-brand{display:flex;align-items:center;gap:12px;}
.nav-logo{font-size:22px;}
.nav-name{font-size:16px;font-weight:800;color:#38bdf8;letter-spacing:.5px;}
.nav-sub{font-size:11px;color:#334155;margin-left:12px;letter-spacing:2px;text-transform:uppercase;}
.nav-right{font-size:12px;color:#475569;font-family:monospace;}
/* MAIN */
.container{max-width:1100px;margin:0 auto;padding:32px 20px;}
/* STATS ROW */
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:28px;}
.stat-card{background:#091016;border:1px solid #1e2a3a;border-radius:10px;padding:18px;}
.stat-val{font-size:26px;font-weight:700;color:#38bdf8;}
.stat-label{font-size:11px;color:#475569;margin-top:4px;letter-spacing:1px;text-transform:uppercase;}
/* NODE PILLS */
.node-pills{display:flex;gap:10px;margin-bottom:24px;flex-wrap:wrap;}
.node-pill{display:flex;align-items:center;gap:8px;padding:8px 14px;border-radius:8px;
           border:1px solid #1e2a3a;background:#091016;font-size:12px;font-family:monospace;}
.npd{width:8px;height:8px;border-radius:50%;box-shadow:0 0 6px;}
/* UPLOAD */
.upload-box{background:#091016;border:2px dashed #1e2a3a;border-radius:12px;
            padding:36px;text-align:center;margin-bottom:28px;transition:border-color .2s;}
.upload-box:hover,.upload-box.drag{border-color:#38bdf8;}
.upload-icon{font-size:40px;margin-bottom:14px;}
.upload-title{font-size:16px;font-weight:600;color:#e2e8f0;margin-bottom:6px;}
.upload-sub{font-size:13px;color:#475569;margin-bottom:20px;}
.upload-form{display:flex;gap:10px;justify-content:center;flex-wrap:wrap;align-items:center;}
.file-input-wrap{position:relative;}
.file-input-wrap input[type=file]{position:absolute;inset:0;opacity:0;cursor:pointer;width:100%;}
.file-btn{background:#1e3a5f;color:#38bdf8;border:1px solid #38bdf8;padding:9px 18px;
          border-radius:7px;font-size:13px;cursor:pointer;white-space:nowrap;}
.node-sel{background:#141924;border:1px solid #1e2a3a;color:#c4cdd8;padding:9px 12px;
          border-radius:7px;font-size:13px;outline:none;}
.node-sel:focus{border-color:#38bdf8;}
.node-sel option{background:#091016;}
.up-label{font-size:12px;color:#334155;}
input[type=text].up-name{background:#141924;border:1px solid #1e2a3a;color:#c4cdd8;
                          padding:9px 12px;border-radius:7px;font-size:13px;outline:none;min-width:160px;}
.btn-upload{background:#38bdf8;color:#07090f;border:none;padding:9px 22px;border-radius:7px;
            font-size:13px;font-weight:700;cursor:pointer;transition:background .2s;}
.btn-upload:hover{background:#7dd3fc;}
/* FILE TABLE */
.section-title{font-size:11px;letter-spacing:3px;text-transform:uppercase;color:#334155;margin-bottom:14px;}
.file-table-wrap{background:#091016;border:1px solid #1e2a3a;border-radius:10px;overflow:hidden;}
table{width:100%;border-collapse:collapse;}
th{background:#080c12;font-size:10px;letter-spacing:1.5px;text-transform:uppercase;
   color:#334155;padding:12px 16px;text-align:left;}
td{padding:13px 16px;font-size:13px;border-bottom:1px solid #0a0e15;}
tr:last-child td{border-bottom:none;}
tr:hover td{background:#0b1018;}
.fn{color:#e2e8f0;font-weight:500;}
.fs{font-family:monospace;color:#475569;}
.nb{display:inline-flex;align-items:center;gap:6px;font-size:11px;padding:3px 10px;
    border-radius:20px;font-family:monospace;font-weight:500;}
.ts{font-family:monospace;font-size:11px;color:#334155;}
.btn-dl{background:#1a2a1a;color:#4ade80;border:1px solid #1a4a1a;padding:5px 12px;
        border-radius:6px;font-size:11px;cursor:pointer;text-decoration:none;display:inline-block;
        transition:all .2s;}
.btn-dl:hover{background:#4ade80;color:#07090f;}
.btn-del{background:#2a1a1a;color:#f87171;border:1px solid #4a1a1a;padding:5px 12px;
         border-radius:6px;font-size:11px;cursor:pointer;text-decoration:none;display:inline-block;
         transition:all .2s;margin-left:6px;}
.btn-del:hover{background:#f87171;color:#07090f;}
.empty{padding:48px;text-align:center;color:#334155;font-size:14px;}
/* TOAST */
#toast{position:fixed;bottom:20px;right:20px;background:#091016;border:1px solid #1e2a3a;
       border-radius:8px;padding:11px 18px;font-size:12px;font-family:monospace;
       opacity:0;transition:opacity .3s;pointer-events:none;z-index:200;}
#toast.show{opacity:1;}
#toast.ok{border-color:#4ade80;color:#4ade80;}
#toast.err{border-color:#f87171;color:#f87171;}
@media(max-width:600px){.stats{grid-template-columns:1fr 1fr;}.upload-form{flex-direction:column;}}
</style></head>
<body>

<nav class="nav">
  <div class="nav-brand">
    <span class="nav-logo">🗄️</span>
    <span class="nav-name">VaultNet</span>
    <span class="nav-sub">Secure Cloud Storage · NodeNet ISP</span>
  </div>
  <div class="nav-right">NodeNet ISP · 3 Data Centers · {{ files|length }} file(s) stored</div>
</nav>

<div class="container">

  <!-- STATS -->
  <div class="stats">
    <div class="stat-card">
      <div class="stat-val">{{ files|length }}</div>
      <div class="stat-label">Files Stored</div>
    </div>
    <div class="stat-card">
      <div class="stat-val" style="color:#4ade80;">3</div>
      <div class="stat-label">Active Nodes</div>
    </div>
    <div class="stat-card">
      <div class="stat-val" style="color:#c084fc;">ON</div>
      <div class="stat-label">Mesh Encryption</div>
    </div>
    <div class="stat-card">
      <div class="stat-val" style="color:#fbbf24;">AES</div>
      <div class="stat-label">Transfer Protocol</div>
    </div>
  </div>

  <!-- NODE STATUS -->
  <div class="node-pills">
    {% for nk, n in nodes.items() %}
    <div class="node-pill">
      <span class="npd" style="background:{{ n.color }};box-shadow:0 0 6px {{ n.color }};"></span>
      {{ n.name }} &nbsp;·&nbsp; {{ n.ip }} &nbsp;·&nbsp;
      <span style="color:{{ n.color }};">{{ files|selectattr('node','equalto',nk)|list|length }} files</span>
    </div>
    {% endfor %}
  </div>

  <!-- UPLOAD -->
  <div class="upload-box" id="drop-zone">
    <div class="upload-icon">📤</div>
    <div class="upload-title">Upload to VaultNet</div>
    <div class="upload-sub">Drag & drop a file here, or click Browse to select one</div>
    <form method="POST" action="/upload" enctype="multipart/form-data" id="upload-form">
      <div class="upload-form">
        <div class="file-input-wrap">
          <div class="file-btn" id="file-btn">📂 Browse Files</div>
          <input type="file" name="file" id="file-input" onchange="fileChosen(this)">
        </div>
        <select name="node" class="node-sel">
          {% for nk, n in nodes.items() %}
          <option value="{{ nk }}">{{ n.name }} Node · {{ n.ip }}</option>
          {% endfor %}
        </select>
        <input type="text" name="uploader" class="up-name" placeholder="Your name (optional)">
        <button type="submit" class="btn-upload">⬆ Upload</button>
      </div>
    </form>
  </div>

  <!-- FILES -->
  <div class="section-title">Stored Files</div>
  <div class="file-table-wrap">
    {% if files %}
    <table>
      <thead><tr>
        <th>File Name</th><th>Size</th><th>Node</th><th>Uploaded</th><th>By</th><th>Actions</th>
      </tr></thead>
      <tbody>
      {% for f in files %}
      <tr>
        <td><span class="fn">{{ f.name }}</span></td>
        <td><span class="fs">{{ f.size }}</span></td>
        <td>
          <span class="nb" style="background:{{ nodes[f.node].color }}1a;color:{{ nodes[f.node].color }};border:1px solid {{ nodes[f.node].color }}33;">
            🟢 {{ nodes[f.node].name }}
          </span>
        </td>
        <td class="ts">{{ f.uploaded }}</td>
        <td class="ts">{{ f.uploader }}</td>
        <td>
          <a href="/download/{{ f.name }}" class="btn-dl">⬇ Download</a>
          <a href="/delete/{{ f.name }}" class="btn-del" onclick="return confirm('Delete {{ f.name }}?')">🗑 Delete</a>
        </td>
      </tr>
      {% endfor %}
      </tbody>
    </table>
    {% else %}
    <div class="empty">📭 &nbsp; No files stored yet. Upload your first file above.</div>
    {% endif %}
  </div>

</div>

<div id="toast"></div>

<script>
// Drag & drop
const zone = document.getElementById('drop-zone');
zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag'); });
zone.addEventListener('dragleave', () => zone.classList.remove('drag'));
zone.addEventListener('drop', e => {
  e.preventDefault(); zone.classList.remove('drag');
  const files = e.dataTransfer.files;
  if (files.length) {
    const dt = new DataTransfer();
    dt.items.add(files[0]);
    document.getElementById('file-input').files = dt.files;
    fileChosen(document.getElementById('file-input'));
  }
});

function fileChosen(input) {
  if (input.files.length) {
    document.getElementById('file-btn').textContent = '📄 ' + input.files[0].name;
  }
}

// Toast
{% if message %}
const t = document.getElementById('toast');
t.textContent = '{{ message }}';
t.className = 'show {{ msg_type }}';
setTimeout(() => t.className = '', 3000);
{% endif %}
</script>
</body></html>
"""

# ── ROUTES ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template_string(HTML, files=get_files(), nodes=NODES, message='', msg_type='ok')

@app.route('/upload', methods=['POST'])
def upload():
    f = request.files.get('file')
    node     = request.form.get('node', 'dc')
    uploader = request.form.get('uploader', 'Anonymous').strip() or 'Anonymous'
    if not f or not f.filename:
        return redirect('/')
    filename = f.filename
    f.save(os.path.join(VAULT_DIR, filename))
    meta = load_meta()
    meta[filename] = {
        'node':     node,
        'uploaded': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
        'uploader': uploader,
    }
    save_meta(meta)
    return render_template_string(HTML, files=get_files(), nodes=NODES,
                                  message=f'Uploaded: {filename}', msg_type='ok')

@app.route('/download/<path:filename>')
def download(filename):
    return send_from_directory(VAULT_DIR, filename, as_attachment=True)

@app.route('/delete/<path:filename>')
def delete(filename):
    path = os.path.join(VAULT_DIR, filename)
    if os.path.exists(path):
        os.remove(path)
        meta = load_meta()
        meta.pop(filename, None)
        save_meta(meta)
    return redirect('/')

if __name__ == '__main__':
    print("VaultNet — starting on http://127.0.0.1:5002")
    print(f"Files stored in: {VAULT_DIR}")
    app.run(host='0.0.0.0', port=5002, debug=True)
