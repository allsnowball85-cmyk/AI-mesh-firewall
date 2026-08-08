"""
AI Policy Engine -- Employee Request Simulator
=================================================
Since the mesh namespaces don't have live internet access, this script
simulates an employee on a given node requesting a website. It feeds
the request through the AI Policy Engine exactly as a real DNS-monitor
would, triggering the same allow/block decision, logging, and admin
notification.

Usage:
  python3 request_simulator.py <domain> <node> <employee>

Examples:
  python3 request_simulator.py login.microsoftonline.com dc jdoe
  python3 request_simulator.py facebook.com seattle mlee
  python3 request_simulator.py youtube.com sf achan
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ai_policy as ap
import notify


def simulate(domain, node, employee):
    result = ap.classify_domain(domain, node=node, employee=employee)

    print(f"\nRequest: {employee}@{node} -> {domain}")
    print(f"Decision: {result['decision']}")
    print(f"Reason:   {result['reason']}")

    if result["decision"] == "BLOCK":
        alerts = ap.load_alerts()
        alert = next(a for a in alerts if a["domain"] == domain and a["status"] == "pending")
        ok, msg = notify.notify_blocked_request(alert)
        print(f"\nAdmin notified: {msg}")
        print("-> Domain will remain blocked until approved in Admin GUI > AI Security")
    else:
        print("-> Traffic allowed (domain is on the zero-trust allowlist)")

    return result


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    simulate(sys.argv[1], sys.argv[2], sys.argv[3])
