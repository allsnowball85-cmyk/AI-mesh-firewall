# AI-Powered Mesh Firewall Router
**IST 495 Capstone Project — Ben Cessna | Penn State University | bac6113@psu.edu**

---

## Project Overview

This project simulates an AI-powered enterprise mesh firewall router running entirely inside a VirtualBox Ubuntu Server VM. Three Linux network namespaces represent geographically distributed data centers — Washington DC, Seattle, and San Francisco — connected via a B.A.T.M.A.N. Advanced mesh network. Each node runs its own independently hosted web service, protected by a zero-trust AI security engine with a trained machine learning threat classifier.

---

## Architecture

```
Windows Host (VirtualBox NAT)
        │
        ▼
Ubuntu Server 22.04 VM
        │
   ┌────┴────────────────────────┐
   │     batman-adv Mesh Layer   │
   ├──────────┬──────────────────┤
   │          │                  │
ns-dc      ns-seattle          ns-sf
10.0.0.1   10.0.0.2           10.0.0.3
NexusComm  ClearCast          EduSphere
(port 5006)(port 5004)        (port 5005)
```

**Services running in the main namespace (always on):**
- NodeNet ISP Portal — port 5001
- Admin GUI (NOC) — port 5000
- VaultNet file sharing — port 5002
- SecureMesh National Bank — port 5003

**Services running inside their node namespace (go down with the node):**
- NexusComm messaging — DC node — port 5006
- ClearCast video streaming — Seattle node — port 5004
- EduSphere classroom — SF node — port 5005

---

## Requirements

- VirtualBox 6.1 or later
- Ubuntu Server 22.04 LTS (VM)
- Python 3.10+ with pip
- The following Python packages (installed inside venv):
  - flask, scapy, scikit-learn, joblib, pandas, numpy
- The following system packages (installed via apt):
  - batctl, bridge-utils, iproute2, nftables, net-tools, curl, wget

---

## Setup Instructions

### Step 1 — Create the VM

1. Download Ubuntu Server 22.04 ISO from `ubuntu.com/download/server`
2. In VirtualBox create a new VM:
   - Type: Linux, Version: Ubuntu (64-bit)
   - RAM: 2048 MB minimum
   - Storage: 20 GB
3. Attach the ISO and install Ubuntu Server with default settings
4. Set your username to `benja` (or update all scripts with your username)
5. The password is `123`
### Step 2 — Configure VirtualBox Port Forwarding

Go to **Settings → Network → Adapter 1 → Advanced → Port Forwarding** and add:

| Name    | Protocol | Host Port | Guest Port |
|---------|----------|-----------|------------|
| SSH     | TCP      | 2222      | 22         |
| Admin   | TCP      | 5000      | 5000       |
| Hub     | TCP      | 5001      | 5001       |
| Vault   | TCP      | 5002      | 5002       |
| Bank    | TCP      | 5003      | 5003       |
| Stream  | TCP      | 5004      | 5004       |
| Learn   | TCP      | 5005      | 5005       |
| Chat    | TCP      | 5006      | 5006       |

### Step 3 — SSH into the VM

From PowerShell on Windows:
```bash
ssh -p 2222 benja@127.0.0.1
```

### Step 4 — Install system dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y batctl bridge-utils iproute2 net-tools nftables \
    curl wget nano git python3 python3-pip python3-venv tcpdump iperf3
```

### Step 5 — Create Python virtual environment

```bash
python3 -m venv ~/project-env
source ~/project-env/bin/activate
pip install flask scapy scikit-learn joblib pandas numpy
```

Add activation to .bashrc so it activates on login:
```bash
echo "source ~/project-env/bin/activate" >> ~/.bashrc
```

### Step 6 — Load the batman-adv kernel module

```bash
sudo modprobe batman-adv
echo "batman-adv" | sudo tee -a /etc/modules
```

### Step 7 — Clone this repository

```bash
git clone https://github.com/allsnowball85-cmyk/AI-mesh-firewall.git ~/router-gui
cd ~/router-gui
```

### Step 8 — Make scripts executable

```bash
chmod +x ~/router-gui/start-all.sh
chmod +x ~/router-gui/stop-all.sh
chmod +x ~/router-gui/setup-mesh.sh
chmod +x ~/router-gui/setup-mgmt.sh
```

### Step 9 — Copy setup-mesh.sh to home directory

```bash
cp ~/router-gui/setup-mesh.sh ~/setup-mesh.sh
cp ~/router-gui/setup-mgmt.sh ~/setup-mgmt.sh
chmod +x ~/setup-mesh.sh ~/setup-mgmt.sh
```

### Step 10 — Launch everything

```bash
~/router-gui/start-all.sh
```

This single command:
1. Starts the 3-node batman-adv mesh network
2. Sets up management interfaces between namespaces
3. Launches all 7 web services

---

## Accessing the Services

Once `start-all.sh` completes, open these URLs in your Windows browser:

| Service | URL | Login |
|---------|-----|-------|
| NodeNet ISP Hub | http://127.0.0.1:5001 | No login |
| Admin GUI (NOC) | http://127.0.0.1:5000 | No login |
| VaultNet Files | http://127.0.0.1:5002 | No login |
| SecureMesh Bank | http://127.0.0.1:5003 | admin / admin |
| NexusComm Chat | http://127.0.0.1:5006 | admin / admin |
| ClearCast Video | http://127.0.0.1:5004 | No login |
| EduSphere LMS | http://127.0.0.1:5005 | jdoe / pass |

**Additional demo logins:**
- Bank / Chat / Learn: `jdoe/pass`, `mlee/pass`, `achan/pass`

---

## Stopping Everything

```bash
~/router-gui/stop-all.sh
```

This kills all services and tears down the mesh namespaces cleanly.

---

## Project Structure

```
router-gui/
├── start-all.sh          # Master launcher — starts mesh + all services
├── stop-all.sh           # Master stop script
├── setup-mesh.sh         # batman-adv mesh network setup (3 nodes)
├── setup-mgmt.sh         # Management network + NAT forwarding setup
├── admin.py              # Admin GUI / NOC — port 5000
├── portal.py             # NodeNet ISP Hub — port 5001
├── fileserver.py         # VaultNet file sharing — port 5002
├── bank.py               # SecureMesh National Bank — port 5003
├── streaming.py          # ClearCast video streaming — port 5004
├── classroom.py          # EduSphere LMS — port 5005
├── messaging.py          # NexusComm messaging — port 5006
├── templates/
│   └── admin.html        # Admin GUI frontend
└── ai_security/
    ├── ai_policy.py      # Zero-trust domain classification engine
    ├── ml_classifier.py  # ML domain risk scorer (inference)
    ├── train_model.py    # Random Forest model training script
    ├── domain_risk_model.joblib  # Pre-trained model (94% accuracy)
    ├── apply_ruleset.py  # nftables ruleset applicator
    ├── notify.py         # Admin notification system (email + log)
    ├── request_simulator.py  # CLI domain request simulator
    └── config.example.json   # Email notification config template
```

---

## AI Security System

The zero-trust policy engine (`ai_security/`) works in two layers:

**Layer 1 — Zero-Trust Policy (deterministic)**
Every outbound domain request is evaluated against a strict allowlist of approved business categories:
- Banking internal services
- OS and security updates
- Core infrastructure (DNS, NTP)
- Approved business tools (Office 365, Slack, Zoom, GitHub)

Anything not on the list is **blocked by default** and escalated to the admin.

**Layer 2 — ML Risk Scorer (machine learning)**
A Random Forest classifier trained on character n-gram (2–4) TF-IDF features scores how suspicious a blocked domain name looks — detecting DGA (algorithmically generated) and phishing-style domains. Test accuracy: **94%**. The score prioritises alerts so the admin sees the most dangerous requests first.

To retrain the model from scratch:
```bash
cd ~/router-gui/ai_security
python3 train_model.py
```

To simulate an employee request through the policy engine:
```bash
python3 request_simulator.py facebook.com dc jdoe
python3 request_simulator.py xk29fj3kqz.tk seattle mlee
```

---

## Mesh Network Details

The mesh uses three Linux network namespaces connected by veth pairs running B.A.T.M.A.N. Advanced:

| Node | Namespace | batman-adv Interface | IP |
|------|-----------|---------------------|-----|
| Washington DC | ns-dc | bat-dc | 10.0.0.1 |
| Seattle | ns-seattle | bat-seattle | 10.0.0.2 |
| San Francisco | ns-sf | bat-sf | 10.0.0.3 |

To verify the mesh is running:
```bash
sudo ip netns list
sudo ip netns exec ns-dc batctl -m bat-dc n
sudo ip netns exec ns-dc ping -c 3 10.0.0.2
```

---

## Firewall

Each node runs an nftables zero-trust ruleset (default DROP on all chains). The Admin GUI lets you toggle the firewall and geo-blocking per node. To apply the AI-generated base ruleset to all nodes from the Admin GUI, use the **AI Security → Generate & Apply Zero-Trust Ruleset** button.

---

## Troubleshooting

**Services show offline in portal:**
Make sure `start-all.sh` completed successfully. The node-bound services (5004, 5005, 5006) require the mesh namespaces to be running.

**batman-adv not found:**
```bash
sudo modprobe batman-adv
```

**Permission denied on scripts:**
```bash
chmod +x ~/router-gui/start-all.sh ~/router-gui/stop-all.sh
```

**Port already in use:**
```bash
sudo fuser -k 5000/tcp
```

---

## Technologies Used

| Technology | Purpose |
|------------|---------|
| B.A.T.M.A.N. Advanced | Mesh routing protocol |
| Linux Network Namespaces | Node isolation / simulation |
| nftables | Zero-trust firewall |
| Flask (Python) | All web services |
| scikit-learn | ML domain risk classifier |
| Scapy | Packet capture framework |
| WireGuard | VPN (architecture planned) |
| VirtualBox | VM host environment |

---

## References

- Rose et al. (2020). *Zero Trust Architecture*. NIST SP 800-207. https://doi.org/10.6028/NIST.SP.800-207
- Pedregosa et al. (2011). Scikit-learn: Machine learning in Python. *JMLR, 12*, 2825–2830.
- Yadav et al. (2010). Detecting algorithmically generated malicious domain names. *ACM IMC 2010*.
- B.A.T.M.A.N. Advanced Kernel Documentation: https://www.kernel.org/doc/html/v4.15/networking/batman-adv.html
- nftables Wiki: https://wiki.nftables.org/
- Flask Documentation: https://flask.palletsprojects.com/

---

*IST 495 Capstone — Penn State University — Summer 2025*
