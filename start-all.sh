#!/bin/bash
# SecureMesh Network — Launch All Services
# Node-specific services run inside their namespaces

PROJECT_DIR="$HOME/router-gui"
PYTHON="$HOME/project-env/bin/python"
LOG_DIR="$HOME/router-gui/logs"
mkdir -p "$LOG_DIR"

echo "════════════════════════════════════════════════════"
echo "   SecureMesh Network — Starting All Services"
echo "════════════════════════════════════════════════════"

# ── 1. Mesh network ──
if ip netns list 2>/dev/null | grep -q "ns-dc"; then
    echo "[1/9] Mesh network already running — skipping"
else
    echo "[1/9] Starting mesh network..."
    sudo "$HOME/setup-mesh.sh" > "$LOG_DIR/mesh.log" 2>&1 && echo "      Mesh started"
fi

# ── 2. Management network (veth pairs + NAT) ──
if ip link show veth-mgmt-dc >/dev/null 2>&1; then
    echo "[2/9] Management network already configured — skipping"
else
    echo "[2/9] Setting up management network..."
    sudo "$HOME/setup-mgmt.sh" > "$LOG_DIR/mgmt.log" 2>&1 && echo "      Management network ready"
fi

# Helper: kill old process on port, then launch in main namespace
launch() {
    NAME=$1; SCRIPT=$2; PORT=$3
    if sudo fuser "$PORT"/tcp >/dev/null 2>&1; then
        sudo fuser -k "$PORT"/tcp >/dev/null 2>&1; sleep 1
    fi
    sudo "$PYTHON" "$PROJECT_DIR/$SCRIPT" > "$LOG_DIR/$NAME.log" 2>&1 &
    disown; sleep 1
    if sudo fuser "$PORT"/tcp >/dev/null 2>&1; then
        echo "      $NAME running  →  http://127.0.0.1:$PORT"
    else
        echo "      WARNING: $NAME failed — check $LOG_DIR/$NAME.log"
    fi
}

# Helper: launch service inside a specific namespace
launch_ns() {
    NAME=$1; NS=$2; SCRIPT=$3; PORT=$4; MGMT_IP=$5
    # Kill any existing process in that namespace on that port
    sudo ip netns exec "$NS" fuser -k "$PORT"/tcp >/dev/null 2>&1 || true
    sleep 0.5
    sudo ip netns exec "$NS" "$PYTHON" "$PROJECT_DIR/$SCRIPT" \
        > "$LOG_DIR/$NAME.log" 2>&1 &
    disown; sleep 2
    # Check via management IP
    if nc -z -w1 "$MGMT_IP" "$PORT" >/dev/null 2>&1; then
        echo "      $NAME running on $NS  →  http://127.0.0.1:$PORT"
    else
        echo "      WARNING: $NAME failed — check $LOG_DIR/$NAME.log"
    fi
}

echo "[3/9] Starting SecureMesh Hub..."
launch "portal"    "portal.py"    5001

echo "[4/9] Starting Admin GUI..."
launch "admin"     "admin.py"     5000

echo "[5/9] Starting NodeVault (file sharing)..."
launch "nodevault" "fileserver.py" 5002

echo "[6/9] Starting SecureMesh Bank..."
launch "bank"      "bank.py"      5003

# Node-specific services (run inside their namespaces)
echo "[7/9] Starting MeshChat on DC node (ns-dc)..."
launch_ns "meshchat"   "ns-dc"      "messaging.py"  5006 "10.100.0.2"

echo "[8/9] Starting MeshStream on Seattle node (ns-seattle)..."
launch_ns "meshstream" "ns-seattle" "streaming.py"  5004 "10.100.1.2"

echo "[9/9] Starting MeshLearn on SF node (ns-sf)..."
launch_ns "meshlearn"  "ns-sf"      "classroom.py"  5005 "10.100.2.2"

echo ""
echo "════════════════════════════════════════════════════"
echo "   All services started"
echo "════════════════════════════════════════════════════"
echo "  Hub (start here):    http://127.0.0.1:5001"
echo "  Admin GUI:           http://127.0.0.1:5000"
echo "  NodeVault:           http://127.0.0.1:5002"
echo "  SecureMesh Bank:     http://127.0.0.1:5003"
echo "  MeshChat (DC):       http://127.0.0.1:5006"
echo "  MeshStream (Seattle):http://127.0.0.1:5004"
echo "  MeshLearn (SF):      http://127.0.0.1:5005"
echo ""
echo "  Node-bound services go offline with their node."
echo "  Use Admin GUI to power nodes on/off."
echo "════════════════════════════════════════════════════"
