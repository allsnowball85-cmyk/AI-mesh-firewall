#!/bin/bash
echo "Stopping all SecureMesh services..."

# Main namespace services
for PORT in 5000 5001 5002 5003; do
    if sudo fuser "$PORT"/tcp >/dev/null 2>&1; then
        sudo fuser -k "$PORT"/tcp >/dev/null 2>&1
        echo "  Stopped port $PORT"
    fi
done

# Node-bound services (kill by namespace)
for NS in ns-dc ns-seattle ns-sf; do
    PIDS=$(sudo ip netns pids "$NS" 2>/dev/null)
    if [ -n "$PIDS" ]; then
        echo "$PIDS" | xargs -r sudo kill -9 2>/dev/null
        echo "  Stopped services in $NS"
    fi
done

echo "Tearing down mesh network..."
for NS in ns-dc ns-seattle ns-sf; do
    sudo ip netns delete $NS 2>/dev/null && echo "  Removed $NS"
done

# Clean up management interfaces
for IFACE in veth-mgmt-dc veth-mgmt-sea veth-mgmt-sf; do
    sudo ip link del $IFACE 2>/dev/null && echo "  Removed $IFACE"
done

echo "All services stopped."
