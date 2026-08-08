from flask import Flask, render_template_string, request, redirect, session
import datetime

app = Flask(__name__)
app.secret_key = 'securemesh_national_bank_2025'

BRANCHES = {
    'dc': {
        'name': 'Washington DC', 'full': 'Washington DC Headquarters',
        'ip': '10.0.0.1', 'code': 'SMNB-DC',
        'address': '1776 Constitution Ave NW, Washington, DC 20006',
        'routing': '021000089',
    },
    'seattle': {
        'name': 'Seattle', 'full': 'Seattle Pacific Regional Branch',
        'ip': '10.0.0.2', 'code': 'SMNB-SEA',
        'address': '1201 3rd Ave, Seattle, WA 98101',
        'routing': '125000024',
    },
    'sf': {
        'name': 'San Francisco', 'full': 'San Francisco Bay Branch',
        'ip': '10.0.0.3', 'code': 'SMNB-SFO',
        'address': '101 Market St, San Francisco, CA 94105',
        'routing': '121000248',
    },
}

USERS = {
    'admin': {'password': 'admin', 'name': 'Network Admin', 'title': 'System Administrator', 'branch': 'dc',      'clearance': 'LEVEL-5'},
    'jdoe':  {'password': 'pass',  'name': 'Jane Doe',       'title': 'VP Operations',         'branch': 'dc',      'clearance': 'LEVEL-3'},
    'mlee':  {'password': 'pass',  'name': 'Michael Lee',    'title': 'Branch Manager',        'branch': 'seattle', 'clearance': 'LEVEL-3'},
    'achan': {'password': 'pass',  'name': 'Alice Chan',     'title': 'Senior Analyst',         'branch': 'sf',      'clearance': 'LEVEL-2'},
}

ACCOUNTS = {
    'dc': [
        {'id': 'DC-CHK-0042', 'type': 'Corporate Checking',   'balance': 2_450_000.00},
        {'id': 'DC-SAV-0011', 'type': 'Treasury Reserve',     'balance': 15_750_000.00},
        {'id': 'DC-INV-0007', 'type': 'Investment Portfolio', 'balance':  8_320_000.00},
    ],
    'seattle': [
        {'id': 'SEA-CHK-0019', 'type': 'Regional Operations', 'balance': 1_250_000.00},
        {'id': 'SEA-SAV-0003', 'type': 'Technology Fund',     'balance': 3_400_000.00},
    ],
    'sf': [
        {'id': 'SFO-CHK-0031', 'type': 'Pacific Operations',  'balance':   950_000.00},
        {'id': 'SFO-INV-0012', 'type': 'Innovation Fund',     'balance': 5_200_000.00},
        {'id': 'SFO-SAV-0008', 'type': 'Venture Reserve',     'balance': 2_100_000.00},
    ],
}

TRANSACTIONS = {
    'dc': [
        {'date':'2025-06-05','type':'Wire Transfer','desc':'Mesh Transfer to Seattle Node',     'amount':-250_000,'status':'Completed'},
        {'date':'2025-06-04','type':'Deposit',       'desc':'Network Revenue Allocation',       'amount': 500_000,'status':'Completed'},
        {'date':'2025-06-03','type':'Wire Transfer', 'desc':'Mesh Transfer to SF Node',          'amount':-150_000,'status':'Completed'},
        {'date':'2025-06-02','type':'Deposit',       'desc':'Federal Reserve Settlement',       'amount':1_000_000,'status':'Completed'},
        {'date':'2025-06-01','type':'Fee',           'desc':'Network Infrastructure Fee',       'amount': -45_000,'status':'Completed'},
        {'date':'2025-05-31','type':'Wire Transfer', 'desc':'Inter-branch Reconciliation',      'amount': 320_000,'status':'Completed'},
        {'date':'2025-05-30','type':'Deposit',       'desc':'Investment Returns',               'amount': 215_000,'status':'Completed'},
    ],
    'seattle': [
        {'date':'2025-06-05','type':'Wire Transfer','desc':'Received from DC Node',             'amount': 250_000,'status':'Completed'},
        {'date':'2025-06-04','type':'Wire Transfer','desc':'Mesh Transfer to SF Node',           'amount': -75_000,'status':'Completed'},
        {'date':'2025-06-03','type':'Deposit',      'desc':'Regional Operations Revenue',       'amount': 320_000,'status':'Completed'},
        {'date':'2025-06-02','type':'Fee',          'desc':'Technology Infrastructure',         'amount': -28_000,'status':'Completed'},
        {'date':'2025-06-01','type':'Deposit',      'desc':'Client Deposits',                   'amount': 180_000,'status':'Completed'},
        {'date':'2025-05-31','type':'Wire Transfer','desc':'Mesh Transfer to DC Node',           'amount': -50_000,'status':'Completed'},
    ],
    'sf': [
        {'date':'2025-06-05','type':'Wire Transfer','desc':'Received from DC Node',             'amount': 150_000,'status':'Completed'},
        {'date':'2025-06-04','type':'Deposit',      'desc':'Pacific Coast Revenue',             'amount': 425_000,'status':'Completed'},
        {'date':'2025-06-03','type':'Wire Transfer','desc':'Mesh Transfer to DC Node',           'amount':-100_000,'status':'Completed'},
        {'date':'2025-06-02','type':'Fee',          'desc':'Security and Compliance',           'amount': -32_000,'status':'Completed'},
        {'date':'2025-06-01','type':'Deposit',      'desc':'Investment Returns',                'amount': 890_000,'status':'Completed'},
        {'date':'2025-05-31','type':'Wire Transfer','desc':'Received from Seattle Node',        'amount':  75_000,'status':'Completed'},
    ],
}

SECURITY_LOGS = [
    {'time':'2025-06-05 18:42:11','node':'dc',      'event':'Successful login',        'actor':'admin',     'detail':'Authenticated from MeshNet VPN tunnel', 'level':'info'},
    {'time':'2025-06-05 18:40:02','node':'seattle', 'event':'Wire transfer authorized','actor':'mlee',      'detail':'Mesh transfer to SF Node, $75,000', 'level':'info'},
    {'time':'2025-06-05 17:55:30','node':'sf',      'event':'Failed login attempt',    'actor':'unknown',   'detail':'Invalid credentials, 3rd attempt, IP flagged', 'level':'warn'},
    {'time':'2025-06-05 17:50:00','node':'dc',      'event':'Geo-block triggered',     'actor':'AI Firewall','detail':'Inbound connection from high-risk range dropped (193.0.0.0/8)', 'level':'danger'},
    {'time':'2025-06-05 16:20:44','node':'dc',      'event':'AI threat score elevated','actor':'AI Engine', 'detail':'Anomalous traffic pattern flagged, auto-block rule queued', 'level':'warn'},
    {'time':'2025-06-05 14:05:19','node':'sf',      'event':'Successful login',        'actor':'achan',     'detail':'Authenticated from MeshNet VPN tunnel', 'level':'info'},
    {'time':'2025-06-04 22:10:08','node':'seattle', 'event':'Crowd-request alert',     'actor':'AI Engine', 'detail':'12 users requested blocked domain, IT notified', 'level':'warn'},
    {'time':'2025-06-04 09:30:00','node':'dc',      'event':'Firewall rules updated',  'actor':'admin',     'detail':'Geo-blocking ranges refreshed on all 3 nodes', 'level':'info'},
]

def fmt_money(v):
    return "${:,.2f}".format(abs(v))

# ── LOGIN PAGE ─────────────────────────────────────────────────────────────────

LOGIN_HTML = """
<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><title>SecureMesh National Bank - Login</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',Arial,sans-serif;background:#060e1a;color:#e2e8f0;min-height:100vh;
     display:flex;align-items:center;justify-content:center;
     background-image:radial-gradient(ellipse at center,#0d2040 0%,#060e1a 70%);}
.wrap{width:420px;}
.hd{text-align:center;margin-bottom:36px;}
.hd .ico{font-size:52px;margin-bottom:14px;}
.hd .nm{font-size:22px;font-weight:700;color:#c9a227;letter-spacing:.5px;}
.hd .sub{font-size:12px;color:#475569;margin-top:6px;letter-spacing:3px;text-transform:uppercase;}
.card{background:#0d1b2a;border:1px solid rgba(201,162,39,.25);border-radius:14px;
      padding:38px;box-shadow:0 24px 64px rgba(0,0,0,.6);}
.sec-badge{display:flex;align-items:center;gap:8px;background:rgba(201,162,39,.07);
           border:1px solid rgba(201,162,39,.2);border-radius:6px;padding:9px 14px;
           font-size:11px;color:#c9a227;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:28px;}
.err{background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.3);color:#f87171;
     padding:10px 14px;border-radius:6px;font-size:13px;margin-bottom:18px;}
.f{margin-bottom:18px;}
.f label{display:block;font-size:10px;color:#475569;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px;}
.f input,.f select{width:100%;background:#070f1c;border:1px solid #1e3a5c;color:#e2e8f0;
                   padding:13px 14px;border-radius:7px;font-size:14px;outline:none;transition:border-color .2s;}
.f input:focus,.f select:focus{border-color:#c9a227;}
.f input::placeholder{color:#2a3a4a;}
.f select option{background:#0d1b2a;}
.btn{width:100%;background:#c9a227;color:#060e1a;border:none;padding:14px;border-radius:8px;
     font-size:14px;font-weight:700;cursor:pointer;letter-spacing:.5px;transition:background .2s;margin-top:6px;}
.btn:hover{background:#e0b83a;}
.foot{text-align:center;margin-top:22px;font-size:11px;color:#2a3a4a;line-height:1.8;}
.demo{font-size:11px;color:#334155;margin-top:16px;line-height:1.8;text-align:center;}
.demo b{color:#475569;}
</style></head><body>
<div class="wrap">
  <div class="hd"><div class="ico">BANK</div>
    <div class="nm">SecureMesh National Bank</div>
    <div class="sub">Private Mesh Banking Network</div></div>
  <div class="card">
    <div class="sec-badge">LOCK -- Encrypted Secure Session Required</div>
    {error_block}
    <form method="POST" action="/login">
      <div class="f"><label>Employee ID</label>
        <input type="text" name="username" placeholder="Enter employee ID" autocomplete="off" required></div>
      <div class="f"><label>Password</label>
        <input type="password" name="password" placeholder="Enter secure password" required></div>
      <div class="f"><label>Branch / Node</label>
        <select name="branch">
          <option value="dc">Washington DC - Node 10.0.0.1</option>
          <option value="seattle">Seattle - Node 10.0.0.2</option>
          <option value="sf">San Francisco - Node 10.0.0.3</option>
        </select></div>
      <button type="submit" class="btn">Secure Login</button>
    </form>
    <div class="demo">Demo logins: <b>admin/admin</b> | <b>jdoe/pass</b> | <b>mlee/pass</b> | <b>achan/pass</b></div>
    </div>
  <div class="foot">SecureMesh National Bank - Private Mesh Network<br>
    All connections encrypted via MeshNet VPN - AES-256</div>
</div></body></html>
"""

# ── SHARED SHELL ─────────────────────────────────────────────────────────────

SHELL_CSS = """
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',Arial,sans-serif;background:#060e1a;color:#e2e8f0;min-height:100vh;}
.nav{background:#0a1520;border-bottom:1px solid rgba(201,162,39,.2);height:58px;
     display:flex;align-items:center;justify-content:space-between;padding:0 28px;
     position:sticky;top:0;z-index:100;}
.nav-brand{display:flex;align-items:center;gap:12px;}
.nav-name{font-size:15px;font-weight:700;color:#c9a227;}
.nav-right{display:flex;align-items:center;gap:18px;}
.nav-user{font-size:13px;color:#64748b;}
.nav-user strong{color:#e2e8f0;}
.clr-badge{font-size:10px;background:rgba(201,162,39,.1);border:1px solid rgba(201,162,39,.3);
           color:#c9a227;padding:2px 9px;border-radius:20px;letter-spacing:1px;margin-left:8px;}
.btn-out{background:transparent;border:1px solid #1e3a5c;color:#64748b;padding:6px 14px;
         border-radius:6px;font-size:12px;cursor:pointer;text-decoration:none;transition:all .2s;}
.btn-out:hover{border-color:#f87171;color:#f87171;}
.tabs{background:#080f1a;border-bottom:1px solid #111e2e;padding:0 28px;display:flex;gap:2px;}
.tab{padding:12px 22px;font-size:13px;color:#475569;text-decoration:none;
     border-bottom:2px solid transparent;transition:all .2s;display:flex;align-items:center;gap:8px;}
.tab:hover{color:#e2e8f0;}
.tab.active{color:#c9a227;border-bottom-color:#c9a227;}
.nd{width:7px;height:7px;border-radius:50%;background:#4ade80;display:inline-block;box-shadow:0 0 6px #4ade80;}
.layout{display:grid;grid-template-columns:240px 1fr;min-height:calc(100vh - 100px);}
.sb{background:#070f1a;border-right:1px solid #111e2e;padding:22px 14px;}
.sb-sec{margin-bottom:26px;}
.sb-title{font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#2a3a4a;margin-bottom:10px;padding:0 8px;}
.sb-item{display:flex;align-items:center;gap:10px;padding:9px 12px;border-radius:7px;
         font-size:13px;color:#475569;cursor:pointer;transition:all .2s;margin-bottom:2px;text-decoration:none;}
.sb-item:hover{background:rgba(201,162,39,.07);color:#c9a227;}
.sb-item.act{background:rgba(201,162,39,.1);color:#c9a227;}
.b-card{background:rgba(201,162,39,.05);border:1px solid rgba(201,162,39,.15);
        border-radius:8px;padding:14px;margin-bottom:10px;}
.b-card-nm{font-size:13px;font-weight:600;color:#c9a227;margin-bottom:6px;}
.b-card-dt{font-size:11px;color:#334155;line-height:1.7;font-family:monospace;}
.nd-stat{display:flex;align-items:center;gap:7px;margin-top:10px;font-size:11px;color:#4ade80;}
.net-row{display:flex;justify-content:space-between;align-items:center;padding:6px 8px;font-size:12px;}
.main{padding:28px;}
.main-hd{margin-bottom:22px;}
.main-hd h1{font-size:20px;font-weight:700;color:#fff;}
.main-hd p{font-size:12px;color:#334155;margin-top:4px;font-family:monospace;}
.acc-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px;margin-bottom:26px;}
.acc-card{background:#0d1b2a;border:1px solid #1a2f45;border-radius:10px;padding:20px;
          transition:transform .2s,border-color .2s;}
.acc-card:hover{transform:translateY(-2px);border-color:rgba(201,162,39,.4);}
.acc-type{font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#475569;margin-bottom:12px;}
.acc-id{font-family:monospace;font-size:11px;color:#334155;margin-bottom:10px;}
.acc-bal{font-size:26px;font-weight:700;color:#c9a227;}
.acc-lbl{font-size:11px;color:#2a3a4a;margin-top:3px;}
.g2{display:grid;grid-template-columns:1fr 340px;gap:18px;}
.panel{background:#0d1b2a;border:1px solid #1a2f45;border-radius:10px;overflow:hidden;}
.ph{padding:15px 20px;border-bottom:1px solid #111e2e;display:flex;justify-content:space-between;align-items:center;}
.ph-title{font-size:13px;font-weight:600;color:#fff;}
table{width:100%;border-collapse:collapse;}
th{background:#080f1a;font-size:10px;letter-spacing:1.5px;text-transform:uppercase;
   color:#334155;padding:10px 16px;text-align:left;}
td{padding:12px 16px;font-size:13px;border-bottom:1px solid #0a1220;}
tr:last-child td{border-bottom:none;}
.tx-pos{color:#4ade80;font-weight:600;}
.tx-neg{color:#f87171;font-weight:600;}
.tx-type{font-size:10px;color:#334155;margin-top:2px;}
.badge{font-size:10px;padding:2px 8px;border-radius:20px;
       background:rgba(74,222,128,.1);color:#4ade80;border:1px solid rgba(74,222,128,.2);}
.tf{padding:20px;}
.tf .f{margin-bottom:15px;}
.tf .f label{display:block;font-size:10px;letter-spacing:1.5px;text-transform:uppercase;
             color:#334155;margin-bottom:7px;}
.tf .f input,.tf .f select{width:100%;background:#070f1c;border:1px solid #1a2f45;
                            color:#e2e8f0;padding:10px 12px;border-radius:6px;font-size:13px;outline:none;}
.tf .f input:focus,.tf .f select:focus{border-color:#c9a227;}
.tf .f select option{background:#0d1b2a;}
.btn-tf{width:100%;background:#c9a227;color:#060e1a;border:none;padding:12px;
        border-radius:7px;font-size:13px;font-weight:700;cursor:pointer;transition:background .2s;}
.btn-tf:hover{background:#e0b83a;}
.tf-note{font-size:11px;color:#2a3a4a;margin-top:14px;line-height:1.8;}
.ts{font-size:11px;color:#2a3a4a;font-family:monospace;}
.toast{position:fixed;bottom:20px;right:20px;background:#0d1b2a;border:1px solid #4ade80;
        color:#4ade80;border-radius:8px;padding:11px 18px;font-size:12px;font-family:monospace;
        box-shadow:0 8px 24px rgba(0,0,0,.5);}
.filters{display:flex;gap:10px;margin-bottom:18px;flex-wrap:wrap;align-items:center;}
.lvl{font-size:10px;padding:2px 9px;border-radius:20px;letter-spacing:1px;text-transform:uppercase;font-weight:600;}
.lvl-info{background:rgba(56,189,248,.1);color:#38bdf8;border:1px solid rgba(56,189,248,.25);}
.lvl-warn{background:rgba(251,191,36,.1);color:#fbbf24;border:1px solid rgba(251,191,36,.25);}
.lvl-danger{background:rgba(248,113,113,.1);color:#f87171;border:1px solid rgba(248,113,113,.25);}
.btn-print{background:#1e3a5f;color:#38bdf8;border:1px solid #38bdf8;padding:7px 16px;border-radius:6px;
            font-size:12px;cursor:pointer;text-decoration:none;}
.btn-print:hover{background:#38bdf8;color:#060e1a;}
.btn-print.active{background:rgba(201,162,39,.15);color:#c9a227;border-color:#c9a227;}
.stat-row{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:24px;}
.stat-card{background:#0d1b2a;border:1px solid #1a2f45;border-radius:10px;padding:18px;}
.stat-val{font-size:24px;font-weight:700;color:#c9a227;}
.stat-label{font-size:11px;color:#475569;margin-top:4px;letter-spacing:1px;text-transform:uppercase;}
@media(max-width:900px){.layout{grid-template-columns:1fr;}.g2{grid-template-columns:1fr;}.sb{display:none;}.stat-row{grid-template-columns:1fr 1fr;}}
"""

SHELL_TOP = """
<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><title>SecureMesh Bank - {page_title}</title>
<style>{css}</style></head><body>

<nav class="nav">
  <div class="nav-brand">
    <span class="nav-name">SecureMesh National Bank</span>
  </div>
  <div class="nav-right">
    <span class="nav-user">
      <strong>{user_name}</strong> | {user_title}
      <span class="clr-badge">{user_clearance}</span>
    </span>
    <a href="/logout" class="btn-out">Logout</a>
  </div>
</nav>

<div class="tabs">
{branch_tabs}
</div>

<div class="layout">
  <aside class="sb">
    <div class="sb-sec">
      <div class="sb-title">Active Node</div>
      <div class="b-card">
        <div class="b-card-nm">{branch_name}</div>
        <div class="b-card-dt">
          {branch_address}<br><br>
          Routing: {branch_routing}<br>
          Node IP: {branch_ip}<br>
          Code: {branch_code}
        </div>
        <div class="nd-stat">Node Online - Mesh Active</div>
      </div>
    </div>
    <div class="sb-sec">
      <div class="sb-title">Navigation</div>
      <a href="/dashboard" class="sb-item {nav_dashboard}">Dashboard</a>
      <a href="/accounts" class="sb-item {nav_accounts}">Accounts</a>
      <a href="/transfers" class="sb-item {nav_transfers}">Transfers</a>
      <a href="/statements" class="sb-item {nav_statements}">Statements</a>
      <a href="/security" class="sb-item {nav_security}">Security Logs</a>
      <a href="http://127.0.0.1:5002" class="sb-item" target="_blank">NodeVault Files</a>
    </div>
    <div class="sb-sec">
      <div class="sb-title">Network Nodes</div>
{node_rows}
    </div>
  </aside>

  <main class="main">
"""

SHELL_BOTTOM = """
  </main>
</div>
{toast}
</body></html>
"""

def render_shell(content, page_title, user, branch, active_nav, toast_msg=None):
    binfo = BRANCHES[branch]
    tabs = []
    for bkey, b in BRANCHES.items():
        active = 'active' if bkey == branch else ''
        tabs.append('  <a href="/switch/{0}" class="tab {1}"><span class="nd"></span>{2} <span style="font-family:monospace;font-size:10px;color:#334155;">{3}</span></a>'.format(bkey, active, b['name'], b['ip']))
    branch_tabs = "\n".join(tabs)

    node_rows = []
    for bkey, b in BRANCHES.items():
        color = '#c9a227' if bkey == branch else '#475569'
        node_rows.append('      <div class="net-row" style="color:{0};"><span>{1}</span><span style="font-family:monospace;font-size:10px;">{2}</span></div>'.format(color, b['name'], b['ip']))
    node_rows_str = "\n".join(node_rows)

    navs = {k: '' for k in ['dashboard','accounts','transfers','statements','security']}
    navs[active_nav] = 'act'

    top = SHELL_TOP.format(
        page_title=page_title, css=SHELL_CSS,
        user_name=user['name'], user_title=user['title'], user_clearance=user['clearance'],
        branch_tabs=branch_tabs,
        branch_name=binfo['name'], branch_address=binfo['address'],
        branch_routing=binfo['routing'], branch_ip=binfo['ip'], branch_code=binfo['code'],
        node_rows=node_rows_str,
        nav_dashboard=navs['dashboard'], nav_accounts=navs['accounts'],
        nav_transfers=navs['transfers'], nav_statements=navs['statements'],
        nav_security=navs['security'],
    )
    toast = ''
    if toast_msg:
        toast = '<div class="toast">' + toast_msg + '</div><script>setTimeout(function(){var t=document.querySelector(".toast");if(t)t.remove();},3000);</script>'
    return top + content + SHELL_BOTTOM.format(toast=toast)

# ── DASHBOARD ──────────────────────────────────────────────────────────────────

def build_dashboard(branch, user, toast_msg=None):
    binfo = BRANCHES[branch]
    accounts = ACCOUNTS[branch]
    txs = TRANSACTIONS[branch]

    account_cards = "\n".join(
        '  <div class="acc-card"><div class="acc-type">{0}</div><div class="acc-id">{1}</div>'
        '<div class="acc-bal">{2}</div><div class="acc-lbl">Available Balance</div></div>'.format(
            a['type'], a['id'], fmt_money(a['balance'])
        ) for a in accounts
    )

    tx_rows = []
    for tx in txs:
        cls = 'tx-pos' if tx['amount'] >= 0 else 'tx-neg'
        sign = '+' if tx['amount'] > 0 else '-'
        tx_rows.append(
            '        <tr><td class="ts">{0}</td>'
            '<td><div style="color:#cbd5e1;font-size:13px;">{1}</div>'
            '<div class="tx-type">{2}</div></td>'
            '<td class="{3}">{4}{5}</td>'
            '<td><span class="badge">{6}</span></td></tr>'.format(
                tx['date'], tx['desc'], tx['type'], cls, sign, fmt_money(tx['amount']), tx['status']
            )
        )
    tx_rows_str = "\n".join(tx_rows)

    from_opts = "\n".join('            <option>{0} - {1}</option>'.format(a['id'], a['type']) for a in accounts)
    to_opts = "\n".join(
        '            <option value="{0}">{1} - {2}</option>'.format(bkey, b['name'], b['ip'])
        for bkey, b in BRANCHES.items() if bkey != branch
    )

    content = """
<div class="main-hd">
  <h1>{full_name}</h1>
  <p class="ts">Session active: {now} | Encrypted via MeshNet VPN | {code}</p>
</div>

<div class="acc-grid">
{account_cards}
</div>

<div class="g2">
  <div class="panel">
    <div class="ph">
      <span class="ph-title">Recent Transactions</span>
      <span class="ts">{branch_name} Node | {branch_ip}</span>
    </div>
    <table>
      <thead><tr><th>Date</th><th>Description</th><th>Amount</th><th>Status</th></tr></thead>
      <tbody>
{tx_rows}
      </tbody>
    </table>
  </div>

  <div class="panel">
    <div class="ph"><span class="ph-title">Mesh Node Transfer</span></div>
    <div class="tf">
      <form method="POST" action="/transfer">
        <div class="f"><label>From Account</label>
          <select name="from_account">
{from_account_options}
          </select></div>
        <div class="f"><label>To Branch Node</label>
          <select name="to_branch">
{to_branch_options}
          </select></div>
        <div class="f"><label>Amount (USD)</label>
          <input type="number" name="amount" placeholder="0.00" min="1" step="0.01"></div>
        <div class="f"><label>Transfer Memo</label>
          <input type="text" name="memo" placeholder="Optional reference"></div>
        <button type="submit" class="btn-tf">Authorize Mesh Transfer</button>
      </form>
      <div class="tf-note">
        All transfers are routed securely via the MeshNet VPN backbone.<br>
        Transactions are logged and encrypted end-to-end.
      </div>
    </div>
  </div>
</div>
""".format(
        full_name=binfo['full'], now=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        code=binfo['code'], account_cards=account_cards,
        branch_name=binfo['name'], branch_ip=binfo['ip'],
        tx_rows=tx_rows_str, from_account_options=from_opts, to_branch_options=to_opts,
    )
    return render_shell(content, 'Dashboard', user, branch, 'dashboard', toast_msg)

# ── ACCOUNTS ───────────────────────────────────────────────────────────────────

def build_accounts(branch, user):
    binfo = BRANCHES[branch]
    accounts = ACCOUNTS[branch]
    rows = "\n".join(
        '      <tr><td style="font-family:monospace;">{0}</td><td>{1}</td>'
        '<td style="color:#c9a227;font-weight:600;">{2}</td>'
        '<td class="ts">{3}</td><td><span class="badge">Active</span></td></tr>'.format(
            a['id'], a['type'], fmt_money(a['balance']), binfo['routing']
        ) for a in accounts
    )
    total = sum(a['balance'] for a in accounts)
    network_total = sum(a['balance'] for accs in ACCOUNTS.values() for a in accs)

    content = """
<div class="main-hd">
  <h1>Accounts - {branch_name}</h1>
  <p class="ts">{code} | Full account overview</p>
</div>
<div class="stat-row">
  <div class="stat-card"><div class="stat-val">{num_accounts}</div><div class="stat-label">Accounts at this node</div></div>
  <div class="stat-card"><div class="stat-val">{total_balance}</div><div class="stat-label">Total node balance</div></div>
  <div class="stat-card"><div class="stat-val">{network_total}</div><div class="stat-label">Network-wide balance</div></div>
  <div class="stat-card"><div class="stat-val">3</div><div class="stat-label">Active mesh nodes</div></div>
</div>
<div class="panel">
  <div class="ph"><span class="ph-title">Account Details</span></div>
  <table>
    <thead><tr><th>Account ID</th><th>Type</th><th>Balance</th><th>Routing Number</th><th>Status</th></tr></thead>
    <tbody>
{rows}
    </tbody>
  </table>
</div>
""".format(
        branch_name=binfo['name'], code=binfo['code'],
        num_accounts=len(accounts), total_balance=fmt_money(total),
        network_total=fmt_money(network_total), rows=rows,
    )
    return render_shell(content, 'Accounts', user, branch, 'accounts')

# ── TRANSFERS ──────────────────────────────────────────────────────────────────

def build_transfers(branch, user):
    binfo = BRANCHES[branch]
    accounts = ACCOUNTS[branch]
    wires = [t for t in TRANSACTIONS[branch] if t['type'] == 'Wire Transfer']
    rows = []
    for tx in wires:
        cls = 'tx-pos' if tx['amount'] >= 0 else 'tx-neg'
        sign = '+' if tx['amount'] > 0 else '-'
        rows.append(
            '        <tr><td class="ts">{0}</td><td>{1}</td>'
            '<td class="{2}">{3}{4}</td>'
            '<td><span class="badge">{5}</span></td></tr>'.format(
                tx['date'], tx['desc'], cls, sign, fmt_money(tx['amount']), tx['status']
            )
        )
    if not rows:
        rows.append('        <tr><td colspan="4" class="ts" style="text-align:center;padding:24px;">No wire transfers yet.</td></tr>')
    from_opts = "\n".join('            <option>{0} - {1}</option>'.format(a['id'], a['type']) for a in accounts)
    to_opts = "\n".join(
        '            <option value="{0}">{1} - {2}</option>'.format(bkey, b['name'], b['ip'])
        for bkey, b in BRANCHES.items() if bkey != branch
    )

    content = """
<div class="main-hd">
  <h1>Mesh Transfers - {branch_name}</h1>
  <p class="ts">{code} | Move funds securely between mesh nodes</p>
</div>
<div class="g2">
  <div class="panel">
    <div class="ph"><span class="ph-title">All Wire Transfers - {branch_name} Node</span></div>
    <table>
      <thead><tr><th>Date</th><th>Description</th><th>Amount</th><th>Status</th></tr></thead>
      <tbody>
{rows}
      </tbody>
    </table>
  </div>
  <div class="panel">
    <div class="ph"><span class="ph-title">New Mesh Transfer</span></div>
    <div class="tf">
      <form method="POST" action="/transfer">
        <div class="f"><label>From Account</label>
          <select name="from_account">
{from_opts}
          </select></div>
        <div class="f"><label>To Branch Node</label>
          <select name="to_branch">
{to_opts}
          </select></div>
        <div class="f"><label>Amount (USD)</label>
          <input type="number" name="amount" placeholder="0.00" min="1" step="0.01"></div>
        <div class="f"><label>Transfer Memo</label>
          <input type="text" name="memo" placeholder="Optional reference"></div>
        <button type="submit" class="btn-tf">Authorize Mesh Transfer</button>
      </form>
      <div class="tf-note">
        Transfers route via the MeshNet VPN backbone between Washington DC,
        Seattle, and San Francisco nodes. All transactions are logged
        and visible on both the sending and receiving node's transaction history.
      </div>
    </div>
  </div>
</div>
""".format(
        branch_name=binfo['name'], code=binfo['code'],
        rows="\n".join(rows), from_opts=from_opts, to_opts=to_opts,
    )
    return render_shell(content, 'Transfers', user, branch, 'transfers')

# ── STATEMENTS ─────────────────────────────────────────────────────────────────

def build_statements(branch, user, type_filter=None):
    binfo = BRANCHES[branch]
    txs = TRANSACTIONS[branch]
    if type_filter:
        filtered = [t for t in txs if t['type'] == type_filter]
        filter_label = ' - filtered: ' + type_filter
    else:
        filtered = txs
        filter_label = ''

    rows = []
    for tx in filtered:
        cls = 'tx-pos' if tx['amount'] >= 0 else 'tx-neg'
        sign = '+' if tx['amount'] > 0 else '-'
        rows.append(
            '      <tr><td class="ts">{0}</td><td>{1}</td>'
            '<td class="tx-type">{2}</td>'
            '<td class="{3}">{4}{5}</td>'
            '<td><span class="badge">{6}</span></td></tr>'.format(
                tx['date'], tx['desc'], tx['type'], cls, sign, fmt_money(tx['amount']), tx['status']
            )
        )
    if not rows:
        rows.append('      <tr><td colspan="5" class="ts" style="text-align:center;padding:24px;">No transactions match this filter.</td></tr>')

    total_in  = sum(t['amount'] for t in txs if t['amount'] > 0)
    total_out = sum(t['amount'] for t in txs if t['amount'] < 0)
    net = total_in + total_out
    net_sign = '+' if net >= 0 else '-'

    def cls_for(active):
        return 'btn-print active' if active else 'btn-print'

    content = """
<div class="main-hd">
  <h1>Statements - {branch_name}</h1>
  <p class="ts">{code} | Full transaction history for this node</p>
</div>
<div class="stat-row">
  <div class="stat-card"><div class="stat-val tx-pos">{total_in}</div><div class="stat-label">Total credits</div></div>
  <div class="stat-card"><div class="stat-val tx-neg">{total_out}</div><div class="stat-label">Total debits</div></div>
  <div class="stat-card"><div class="stat-val">{net_sign}{net}</div><div class="stat-label">Net change</div></div>
  <div class="stat-card"><div class="stat-val">{count}</div><div class="stat-label">Transactions</div></div>
</div>
<div class="filters">
  <a href="/statements" class="{c_all}">All Types</a>
  <a href="/statements?type=Deposit" class="{c_dep}">Deposits</a>
  <a href="/statements?type=Wire+Transfer" class="{c_wire}">Wire Transfers</a>
  <a href="/statements?type=Fee" class="{c_fee}">Fees</a>
  <a href="/statements/print" class="btn-print" style="margin-left:auto;" target="_blank">Print Statement</a>
</div>
<div class="panel">
  <div class="ph"><span class="ph-title">Transaction History{filter_label}</span></div>
  <table>
    <thead><tr><th>Date</th><th>Description</th><th>Type</th><th>Amount</th><th>Status</th></tr></thead>
    <tbody>
{rows}
    </tbody>
  </table>
</div>
""".format(
        branch_name=binfo['name'], code=binfo['code'],
        total_in=fmt_money(total_in), total_out=fmt_money(total_out),
        net_sign=net_sign, net=fmt_money(net),
        count=len(txs), rows="\n".join(rows), filter_label=filter_label,
        c_all=cls_for(type_filter is None), c_dep=cls_for(type_filter == 'Deposit'),
        c_wire=cls_for(type_filter == 'Wire Transfer'), c_fee=cls_for(type_filter == 'Fee'),
    )
    return render_shell(content, 'Statements', user, branch, 'statements')

def build_print(branch):
    binfo = BRANCHES[branch]
    rows = []
    for tx in TRANSACTIONS[branch]:
        cls = 'pos' if tx['amount'] >= 0 else 'neg'
        sign = '+' if tx['amount'] > 0 else '-'
        rows.append('<tr><td>{0}</td><td>{1}</td><td>{2}</td><td class="{3}">{4}{5}</td><td>{6}</td></tr>'.format(
            tx['date'], tx['desc'], tx['type'], cls, sign, fmt_money(tx['amount']), tx['status']
        ))
    return """
<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Statement - {branch_name}</title>
<style>
body{{font-family:Arial,sans-serif;background:#fff;color:#111;padding:36px;}}
h1{{font-size:18px;margin-bottom:4px;}}
.meta{{font-size:12px;color:#555;margin-bottom:20px;}}
table{{width:100%;border-collapse:collapse;font-size:12px;}}
th{{background:#1b2a3f;color:#fff;padding:8px 10px;text-align:left;}}
td{{padding:7px 10px;border-bottom:1px solid #ddd;}}
.pos{{color:#15803d;}} .neg{{color:#b91c1c;}}
.btn{{background:#c9a227;color:#fff;border:none;padding:8px 18px;border-radius:6px;cursor:pointer;font-size:13px;margin-bottom:20px;}}
</style></head><body>
<button class="btn" onclick="window.print()">Print</button>
<h1>SecureMesh National Bank - Account Statement</h1>
<div class="meta">{branch_full}<br>{code} | Routing {routing}<br>Generated: {now}</div>
<table><thead><tr><th>Date</th><th>Description</th><th>Type</th><th>Amount</th><th>Status</th></tr></thead>
<tbody>
{rows}
</tbody></table>
</body></html>
""".format(
        branch_name=binfo['name'], branch_full=binfo['full'], code=binfo['code'],
        routing=binfo['routing'], now=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        rows="\n".join(rows)
    )

# ── SECURITY LOGS ──────────────────────────────────────────────────────────────

def build_security(branch, user, node_filter=None):
    logs = SECURITY_LOGS
    if node_filter:
        logs = [l for l in logs if l['node'] == node_filter]
        filter_label = ' - ' + BRANCHES[node_filter]['name'] + ' only'
    else:
        filter_label = ''

    rows = []
    for l in logs:
        rows.append(
            '      <tr><td class="ts">{0}</td><td>{1}</td>'
            '<td>{2}</td><td style="font-family:monospace;">{3}</td>'
            '<td style="color:#64748b;">{4}</td>'
            '<td><span class="lvl lvl-{5}">{5}</span></td></tr>'.format(
                l['time'], BRANCHES[l['node']]['name'], l['event'], l['actor'], l['detail'], l['level']
            )
        )

    def cls_for(active):
        return 'btn-print active' if active else 'btn-print'

    total = len(SECURITY_LOGS)
    danger = len([l for l in SECURITY_LOGS if l['level'] == 'danger'])
    warn = len([l for l in SECURITY_LOGS if l['level'] == 'warn'])
    info = len([l for l in SECURITY_LOGS if l['level'] == 'info'])

    content = """
<div class="main-hd">
  <h1>Security Logs - Mesh-Wide</h1>
  <p class="ts">Live event feed across all 3 nodes | AI Firewall and access monitoring</p>
</div>
<div class="stat-row">
  <div class="stat-card"><div class="stat-val">{total}</div><div class="stat-label">Total events</div></div>
  <div class="stat-card"><div class="stat-val" style="color:#f87171;">{danger}</div><div class="stat-label">High severity</div></div>
  <div class="stat-card"><div class="stat-val" style="color:#fbbf24;">{warn}</div><div class="stat-label">Warnings</div></div>
  <div class="stat-card"><div class="stat-val" style="color:#4ade80;">{info}</div><div class="stat-label">Info events</div></div>
</div>
<div class="filters">
  <a href="/security" class="{f_all}">All Nodes</a>
  <a href="/security?node=dc" class="{f_dc}">Washington DC</a>
  <a href="/security?node=seattle" class="{f_sea}">Seattle</a>
  <a href="/security?node=sf" class="{f_sf}">San Francisco</a>
</div>
<div class="panel">
  <div class="ph"><span class="ph-title">Event Log{filter_label}</span></div>
  <table>
    <thead><tr><th>Timestamp</th><th>Node</th><th>Event</th><th>Actor</th><th>Detail</th><th>Severity</th></tr></thead>
    <tbody>
{rows}
    </tbody>
  </table>
</div>
""".format(
        total=total, danger=danger, warn=warn, info=info,
        f_all=cls_for(node_filter is None), f_dc=cls_for(node_filter == 'dc'),
        f_sea=cls_for(node_filter == 'seattle'), f_sf=cls_for(node_filter == 'sf'),
        filter_label=filter_label, rows="\n".join(rows),
    )
    return render_shell(content, 'Security Logs', user, branch, 'security')

# ── ROUTES ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user' in session:
        return redirect('/dashboard')
    return LOGIN_HTML.replace('{error_block}', '')

@app.route('/login', methods=['POST'])
def login():
    u = request.form.get('username', '')
    p = request.form.get('password', '')
    b = request.form.get('branch', 'dc')
    if u in USERS and USERS[u]['password'] == p:
        session['user']   = u
        session['branch'] = b
        return redirect('/dashboard')
    err = '<div class="err">Invalid credentials. Please try again.</div>'
    return LOGIN_HTML.replace('{error_block}', err)

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')
    u  = USERS[session['user']]
    br = session.get('branch', u['branch'])
    toast = session.pop('toast', None)
    return build_dashboard(br, u, toast)

@app.route('/accounts')
def accounts_page():
    if 'user' not in session:
        return redirect('/')
    u  = USERS[session['user']]
    br = session.get('branch', u['branch'])
    return build_accounts(br, u)

@app.route('/transfers')
def transfers_page():
    if 'user' not in session:
        return redirect('/')
    u  = USERS[session['user']]
    br = session.get('branch', u['branch'])
    return build_transfers(br, u)

@app.route('/statements')
def statements_page():
    if 'user' not in session:
        return redirect('/')
    u  = USERS[session['user']]
    br = session.get('branch', u['branch'])
    type_filter = request.args.get('type')
    return build_statements(br, u, type_filter)

@app.route('/statements/print')
def statements_print():
    if 'user' not in session:
        return redirect('/')
    u  = USERS[session['user']]
    br = session.get('branch', u['branch'])
    return build_print(br)

@app.route('/security')
def security_page():
    if 'user' not in session:
        return redirect('/')
    u  = USERS[session['user']]
    br = session.get('branch', u['branch'])
    node_filter = request.args.get('node')
    return build_security(br, u, node_filter)

@app.route('/switch/<branch>')
def switch_branch(branch):
    if branch in BRANCHES:
        session['branch'] = branch
    ref = request.referrer
    if ref and request.host_url.rstrip('/') in ref:
        path = ref.split(request.host_url.rstrip('/'), 1)[-1]
        if path and path != '/':
            return redirect(path)
    return redirect('/dashboard')

@app.route('/transfer', methods=['POST'])
def transfer():
    if 'user' not in session:
        return redirect('/')
    try:
        amount    = float(request.form.get('amount', 0))
        to_branch = request.form.get('to_branch', 'dc')
        fr_branch = session.get('branch', 'dc')
        memo      = request.form.get('memo', '')
        today     = datetime.datetime.now().strftime('%Y-%m-%d')
        desc_from = 'Mesh Transfer to ' + BRANCHES[to_branch]['name'] + ' Node'
        desc_to   = 'Received from ' + BRANCHES[fr_branch]['name'] + ' Node'
        if memo:
            desc_from += ' (' + memo + ')'
            desc_to   += ' (' + memo + ')'
        if amount > 0:
            TRANSACTIONS[fr_branch].insert(0, {'date':today,'type':'Wire Transfer','desc':desc_from,'amount':-amount,'status':'Completed'})
            TRANSACTIONS[to_branch].insert(0, {'date':today,'type':'Wire Transfer','desc':desc_to,  'amount': amount,'status':'Completed'})
            session['toast'] = 'Transferred ' + fmt_money(amount) + ' to ' + BRANCHES[to_branch]['name']
    except (ValueError, KeyError):
        pass
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    print("SecureMesh National Bank - starting on http://127.0.0.1:5003")
    print("Default login: admin / admin")
    app.run(host='0.0.0.0', port=5003, debug=True)
