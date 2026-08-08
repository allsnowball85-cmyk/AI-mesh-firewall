"""
AI Policy Engine -- Apply Base Zero-Trust Ruleset
====================================================
Generates and applies the zero-trust nftables ruleset to one or all
mesh nodes (namespaces). Called from the Admin GUI "Generate & Apply
Base Ruleset" button, or directly via CLI.

Usage:
  python3 apply_ruleset.py <node|all>

Examples:
  python3 apply_ruleset.py dc
  python3 apply_ruleset.py all
"""

import sys
import os
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ai_policy as ap

NS_MAP = {"dc": "ns-dc", "seattle": "ns-seattle", "sf": "ns-sf"}


def run(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except Exception as e:
        return "", str(e), 1


def apply_to_node(node_key):
    ns = NS_MAP.get(node_key)
    if not ns:
        return False, f"Unknown node: {node_key}"

    ruleset = ap.generate_base_ruleset(node_key)

    # Write ruleset to a temp file then load it via nft -f
    tmp_path = f"/tmp/ai_ruleset_{node_key}.nft"
    with open(tmp_path, "w") as f:
        f.write(ruleset)

    # Flush existing rules first, then load the new base ruleset
    run(f"sudo ip netns exec {ns} nft flush ruleset")
    out, err, code = run(f"sudo ip netns exec {ns} nft -f {tmp_path}")

    if code != 0:
        return False, f"nft load failed: {err or out}"

    # Re-apply any previously-approved IP allowances
    allowlist = ap.load_allowlist()
    reapplied = 0
    for category, info in allowlist.items():
        if info.get("risk") == "admin_approved":
            for domain in info["domains"]:
                # Best-effort DNS resolution for re-applying IP allow rules
                ip_out, _, ip_code = run(f"getent hosts {domain} | awk '{{print $1}}' | head -1")
                if ip_code == 0 and ip_out:
                    for cmd in ap.add_allowed_ip(node_key, ip_out, comment=domain):
                        run(f"sudo ip netns exec {ns} {cmd}")
                    reapplied += 1

    return True, f"Base ruleset applied to {node_key} ({ns}). Re-applied {reapplied} approved domain(s)."


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    target = sys.argv[1].lower()
    targets = list(NS_MAP.keys()) if target == "all" else [target]

    for node_key in targets:
        ok, msg = apply_to_node(node_key)
        status = "OK" if ok else "FAILED"
        print(f"[{status}] {node_key}: {msg}")


if __name__ == "__main__":
    main()
