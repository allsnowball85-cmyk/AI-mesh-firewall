from flask import Flask, request, redirect, session, Response, jsonify
import os, json, datetime, re, uuid

app = Flask(__name__)
app.secret_key = 'meshstream_2025'

STREAM_DIR = os.path.expanduser('~/meshstream')
META_FILE  = os.path.join(STREAM_DIR, '.meta.json')
os.makedirs(STREAM_DIR, exist_ok=True)

NODES = {
    'dc':      {'name': 'DC',            'ip': '10.0.0.1', 'color': '#38bdf8'},
    'seattle': {'name': 'Seattle',       'ip': '10.0.0.2', 'color': '#c084fc'},
    'sf':      {'name': 'San Francisco', 'ip': '10.0.0.3', 'color': '#4ade80'},
}

def load_meta():
    if os.path.exists(META_FILE):
        try:
            with open(META_FILE) as f: return json.load(f)
        except: pass
    return {}

def save_meta(m): 
    with open(META_FILE, 'w') as f: json.dump(m, f, indent=2)

def fmt_size(b):
    for u in ['B','KB','MB','GB']:
        if b < 1024: return f"{b:.1f} {u}"
        b /= 1024
    return f"{b:.1f} TB"

def fmt_views(n):
    if n >= 1000: return f"{n/1000:.1f}K"
    return str(n)

# ── STREAMING ROUTE (range-request aware) ────────────────────────────────────
@app.route('/stream/<vid_id>')
def stream_video(vid_id):
    meta = load_meta()
    if vid_id not in meta:
        return "Video not found", 404
    filename = meta[vid_id]['filename']
    path = os.path.join(STREAM_DIR, filename)
    if not os.path.exists(path):
        return "File not found on disk", 404

    # Increment view count
    meta[vid_id]['views'] = meta[vid_id].get('views', 0) + 1
    save_meta(meta)

    file_size = os.path.getsize(path)
    rng = request.headers.get('Range')

    if rng:
        m = re.search(r'bytes=(\d+)-(\d*)', rng)
        start = int(m.group(1))
        end   = int(m.group(2)) if m.group(2) else file_size - 1
        end   = min(end, file_size - 1)
        length = end - start + 1
        with open(path, 'rb') as f:
            f.seek(start)
            data = f.read(length)
        resp = Response(data, 206, mimetype='video/mp4', direct_passthrough=True)
        resp.headers['Content-Range']  = f'bytes {start}-{end}/{file_size}'
        resp.headers['Accept-Ranges']  = 'bytes'
        resp.headers['Content-Length'] = str(length)
        return resp

    resp = Response(open(path, 'rb'), 200, mimetype='video/mp4', direct_passthrough=True)
    resp.headers['Accept-Ranges']  = 'bytes'
    resp.headers['Content-Length'] = str(file_size)
    return resp

# ── HTML ─────────────────────────────────────────────────────────────────────
CSS = """
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',Arial,sans-serif;background:#050f0a;color:#e2e8f0;min-height:100vh;}
a{text-decoration:none;color:inherit;}
.nav{background:#091510;border-bottom:1px solid #1e2a3a;height:56px;display:flex;
     align-items:center;justify-content:space-between;padding:0 24px;
     position:sticky;top:0;z-index:100;}
.nav-brand{display:flex;align-items:center;gap:10px;font-size:16px;font-weight:700;color:#059669;}
.nav-links{display:flex;gap:8px;}
.nav-links a{padding:6px 14px;border-radius:6px;font-size:13px;color:#64748b;transition:all .2s;}
.nav-links a:hover{background:#1e2a3a;color:#e2e8f0;}
.btn-upload{background:#059669;color:#fff;border:none;padding:8px 18px;border-radius:7px;
            font-size:13px;font-weight:600;cursor:pointer;text-decoration:none;}
.btn-upload:hover{background:#047857;}
.container{max-width:1200px;margin:0 auto;padding:28px 20px;}
.page-title{font-size:18px;font-weight:700;color:#fff;margin-bottom:20px;}
.video-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:20px;}
.video-card{background:#091510;border-radius:10px;overflow:hidden;
            border:1px solid #1e2a3a;cursor:pointer;transition:transform .2s,border-color .2s;}
.video-card:hover{transform:translateY(-3px);border-color:#059669;}
.video-thumb{width:100%;aspect-ratio:16/9;display:flex;align-items:center;justify-content:center;
             font-size:40px;background:linear-gradient(135deg,#1e2a3a,#0d1117);position:relative;}
.play-icon{font-size:48px;opacity:.6;transition:opacity .2s;}
.video-card:hover .play-icon{opacity:1;}
.duration-badge{position:absolute;bottom:8px;right:8px;background:rgba(0,0,0,.8);
                color:#fff;font-size:10px;padding:2px 6px;border-radius:4px;font-family:monospace;}
.video-info{padding:12px;}
.video-title{font-size:14px;font-weight:600;color:#f1f5f9;margin-bottom:6px;
             white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.video-meta{font-size:11px;color:#475569;}
.node-dot{width:6px;height:6px;border-radius:50%;display:inline-block;margin-right:4px;}
.video-tags{display:flex;flex-wrap:wrap;gap:4px;margin-top:8px;}
.tag{font-size:10px;background:#1e2a3a;color:#64748b;padding:2px 7px;border-radius:10px;}
.empty{text-align:center;padding:80px 20px;color:#334155;}
.empty h2{font-size:20px;color:#475569;margin-bottom:10px;}
/* WATCH PAGE */
.watch-layout{display:grid;grid-template-columns:1fr 340px;gap:24px;align-items:start;}
.video-player-wrap video{width:100%;border-radius:10px;background:#000;display:block;}
.video-details{margin-top:14px;}
.video-details h1{font-size:18px;font-weight:700;color:#fff;margin-bottom:8px;}
.video-stats{display:flex;align-items:center;gap:16px;font-size:12px;color:#475569;padding-bottom:14px;border-bottom:1px solid #1e2a3a;}
.video-desc{margin-top:14px;font-size:13px;color:#94a3b8;line-height:1.7;}
.node-badge{display:inline-flex;align-items:center;gap:5px;font-size:11px;padding:3px 10px;
            border-radius:20px;font-family:monospace;font-weight:500;}
.sidebar-title{font-size:12px;letter-spacing:2px;text-transform:uppercase;color:#334155;margin-bottom:12px;}
.sidebar-card{display:flex;gap:10px;margin-bottom:12px;cursor:pointer;padding:8px;
              border-radius:8px;transition:background .2s;}
.sidebar-card:hover{background:#091510;}
.sidebar-thumb{width:90px;aspect-ratio:16/9;border-radius:6px;display:flex;align-items:center;
               justify-content:center;font-size:20px;flex-shrink:0;background:#1e2a3a;}
.sidebar-info .title{font-size:12px;font-weight:600;color:#e2e8f0;margin-bottom:4px;
                      display:-webkit-box;-webkit-line-clamp:2;-webkit-box-clamp:2;overflow:hidden;}
.sidebar-info .meta{font-size:10px;color:#475569;}
/* UPLOAD PAGE */
.upload-card{background:#091510;border:1px solid #1e2a3a;border-radius:12px;padding:32px;max-width:680px;}
.drop-zone{border:2px dashed #1e2a3a;border-radius:10px;padding:48px;text-align:center;
           margin-bottom:24px;transition:border-color .2s;cursor:pointer;position:relative;}
.drop-zone:hover,.drop-zone.drag{border-color:#059669;}
.drop-icon{font-size:40px;margin-bottom:12px;}
.drop-text{font-size:15px;color:#94a3b8;margin-bottom:6px;}
.drop-sub{font-size:12px;color:#334155;}
.f{margin-bottom:16px;}
.f label{display:block;font-size:10px;letter-spacing:2px;text-transform:uppercase;
         color:#334155;margin-bottom:7px;}
.f input,.f textarea,.f select{width:100%;background:#070910;border:1px solid #1e2a3a;
                                color:#e2e8f0;padding:10px 12px;border-radius:7px;font-size:13px;outline:none;}
.f input:focus,.f textarea:focus,.f select:focus{border-color:#059669;}
.f textarea{resize:vertical;min-height:80px;}
.f select option{background:#091510;}
.btn-sub{background:#059669;color:#fff;border:none;padding:12px 28px;border-radius:7px;
         font-size:13px;font-weight:700;cursor:pointer;transition:background .2s;}
.btn-sub:hover{background:#047857;}
.toast{position:fixed;bottom:20px;right:20px;background:#091510;border:1px solid #4ade80;
       color:#4ade80;border-radius:8px;padding:11px 18px;font-size:12px;font-family:monospace;
       box-shadow:0 8px 24px rgba(0,0,0,.5);opacity:0;transition:opacity .3s;pointer-events:none;}
.toast.show{opacity:1;}
@media(max-width:900px){.watch-layout{grid-template-columns:1fr;}.sidebar-section{display:none;}}
"""

def nav_html(active='home'):
    return f"""
<nav class="nav">
  <a href="/" class="nav-brand">▶ ClearCast</a>
  <div class="nav-links">
    <a href="/" style="{'color:#059669;background:#1e0a0a;' if active=='home' else ''}">Home</a>
    <a href="/upload" style="{'color:#059669;background:#1e0a0a;' if active=='upload' else ''}">Upload</a>
    <a href="http://127.0.0.1:5001" target="_blank">Hub</a>
  </div>
  <a href="/upload" class="btn-upload">+ Upload Video</a>
</nav>"""

def video_card_html(vid_id, v):
    node = v.get('node','dc')
    nc = NODES.get(node, NODES['dc'])
    tags = ''.join(f'<span class="tag">{t}</span>' for t in v.get('tags','').split(',') if t.strip())
    return f"""
<a href="/watch/{vid_id}" class="video-card">
  <div class="video-thumb" style="background:linear-gradient(135deg,#1e2a3a,{'#0a1a12' if node=='dc' else '#0a1a0a' if node=='sf' else '#1a0a1a'})">
    <span class="play-icon">▶</span>
    <span class="duration-badge">{fmt_size(v.get('size',0))}</span>
  </div>
  <div class="video-info">
    <div class="video-title">{v.get('title','Untitled')}</div>
    <div class="video-meta">
      <span class="node-dot" style="background:{nc['color']};"></span>
      {nc['name']} · {fmt_views(v.get('views',0))} views · {v.get('uploaded','')[:10]}
    </div>
    <div class="video-tags">{tags}</div>
  </div>
</a>"""

@app.route('/')
def index():
    meta = load_meta()
    if meta:
        cards = ''.join(video_card_html(vid_id, v) for vid_id, v in sorted(meta.items(), key=lambda x: x[1].get('uploaded',''), reverse=True))
        grid  = f'<div class="video-grid">{cards}</div>'
    else:
        grid = '''<div class="empty">
          <h2>No videos yet</h2>
          <p style="margin-bottom:20px;">Upload your first video to get started.</p>
          <a href="/upload" class="btn-sub">Upload a Video</a>
        </div>'''
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ClearCast</title><style>{CSS}</style></head><body>
{nav_html('home')}
<div class="container">
  <div class="page-title">ClearCast — Professional Video Platform</div>
  {grid}
<div style="text-align:center;padding:16px;font-size:11px;color:#1a3a2a;border-top:1px solid #0a2318;margin-top:20px;">Powered by <strong style="color:#059669;">NodeNet ISP</strong> · Seattle Data Center · 10.0.0.2</div></div></body></html>"""

@app.route('/watch/<vid_id>')
def watch(vid_id):
    meta = load_meta()
    if vid_id not in meta:
        return redirect('/')
    v = meta[vid_id]
    node = v.get('node','dc')
    nc = NODES.get(node, NODES['dc'])
    others = [(oid, ov) for oid, ov in sorted(meta.items(), key=lambda x: x[1].get('views',0), reverse=True) if oid != vid_id][:8]
    sidebar_cards = ''.join(f'''
<a href="/watch/{oid}" class="sidebar-card">
  <div class="sidebar-thumb" style="background:linear-gradient(135deg,#1e2a3a,#0d1117);">▶</div>
  <div class="sidebar-info">
    <div class="title">{ov.get("title","Untitled")}</div>
    <div class="meta">{fmt_views(ov.get("views",0))} views · {NODES.get(ov.get("node","dc"),NODES["dc"])["name"]}</div>
  </div>
</a>''' for oid, ov in others)

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{v.get('title','Video')} — ClearCast</title><style>{CSS}</style></head><body>
{nav_html()}
<div class="container">
  <div class="watch-layout">
    <div>
      <div class="video-player-wrap">
        <video controls autoplay controlslist="nodownload" oncontextmenu="return false">
          <source src="/stream/{vid_id}" type="video/mp4">
          Your browser doesn't support HTML5 video.
        </video>
      </div>
      <div class="video-details">
        <h1>{v.get('title','Untitled')}</h1>
        <div class="video-stats">
          <span>{fmt_views(v.get('views',0))} views</span>
          <span>Uploaded {v.get('uploaded','')[:10]}</span>
          <span class="node-badge" style="background:{nc['color']}1a;color:{nc['color']};border:1px solid {nc['color']}33;">
            {nc['name']} Node · {nc['ip']}
          </span>
          <span>{fmt_size(v.get('size',0))}</span>
        </div>
        <div class="video-desc">{v.get('description','No description.')}</div>
      </div>
    </div>
    <div class="sidebar-section">
      <div class="sidebar-title">Up Next</div>
      {sidebar_cards or '<div style="color:#334155;font-size:12px;">No other videos yet.</div>'}
    </div>
  </div>
</div></body></html>"""

UPLOAD_HTML = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Upload — ClearCast</title><style>""" + CSS + """
.dz{border:2px dashed #1e2a3a;border-radius:10px;padding:48px 24px;text-align:center;
    margin-bottom:20px;transition:all .2s;}
.dz.drag{border-color:#059669;background:#0a1a12;}
.dz.chosen{border-color:#4ade80;background:#0a1a0a;}
.browse-btn{background:#064e3b;color:#059669;border:1px solid #059669;
            padding:9px 22px;border-radius:7px;font-size:13px;cursor:pointer;
            transition:all .2s;margin-top:14px;}
.browse-btn:hover{background:#38bdf8;color:#0d1117;}
.chosen-bar{background:#0a1a0a;border:1px solid #1a4a1a;border-radius:8px;
            padding:12px 16px;margin-bottom:18px;display:none;align-items:center;gap:10px;}
.chosen-bar.show{display:flex;}
.f{margin-bottom:16px;}
.f label{display:block;font-size:10px;letter-spacing:2px;text-transform:uppercase;
         color:#334155;margin-bottom:7px;}
.f input,.f textarea,.f select{width:100%;background:#070910;border:1px solid #1e2a3a;
  color:#e2e8f0;padding:10px 12px;border-radius:7px;font-size:13px;outline:none;}
.f input:focus,.f textarea:focus,.f select:focus{border-color:#059669;}
.f textarea{resize:vertical;min-height:80px;}
.f select option{background:#091510;}
.btn-sub2{background:#059669;color:#fff;border:none;padding:12px 28px;border-radius:7px;
          font-size:13px;font-weight:700;cursor:pointer;}
.btn-sub2:hover{background:#047857;}
.btn-sub2:disabled{background:#0a2318;color:#475569;cursor:not-allowed;}
</style></head><body>
{nav}
<div class="container">
  <div class="page-title">Upload Video</div>
  <div class="upload-card">
    <form method="POST" action="/upload" enctype="multipart/form-data" id="upload-form">

      <!-- Hidden file input — triggered ONLY by the Browse button below -->
      <input type="file" name="file" id="fi" accept="video/mp4" style="display:none;">

      <!-- Drop zone — purely visual, no input inside -->
      <div class="dz" id="dz">
        <div style="font-size:42px;margin-bottom:10px;" id="dz-ico">🎬</div>
        <div style="font-size:14px;color:#94a3b8;" id="dz-txt">Drag an MP4 file here</div>
        <div style="font-size:12px;color:#334155;margin-top:6px;">or use the button below</div>
        <br>
        <button type="button" class="browse-btn"
                onclick="document.getElementById('fi').click()">
          📂 Browse &amp; Select MP4
        </button>
      </div>

      <!-- Confirmation bar shown after file is chosen -->
      <div class="chosen-bar" id="cbar">
        <span style="font-size:22px;">✅</span>
        <div>
          <div id="cname" style="font-size:13px;color:#4ade80;font-weight:600;"></div>
          <div id="csize" style="font-size:11px;color:#334155;"></div>
        </div>
        <button type="button" onclick="clearFile()"
                style="margin-left:auto;background:none;border:none;color:#f87171;cursor:pointer;">
          ✕ Remove
        </button>
      </div>

      <div class="f"><label>Title</label>
        <input type="text" name="title" id="ti" placeholder="Video title" required></div>
      <div class="f"><label>Description</label>
        <textarea name="description" placeholder="Describe the video..."></textarea></div>
      <div class="f"><label>Tags (comma separated)</label>
        <input type="text" name="tags" placeholder="e.g. security, networking, demo"></div>
      <div class="f"><label>Hosting Node</label>
        <select name="node">
          <option value="dc">Washington DC — Node 10.0.0.1</option>
          <option value="seattle">Seattle — Node 10.0.0.2</option>
          <option value="sf">San Francisco — Node 10.0.0.3</option>
        </select></div>

      <button type="submit" class="btn-sub2" id="sb" disabled>⬆ Upload Video</button>
      <a href="/" style="margin-left:16px;font-size:12px;color:#475569;">Cancel</a>
      <div id="umsg" style="display:none;margin-top:14px;font-size:13px;color:#4ade80;">
        ⏳ Uploading — please wait, do not close this tab...
      </div>
    </form>
  </div>
</div>
<script>
const fi = document.getElementById('fi');
const dz = document.getElementById('dz');
const sb = document.getElementById('sb');
const ti = document.getElementById('ti');
function fmt(b){
  if(b>=1073741824)return(b/1073741824).toFixed(1)+' GB';
  if(b>=1048576)return(b/1048576).toFixed(1)+' MB';
  return(b/1024).toFixed(1)+' KB';
}
function setFile(f){
  document.getElementById('cname').textContent=f.name;
  document.getElementById('csize').textContent=fmt(f.size);
  document.getElementById('cbar').classList.add('show');
  document.getElementById('dz-ico').textContent='✅';
  document.getElementById('dz-txt').textContent='File ready';
  dz.classList.add('chosen');
  sb.disabled=false;
  if(!ti.value) ti.value=f.name.replace(/[.]mp4$/i,'').replace(/[-_]/g,' ');
}
function clearFile(){
  fi.value='';
  document.getElementById('cbar').classList.remove('show');
  document.getElementById('dz-ico').textContent='🎬';
  document.getElementById('dz-txt').textContent='Drag an MP4 file here';
  dz.classList.remove('chosen');
  sb.disabled=true;
}
fi.addEventListener('change',function(){if(this.files[0])setFile(this.files[0]);});
dz.addEventListener('dragover',e=>{e.preventDefault();dz.classList.add('drag');});
dz.addEventListener('dragleave',()=>{if(!fi.files[0])dz.classList.remove('drag');});
dz.addEventListener('drop',e=>{
  e.preventDefault();dz.classList.remove('drag');
  const f=e.dataTransfer.files[0];
  if(!f)return;
  if(!f.name.toLowerCase().endsWith('.mp4')){alert('MP4 files only.');return;}
  const dt=new DataTransfer();dt.items.add(f);fi.files=dt.files;setFile(f);
});
document.getElementById('upload-form').addEventListener('submit',function(e){
  if(!fi.files[0]){e.preventDefault();alert('Please choose an MP4 file first.');return;}
  sb.disabled=true;document.getElementById('umsg').style.display='block';
});
</script>
</body></html>"""

@app.route('/upload', methods=['GET','POST'])
def upload():
    if request.method == 'GET':
        return UPLOAD_HTML.replace('{nav}', nav_html('upload'))
    f = request.files.get('file')
    if not f or not f.filename.lower().endswith('.mp4'):
        return redirect('/upload')
    vid_id   = str(uuid.uuid4())[:8]
    filename = vid_id + '.mp4'
    path     = os.path.join(STREAM_DIR, filename)
    f.save(path)
    meta = load_meta()
    meta[vid_id] = {
        'filename':    filename,
        'title':       request.form.get('title', 'Untitled'),
        'description': request.form.get('description', ''),
        'tags':        request.form.get('tags', ''),
        'node':        request.form.get('node', 'dc'),
        'uploaded':    datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
        'size':        os.path.getsize(path),
        'views':       0,
    }
    save_meta(meta)
    return redirect(f'/watch/{vid_id}')

if __name__ == '__main__':
    print("ClearCast — starting on http://127.0.0.1:5004")
    app.run(host='0.0.0.0', port=5004, debug=True)
