from flask import Flask, request, redirect, session, send_from_directory
import os, json, datetime, uuid

app = Flask(__name__)
app.secret_key = 'edusphere_2025'

WORK_DIR  = os.path.expanduser('~/meshlearn')
SUB_DIR   = os.path.join(WORK_DIR, 'submissions')
os.makedirs(SUB_DIR, exist_ok=True)

USERS = {
    'admin':  {'password':'admin', 'name':'Admin',       'role':'teacher', 'avatar':'👩‍💼'},
    'jdoe':   {'password':'pass',  'name':'Jane Doe',    'role':'teacher', 'avatar':'👩‍🏫'},
    'mlee':   {'password':'pass',  'name':'Michael Lee', 'role':'student', 'avatar':'👨‍💻'},
    'achan':  {'password':'pass',  'name':'Alice Chan',  'role':'student', 'avatar':'👩‍💻'},
}

COURSES = {
    'net-sec': {
        'id':'net-sec',
        'name':'Network Security Fundamentals',
        'code':'NSF-101',
        'color':'#38bdf8',
        'teacher':'jdoe',
        'enrolled':['mlee','achan'],
        'description':'Core concepts of network security, firewalls, and intrusion detection. Covers nftables, zero-trust architecture, and AI-assisted threat detection on the SecureMesh platform.',
        'announcements':[
            {'id':'a1','title':'Welcome to NSF-101','body':'Welcome everyone! This semester we cover zero-trust architecture and AI-assisted network defense. All labs run on our live SecureMesh VM.','author':'jdoe','date':'2025-05-10'},
            {'id':'a2','title':'Lab 1 is posted','body':'Lab 1 — nftables firewall configuration — is now available under Assignments. Due in one week.','author':'jdoe','date':'2025-05-14'},
        ],
        'assignments':[
            {'id':'asg1','title':'Lab 1 — nftables Firewall Setup','due':'2025-05-21','points':100,'description':'Configure a default-deny nftables ruleset on all three mesh nodes. Document each rule and explain the zero-trust rationale. Submit a PDF report.','open':True},
            {'id':'asg2','title':'Lab 2 — AI Policy Engine Analysis','due':'2025-06-01','points':150,'description':'Run 10 domain requests through the AI policy engine using the simulator. Document the ML risk scores, decision outcomes, and evaluate whether each decision was appropriate.','open':True},
            {'id':'asg3','title':'Midterm — Zero-Trust Architecture Paper','due':'2025-06-15','points':200,'description':'Write a 1500-word paper comparing your SecureMesh zero-trust implementation to an enterprise product (Cloudflare Gateway, Palo Alto Prisma). Cite at least 5 sources.','open':False},
        ],
        'materials':[
            {'id':'m1','title':'nftables Official Documentation','type':'link','url':'https://wiki.nftables.org/'},
            {'id':'m2','title':'Zero Trust Architecture — NIST SP 800-207','type':'link','url':'https://doi.org/10.6028/NIST.SP.800-207'},
            {'id':'m3','title':'Course Syllabus','type':'file','url':'#'},
        ],
    },
    'mesh-arch': {
        'id':'mesh-arch',
        'name':'Mesh Systems Architecture',
        'code':'MSA-201',
        'color':'#d97706',
        'teacher':'jdoe',
        'enrolled':['mlee','achan'],
        'description':'Study of distributed mesh networking with B.A.T.M.A.N. Advanced. Covers Linux network namespaces, veth pairs, routing protocols, and node failover.',
        'announcements':[
            {'id':'b1','title':'Module 2 now available','body':'Module 2 — BATMAN-adv advanced routing — is posted. Please complete the reading before Thursday\'s lab.','author':'jdoe','date':'2025-05-17'},
        ],
        'assignments':[
            {'id':'basg1','title':'Assignment 1 — Namespace Topology Diagram','due':'2025-05-28','points':75,'description':'Draw a complete network diagram of your 3-node mesh (DC, Seattle, SF). Show all veth pairs, batman-adv instances, IP assignments, and firewall boundaries.','open':True},
            {'id':'basg2','title':'Assignment 2 — Node Failover Report','due':'2025-06-10','points':125,'description':'Simulate a node failure in your mesh. Document how batman-adv reroutes traffic and measure the failover time. Submit results with screenshots.','open':True},
        ],
        'materials':[
            {'id':'n1','title':'B.A.T.M.A.N. Advanced Kernel Documentation','type':'link','url':'https://www.kernel.org/doc/html/latest/networking/batman-adv.html'},
            {'id':'n2','title':'Linux Network Namespaces Guide','type':'link','url':'https://man7.org/linux/man-pages/man8/ip-netns.8.html'},
        ],
    },
    'ai-security': {
        'id':'ai-security',
        'name':'AI in Cybersecurity',
        'code':'AIS-301',
        'color':'#4ade80',
        'teacher':'jdoe',
        'enrolled':['mlee','achan'],
        'description':'Machine learning applications in network defense. Covers DGA detection, phishing domain classification, Random Forest classifiers, and integration with live firewall systems.',
        'announcements':[
            {'id':'c1','title':'Model training lab this Friday','body':'We\'ll be running the domain risk model training in Friday\'s lab session. Make sure scikit-learn and joblib are installed in your project-env before class.','author':'jdoe','date':'2025-06-01'},
        ],
        'assignments':[
            {'id':'casg1','title':'Lab — Train & Evaluate Domain Risk Model','due':'2025-06-15','points':100,'description':'Run train_model.py on the provided dataset. Report the accuracy, precision, recall, and F1 score. Add 20 new training samples and document how they change the model performance.','open':True},
        ],
        'materials':[
            {'id':'p1','title':'Yadav et al. — Detecting Algorithmically Generated Domains (2010)','type':'link','url':'https://dl.acm.org/doi/10.1145/1879141.1879148'},
            {'id':'p2','title':'scikit-learn Documentation','type':'link','url':'https://scikit-learn.org/stable/'},
        ],
    },
}

SUBMISSIONS = {}  # {asg_id: {username: {file, submitted_at, grade, feedback}}}
SUB_FILE = os.path.join(WORK_DIR, 'submissions.json')

def load_subs():
    if os.path.exists(SUB_FILE):
        try:
            with open(SUB_FILE) as f: return json.load(f)
        except: pass
    return {}

def save_subs(s):
    with open(SUB_FILE, 'w') as f: json.dump(s, f, indent=2)

def user_courses(username):
    u = USERS.get(username, {})
    if u.get('role') == 'teacher':
        return [c for c in COURSES.values() if c['teacher'] == username or username == 'admin']
    return [c for c in COURSES.values() if username in c.get('enrolled', [])]

# ─── CSS ─────────────────────────────────────────────────────────────────────
CSS = """
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',Arial,sans-serif;background:#0f0d08;color:#e2e8f0;min-height:100vh;}
a{text-decoration:none;color:inherit;}
/* NAV */
.nav{background:#17120a;border-bottom:1px solid #1e2a3a;height:56px;display:flex;
     align-items:center;justify-content:space-between;padding:0 24px;position:sticky;top:0;z-index:100;}
.nav-brand{font-size:16px;font-weight:700;color:#fff;display:flex;align-items:center;gap:8px;}
.nav-right{display:flex;align-items:center;gap:12px;}
.user-chip{display:flex;align-items:center;gap:7px;font-size:13px;color:#94a3b8;}
.role-badge{font-size:10px;padding:2px 8px;border-radius:10px;letter-spacing:1px;text-transform:uppercase;}
.role-teacher{background:rgba(217,119,6,.1);color:#d97706;border:1px solid rgba(217,119,6,.3);}
.role-student{background:rgba(56,189,248,.1);color:#38bdf8;border:1px solid rgba(56,189,248,.3);}
.btn-out{background:transparent;border:1px solid #1e2a3a;color:#64748b;padding:5px 13px;
         border-radius:6px;font-size:12px;cursor:pointer;text-decoration:none;transition:all .2s;}
.btn-out:hover{border-color:#f87171;color:#f87171;}
/* LOGIN */
.login-wrap{min-height:100vh;display:flex;align-items:center;justify-content:center;
            background:radial-gradient(ellipse at center,#111827 0%,#0d0f14 70%);}
.login-card{width:400px;background:#17120a;border:1px solid #1e2a3a;border-radius:14px;padding:36px;}
.login-logo{text-align:center;margin-bottom:28px;}
.login-logo .ico{font-size:44px;}
.login-logo .nm{font-size:20px;font-weight:700;color:#fff;margin-top:10px;}
.login-logo .sub{font-size:12px;color:#475569;margin-top:4px;letter-spacing:2px;text-transform:uppercase;}
.f{margin-bottom:16px;}
.f label{display:block;font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#334155;margin-bottom:7px;}
.f input,.f select{width:100%;background:#070910;border:1px solid #1e2a3a;color:#e2e8f0;
                   padding:12px 13px;border-radius:7px;font-size:14px;outline:none;transition:border-color .2s;}
.f input:focus,.f select:focus{border-color:#d97706;}
.f select option{background:#17120a;}
.btn-login{width:100%;background:#d97706;color:#0d0f14;border:none;padding:13px;border-radius:7px;
           font-size:14px;font-weight:700;cursor:pointer;margin-top:6px;}
.btn-login:hover{background:#b45309;}
.err{background:rgba(248,113,113,.1);border:1px solid rgba(248,113,113,.3);color:#f87171;
     padding:9px 13px;border-radius:6px;font-size:13px;margin-bottom:16px;}
.demo-hint{font-size:11px;color:#334155;text-align:center;margin-top:14px;line-height:1.8;}
/* DASHBOARD */
.layout{display:grid;grid-template-columns:220px 1fr;min-height:calc(100vh - 56px);}
.sidebar{background:#100d07;border-right:1px solid #1e2a3a;padding:20px 12px;}
.sb-title{font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#2a3a4a;margin-bottom:10px;padding:0 8px;}
.sb-item{display:flex;align-items:center;gap:9px;padding:9px 12px;border-radius:7px;
         font-size:13px;color:#475569;cursor:pointer;transition:all .2s;margin-bottom:2px;text-decoration:none;}
.sb-item:hover,.sb-item.act{background:rgba(217,119,6,.08);color:#d97706;}
.main{padding:28px;}
.page-title{font-size:19px;font-weight:700;color:#fff;margin-bottom:6px;}
.page-sub{font-size:13px;color:#475569;margin-bottom:24px;}
/* COURSE CARDS */
.course-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;}
.course-card{border-radius:10px;overflow:hidden;border:1px solid #1e2a3a;
             transition:transform .2s,box-shadow .2s;cursor:pointer;}
.course-card:hover{transform:translateY(-3px);box-shadow:0 12px 32px rgba(0,0,0,.4);}
.course-header{padding:20px;color:#fff;}
.course-code{font-size:10px;letter-spacing:2px;text-transform:uppercase;opacity:.7;margin-bottom:6px;}
.course-name{font-size:15px;font-weight:700;margin-bottom:4px;}
.course-teacher{font-size:12px;opacity:.7;}
.course-body{background:#0d1117;padding:16px;}
.course-stats{display:flex;gap:16px;font-size:11px;color:#475569;}
.course-stat-val{font-size:18px;font-weight:700;color:#e2e8f0;display:block;}
/* COURSE PAGE */
.course-tabs{display:flex;gap:2px;border-bottom:1px solid #1e2a3a;margin-bottom:24px;}
.ctab{padding:10px 20px;font-size:13px;color:#475569;cursor:pointer;border:none;background:none;
      border-bottom:2px solid transparent;transition:all .2s;}
.ctab:hover{color:#e2e8f0;}
.ctab.act{color:#d97706;border-bottom-color:#d97706;}
.tab-panel{display:none;}
.tab-panel.act{display:block;}
/* ANNOUNCEMENTS */
.announcement{background:#17120a;border:1px solid #1e2a3a;border-radius:9px;padding:18px;margin-bottom:14px;}
.ann-title{font-size:15px;font-weight:600;color:#fff;margin-bottom:6px;}
.ann-meta{font-size:11px;color:#475569;margin-bottom:10px;}
.ann-body{font-size:13px;color:#94a3b8;line-height:1.7;}
/* ASSIGNMENTS */
.asg-card{background:#17120a;border:1px solid #1e2a3a;border-radius:9px;padding:18px;
          margin-bottom:14px;display:flex;justify-content:space-between;align-items:flex-start;}
.asg-left .asg-title{font-size:14px;font-weight:600;color:#fff;margin-bottom:5px;}
.asg-left .asg-meta{font-size:11px;color:#475569;}
.asg-right{text-align:right;flex-shrink:0;margin-left:16px;}
.pts-badge{font-size:13px;font-weight:700;color:#d97706;}
.due-badge{font-size:11px;color:#475569;margin-top:4px;}
.btn-submit{background:rgba(217,119,6,.1);color:#d97706;border:1px solid rgba(217,119,6,.3);
            padding:6px 14px;border-radius:6px;font-size:12px;cursor:pointer;margin-top:8px;text-decoration:none;
            display:inline-block;transition:all .2s;}
.btn-submit:hover{background:#d97706;color:#0d0f14;}
.btn-grade{background:rgba(74,222,128,.1);color:#4ade80;border:1px solid rgba(74,222,128,.3);
           padding:6px 14px;border-radius:6px;font-size:12px;cursor:pointer;margin-top:8px;text-decoration:none;
           display:inline-block;transition:all .2s;}
.btn-grade:hover{background:#4ade80;color:#0d0f14;}
.status-sub{font-size:10px;background:rgba(74,222,128,.1);color:#4ade80;
            border:1px solid rgba(74,222,128,.2);padding:2px 8px;border-radius:10px;margin-top:6px;display:inline-block;}
.status-not{font-size:10px;background:rgba(251,191,36,.1);color:#fbbf24;
            border:1px solid rgba(251,191,36,.2);padding:2px 8px;border-radius:10px;margin-top:6px;display:inline-block;}
/* MATERIALS */
.material-row{display:flex;align-items:center;gap:12px;padding:12px 16px;
              background:#17120a;border:1px solid #1e2a3a;border-radius:8px;margin-bottom:10px;}
.mat-icon{font-size:20px;width:32px;text-align:center;}
.mat-name{font-size:13px;color:#e2e8f0;}
.mat-link{font-size:11px;color:#38bdf8;margin-top:2px;}
/* SUBMISSION / GRADE */
.sub-card{background:#17120a;border:1px solid #1e2a3a;border-radius:9px;padding:16px;margin-bottom:12px;}
.sub-user{font-size:13px;font-weight:600;color:#fff;margin-bottom:4px;}
.sub-meta{font-size:11px;color:#475569;margin-bottom:10px;}
.grade-chip{display:inline-block;background:rgba(74,222,128,.1);color:#4ade80;
            border:1px solid rgba(74,222,128,.2);padding:3px 10px;border-radius:10px;font-size:12px;font-weight:600;}
.grade-form input,.grade-form textarea{width:100%;background:#070910;border:1px solid #1e2a3a;
                                        color:#e2e8f0;padding:8px 10px;border-radius:6px;font-size:12px;outline:none;margin-bottom:8px;}
.grade-form input:focus,.grade-form textarea:focus{border-color:#4ade80;}
.btn-save{background:#d97706;color:#0d0f14;border:none;padding:7px 18px;border-radius:6px;
          font-size:12px;font-weight:700;cursor:pointer;}
/* POST FORM */
.post-form{background:#17120a;border:1px solid #1e2a3a;border-radius:9px;padding:18px;margin-bottom:20px;}
.post-form input,.post-form textarea,.post-form select{width:100%;background:#070910;border:1px solid #1e2a3a;
  color:#e2e8f0;padding:9px 11px;border-radius:6px;font-size:13px;outline:none;margin-bottom:10px;}
.post-form input:focus,.post-form textarea:focus{border-color:#d97706;}
.post-form textarea{resize:vertical;min-height:70px;}
.btn-post{background:#d97706;color:#0d0f14;border:none;padding:9px 22px;border-radius:6px;
          font-size:13px;font-weight:700;cursor:pointer;}
.drop-zone{border:2px dashed #1e2a3a;border-radius:8px;padding:32px;text-align:center;
           cursor:pointer;transition:border-color .2s;position:relative;margin-bottom:12px;}
.drop-zone:hover,.drop-zone.drag{border-color:#d97706;}
.panel{background:#17120a;border:1px solid #1e2a3a;border-radius:9px;padding:20px;margin-bottom:16px;}
.section-lbl{font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#334155;margin-bottom:12px;}
@media(max-width:800px){.layout{grid-template-columns:1fr;}.sidebar{display:none;}}
"""

def nav_html(user):
    u = USERS.get(user, {})
    role_cls = 'role-teacher' if u.get('role') == 'teacher' else 'role-student'
    return f"""<nav class="nav">
  <div class="nav-brand">📚 EduSphere</div>
  <div class="nav-right">
    <span class="user-chip">{u.get('avatar','')} {u.get('name',user)} <span class="role-badge {role_cls}">{u.get('role','')}</span></span>
    <a href="/logout" class="btn-out">Logout</a>
  </div>
</nav>"""

def sidebar_html(active='courses'):
    items = [
        ('/', '📊', 'My Courses', 'courses'),
        ('/announcements', '📢', 'Announcements', 'ann'),
        ('/assignments', '📝', 'Assignments', 'asg'),
        ('http://127.0.0.1:5001', '🏠', 'Network Hub', ''),
    ]
    html = '<div class="sidebar"><div class="sb-title">Navigation</div>'
    for url, icon, label, key in items:
        act = 'act' if key == active else ''
        html += f'<a href="{url}" class="sb-item {act}">{icon} {label}</a>'
    html += '</div>'
    return html

# ─── ROUTES ──────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user' not in session: return redirect('/login')
    u = session['user']
    courses = user_courses(u)
    subs = load_subs()
    cards = ''
    for c in courses:
        n_asg = len(c.get('assignments', []))
        n_ann = len(c.get('announcements', []))
        # count pending subs for teacher
        pending = 0
        for a in c.get('assignments', []):
            for sub in subs.get(a['id'], {}).values():
                if not sub.get('grade'): pending += 1
        cards += f"""
<a href="/course/{c['id']}" class="course-card">
  <div class="course-header" style="background:linear-gradient(135deg,{c['color']}22,{c['color']}11);border-bottom:3px solid {c['color']};">
    <div class="course-code">{c['code']}</div>
    <div class="course-name">{c['name']}</div>
    <div class="course-teacher">Prof. {USERS.get(c['teacher'],{}).get('name',c['teacher'])}</div>
  </div>
  <div class="course-body">
    <div class="course-stats">
      <div><span class="course-stat-val">{n_asg}</span>Assignments</div>
      <div><span class="course-stat-val">{n_ann}</span>Announcements</div>
      {f'<div><span class="course-stat-val" style="color:#fbbf24;">{pending}</span>To Grade</div>' if USERS[u]['role']=='teacher' else ''}
    </div>
  </div>
</a>"""
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>EduSphere</title><style>{CSS}</style></head><body>
{nav_html(u)}<div class="layout">{sidebar_html('courses')}<main class="main">
<div class="page-title">My Courses</div>
<div class="page-sub">{len(courses)} course(s) this semester</div>
<div class="course-grid">{cards}</div>
</main></div></body></html>"""

@app.route('/course/<course_id>')
def course(course_id):
    if 'user' not in session: return redirect('/login')
    u = session['user']
    role = USERS[u]['role']
    c = COURSES.get(course_id)
    if not c: return redirect('/')
    subs = load_subs()

    # ── Announcements tab ──
    ann_html = ''
    if role == 'teacher' and (c['teacher'] == u or u == 'admin'):
        ann_html += f"""<div class="post-form">
          <div class="section-lbl">Post Announcement</div>
          <form method="POST" action="/course/{course_id}/announce">
            <input name="title" placeholder="Title" required>
            <textarea name="body" placeholder="Message..."></textarea>
            <button type="submit" class="btn-post">Post</button>
          </form></div>"""
    for a in reversed(c.get('announcements',[])):
        ann_html += f"""<div class="announcement">
          <div class="ann-title">{a['title']}</div>
          <div class="ann-meta">{USERS.get(a['author'],{}).get('name',a['author'])} · {a['date']}</div>
          <div class="ann-body">{a['body']}</div>
        </div>"""

    # ── Assignments tab ──
    asg_html = ''
    if role == 'teacher' and (c['teacher'] == u or u == 'admin'):
        asg_html += f"""<div class="post-form">
          <div class="section-lbl">Create Assignment</div>
          <form method="POST" action="/course/{course_id}/create-assignment">
            <input name="title" placeholder="Assignment title" required>
            <textarea name="description" placeholder="Instructions..."></textarea>
            <input type="date" name="due" required>
            <input type="number" name="points" placeholder="Points (e.g. 100)" required>
            <button type="submit" class="btn-post">Create</button>
          </form></div>"""
    for a in c.get('assignments',[]):
        a_subs = subs.get(a['id'], {})
        my_sub = a_subs.get(u)
        if role == 'teacher':
            sub_count = len(a_subs)
            graded    = sum(1 for s in a_subs.values() if s.get('grade'))
            action_html = f'<a href="/grade/{course_id}/{a["id"]}" class="btn-grade">Grade Submissions ({sub_count})</a>'
        else:
            if my_sub:
                grade_txt = f' — Grade: {my_sub["grade"]}/{a["points"]}' if my_sub.get('grade') else ''
                action_html = f'<span class="status-sub">✓ Submitted{grade_txt}</span>'
            else:
                action_html = f'<a href="/submit/{course_id}/{a["id"]}" class="btn-submit">Submit</a>'
        open_lbl = '' if a.get('open',True) else '<span style="font-size:10px;color:#f87171;margin-left:6px;">(closed)</span>'
        asg_html += f"""<div class="asg-card">
          <div class="asg-left">
            <div class="asg-title">{a['title']}{open_lbl}</div>
            <div class="asg-meta">{a.get('description','')[:120]}{'...' if len(a.get('description',''))>120 else ''}</div>
            {action_html}
          </div>
          <div class="asg-right">
            <div class="pts-badge">{a['points']} pts</div>
            <div class="due-badge">Due {a['due']}</div>
          </div>
        </div>"""

    # ── Materials tab ──
    mat_html = ''
    for m in c.get('materials',[]):
        icon = '🔗' if m['type']=='link' else '📄'
        mat_html += f"""<div class="material-row">
          <div class="mat-icon">{icon}</div>
          <div><div class="mat-name">{m['title']}</div>
          <a href="{m.get('url','#')}" target="_blank" class="mat-link">{m.get('url','Download')}</a></div>
        </div>"""

    # ── People tab ──
    people_html = f"""<div class="panel">
      <div class="section-lbl">Instructor</div>
      <div style="font-size:13px;color:#e2e8f0;">{USERS.get(c['teacher'],{}).get('avatar','')} {USERS.get(c['teacher'],{}).get('name',c['teacher'])}</div>
    </div>
    <div class="panel"><div class="section-lbl">Students ({len(c.get('enrolled',[]))})</div>"""
    for s in c.get('enrolled',[]):
        su = USERS.get(s,{})
        people_html += f'<div style="font-size:13px;color:#94a3b8;margin-bottom:8px;">{su.get("avatar","")} {su.get("name",s)}</div>'
    people_html += '</div>'

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>{c['name']} — EduSphere</title><style>{CSS}</style></head><body>
{nav_html(u)}<div class="layout">{sidebar_html()}
<main class="main">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
    <span style="width:12px;height:12px;border-radius:50%;background:{c['color']};display:inline-block;"></span>
    <div class="page-title" style="margin:0;">{c['name']}</div>
  </div>
  <div class="page-sub">{c['code']} · {c['description'][:100]}...</div>
  <div class="course-tabs">
    <button class="ctab act" onclick="showTab('ann',this)">📢 Announcements</button>
    <button class="ctab" onclick="showTab('asg',this)">📝 Assignments</button>
    <button class="ctab" onclick="showTab('mat',this)">📁 Materials</button>
    <button class="ctab" onclick="showTab('ppl',this)">👥 People</button>
  </div>
  <div id="tab-ann" class="tab-panel act">{ann_html}</div>
  <div id="tab-asg" class="tab-panel">{asg_html}</div>
  <div id="tab-mat" class="tab-panel">{mat_html}</div>
  <div id="tab-ppl" class="tab-panel">{people_html}</div>
</main></div>
<script>
function showTab(name, el) {{
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('act'));
  document.querySelectorAll('.ctab').forEach(b => b.classList.remove('act'));
  document.getElementById('tab-'+name).classList.add('act');
  el.classList.add('act');
}}
// Open tab from URL hash
if (location.hash) {{
  const map = {{'#assignments':'asg','#materials':'mat','#people':'ppl'}};
  if(map[location.hash]) showTab(map[location.hash], document.querySelectorAll('.ctab')[['#assignments','#materials','#people'].indexOf(location.hash)+1]);
}}
</script>
</body></html>"""

@app.route('/submit/<course_id>/<asg_id>', methods=['GET','POST'])
def submit(course_id, asg_id):
    if 'user' not in session: return redirect('/login')
    u = session['user']
    c = COURSES.get(course_id)
    asg = next((a for a in c.get('assignments',[]) if a['id']==asg_id), None)
    if not asg: return redirect(f'/course/{course_id}')

    if request.method == 'POST':
        f   = request.files.get('file')
        txt = request.form.get('text','').strip()
        subs = load_subs()
        if asg_id not in subs: subs[asg_id] = {}
        entry = {'submitted_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), 'grade': None, 'feedback': ''}
        if f and f.filename:
            fname = f"{u}_{asg_id}_{f.filename}"
            f.save(os.path.join(SUB_DIR, fname))
            entry['file'] = fname
        if txt: entry['text'] = txt
        subs[asg_id][u] = entry
        save_subs(subs)
        return redirect(f'/course/{course_id}')

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>Submit — EduSphere</title><style>{CSS}</style></head><body>
{nav_html(u)}<div class="layout">{sidebar_html()}
<main class="main">
  <div class="page-title">Submit: {asg['title']}</div>
  <div class="page-sub">Due {asg['due']} · {asg['points']} points</div>
  <div class="panel" style="max-width:600px;">
    <div class="section-lbl">Assignment Instructions</div>
    <p style="font-size:13px;color:#94a3b8;line-height:1.7;margin-bottom:20px;">{asg['description']}</p>
    <form method="POST" enctype="multipart/form-data">
      <div class="section-lbl">Your Submission</div>
      <div class="drop-zone" id="dz">
        <div style="font-size:28px;margin-bottom:8px;">📎</div>
        <div style="font-size:13px;color:#94a3b8;" id="dz-txt">Attach a file (optional)</div>
        <input type="file" name="file" id="fi" style="position:absolute;opacity:0;inset:0;cursor:pointer;">
      </div>
      <div class="f"><label>Or type your response</label>
        <textarea name="text" style="width:100%;background:#070910;border:1px solid #1e2a3a;color:#e2e8f0;
        padding:10px;border-radius:7px;font-size:13px;outline:none;resize:vertical;min-height:100px;"
        placeholder="Type your answer here..."></textarea></div>
      <button type="submit" class="btn-post">Submit Assignment</button>
      <a href="/course/{course_id}" style="margin-left:14px;font-size:12px;color:#475569;">Cancel</a>
    </form>
  </div>
</main></div>
<script>
document.getElementById('fi').addEventListener('change', function(){{
  if(this.files[0]) document.getElementById('dz-txt').textContent = this.files[0].name;
}});
</script></body></html>"""

@app.route('/grade/<course_id>/<asg_id>', methods=['GET','POST'])
def grade(course_id, asg_id):
    if 'user' not in session: return redirect('/login')
    u = session['user']
    if USERS[u]['role'] != 'teacher': return redirect('/')
    c = COURSES.get(course_id)
    asg = next((a for a in c.get('assignments',[]) if a['id']==asg_id), None)
    subs = load_subs()

    if request.method == 'POST':
        student  = request.form.get('student')
        g_val    = request.form.get('grade')
        feedback = request.form.get('feedback','')
        if student and g_val:
            if asg_id not in subs: subs[asg_id] = {}
            if student not in subs[asg_id]: subs[asg_id][student] = {}
            subs[asg_id][student]['grade']    = g_val
            subs[asg_id][student]['feedback'] = feedback
            save_subs(subs)
        return redirect(f'/grade/{course_id}/{asg_id}')

    a_subs = subs.get(asg_id, {})
    sub_cards = ''
    for student, sub in a_subs.items():
        su = USERS.get(student, {})
        grade_val = sub.get('grade')
        grade_html = f'<span class="grade-chip">{grade_val}/{asg["points"]}</span>' if grade_val else '<span style="color:#fbbf24;font-size:11px;">Not graded</span>'
        text_sub = sub.get('text','')
        file_sub = sub.get('file','')
        sub_cards += f"""<div class="sub-card">
          <div class="sub-user">{su.get('avatar','')} {su.get('name',student)}</div>
          <div class="sub-meta">Submitted {sub.get('submitted_at','')} · {grade_html}</div>
          {f'<div style="font-size:12px;color:#94a3b8;background:#070910;padding:10px;border-radius:6px;margin-bottom:10px;">{text_sub}</div>' if text_sub else ''}
          {f'<div style="font-size:11px;color:#38bdf8;margin-bottom:10px;">📎 {file_sub}</div>' if file_sub else ''}
          {f'<div style="font-size:12px;color:#4ade80;margin-bottom:10px;">Feedback: {sub.get("feedback","")}</div>' if sub.get("feedback") else ''}
          <form method="POST" class="grade-form" style="display:flex;gap:8px;align-items:flex-start;">
            <input type="hidden" name="student" value="{student}">
            <input type="number" name="grade" placeholder="Grade" min="0" max="{asg['points']}" value="{grade_val or ''}" style="width:80px;">
            <textarea name="feedback" placeholder="Feedback (optional)" rows="2">{sub.get('feedback','')}</textarea>
            <button type="submit" class="btn-save">Save</button>
          </form>
        </div>"""

    if not sub_cards:
        sub_cards = '<div style="color:#334155;font-size:13px;padding:20px;">No submissions yet.</div>'

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>Grade — EduSphere</title><style>{CSS}</style></head><body>
{nav_html(u)}<div class="layout">{sidebar_html()}
<main class="main">
  <div class="page-title">Grade: {asg['title']}</div>
  <div class="page-sub">{c['name']} · {len(a_subs)} submission(s) · {asg['points']} points</div>
  {sub_cards}
</main></div></body></html>"""

@app.route('/course/<course_id>/announce', methods=['POST'])
def post_announcement(course_id):
    if 'user' not in session: return redirect('/login')
    u = session['user']
    c = COURSES.get(course_id)
    if not c: return redirect('/')
    COURSES[course_id]['announcements'].insert(0, {
        'id': str(uuid.uuid4())[:6],
        'title': request.form.get('title',''),
        'body': request.form.get('body',''),
        'author': u,
        'date': datetime.datetime.now().strftime('%Y-%m-%d'),
    })
    return redirect(f'/course/{course_id}')

@app.route('/course/<course_id>/create-assignment', methods=['POST'])
def create_assignment(course_id):
    if 'user' not in session: return redirect('/login')
    c = COURSES.get(course_id)
    if not c: return redirect('/')
    COURSES[course_id]['assignments'].insert(0, {
        'id': str(uuid.uuid4())[:6],
        'title': request.form.get('title','Untitled'),
        'description': request.form.get('description',''),
        'due': request.form.get('due',''),
        'points': int(request.form.get('points',100)),
        'open': True,
    })
    return redirect(f'/course/{course_id}')

@app.route('/assignments')
def all_assignments():
    if 'user' not in session: return redirect('/login')
    u = session['user']
    subs = load_subs()
    courses = user_courses(u)
    cards = ''
    for c in courses:
        for a in c.get('assignments',[]):
            my_sub = subs.get(a['id'],{}).get(u)
            status = '<span class="status-sub">✓ Submitted</span>' if my_sub else '<span class="status-not">Pending</span>'
            cards += f"""<div class="asg-card">
              <div class="asg-left">
                <div class="asg-title">{a['title']}</div>
                <div class="asg-meta" style="margin:4px 0;">{c['name']}</div>
                {status if USERS[u]['role']=='student' else ''}
              </div>
              <div class="asg-right">
                <div class="pts-badge">{a['points']} pts</div>
                <div class="due-badge">Due {a['due']}</div>
                <a href="/{'submit' if USERS[u]['role']=='student' else 'grade'}/{c['id']}/{a['id']}" class="{'btn-submit' if USERS[u]['role']=='student' else 'btn-grade'}">
                  {'Submit' if USERS[u]['role']=='student' else 'Grade'}
                </a>
              </div>
            </div>"""
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>Assignments — EduSphere</title><style>{CSS}</style></head><body>
{nav_html(u)}<div class="layout">{sidebar_html('asg')}<main class="main">
<div class="page-title">All Assignments</div><div class="page-sub">Across all enrolled courses</div>
{cards or '<div style="color:#334155;font-size:13px;">No assignments found.</div>'}
</main></div></body></html>"""

@app.route('/announcements')
def all_announcements():
    if 'user' not in session: return redirect('/login')
    u = session['user']
    courses = user_courses(u)
    all_anns = []
    for c in courses:
        for a in c.get('announcements',[]):
            all_anns.append({**a, 'course_name': c['name'], 'course_id': c['id'], 'course_color': c['color']})
    all_anns.sort(key=lambda x: x['date'], reverse=True)
    cards = ''.join(f"""<div class="announcement" style="border-left:3px solid {a['course_color']};">
      <div style="font-size:10px;color:{a['course_color']};letter-spacing:1px;text-transform:uppercase;margin-bottom:6px;">{a['course_name']}</div>
      <div class="ann-title">{a['title']}</div>
      <div class="ann-meta">{USERS.get(a['author'],{}).get('name',a['author'])} · {a['date']}</div>
      <div class="ann-body">{a['body']}</div>
    </div>""" for a in all_anns)
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>Announcements — EduSphere</title><style>{CSS}</style></head><body>
{nav_html(u)}<div class="layout">{sidebar_html('ann')}<main class="main">
<div class="page-title">All Announcements</div><div class="page-sub">{len(all_anns)} total</div>
{cards or '<div style="color:#334155;">No announcements yet.</div>'}
</main></div></body></html>"""

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        u = request.form.get('username','')
        p = request.form.get('password','')
        if u in USERS and USERS[u]['password'] == p:
            session['user'] = u
            return redirect('/')
        err = '<div class="err">Invalid credentials.</div>'
    else:
        err = ''
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>EduSphere — Sign In</title><style>{CSS}</style></head><body>
<div class="login-wrap"><div class="login-card">
  <div class="login-logo"><div class="ico">📚</div>
    <div class="nm">EduSphere</div>
    <div class="sub">Professional Learning Platform · SF Data Center</div></div>
  {err}
  <form method="POST">
    <div class="f"><label>Username</label><input name="username" placeholder="e.g. jdoe" required autocomplete="off"></div>
    <div class="f"><label>Password</label><input type="password" name="password" placeholder="Password" required></div>
    <button type="submit" class="btn-login">Sign In</button>
  </form>
  <div style='font-size:10px;color:#3a2f1a;text-align:center;margin-top:8px;'>Powered by NodeNet ISP · San Francisco Data Center</div>
  <div class="demo-hint">Teachers: <b>admin/admin</b> · <b>jdoe/pass</b><br>Students: <b>mlee/pass</b> · <b>achan/pass</b></div>
</div></div></body></html>"""

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    print("EduSphere — starting on http://127.0.0.1:5005")
    app.run(host='0.0.0.0', port=5005, debug=True)
