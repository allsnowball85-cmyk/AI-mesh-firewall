"""
AI Policy Engine -- Zero-Trust Domain Classification & Base Ruleset Generator
==============================================================================
Core idea: NOTHING is trusted by default. A domain is only allowed if it
falls into a pre-approved business-need category. Everything else is
blocked and escalated to the admin for review.

This module is shared by:
  - dns_watch.py     (live monitoring, when running on real hardware)
  - request_simulator.py (manual testing / demo)
  - admin.py         (Admin GUI integration)
"""

import json
import os
import datetime
import ml_classifier

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
ALLOWLIST_FILE = os.path.join(BASE_DIR, "allowlist.json")
ALERTS_FILE    = os.path.join(BASE_DIR, "alerts.json")
LOG_FILE       = os.path.join(BASE_DIR, "policy_log.json")

# ── DEFAULT ZERO-TRUST ALLOWLIST ─────────────────────────────────────────────
# Only domains matching these categories are trusted out of the box.
# Everything else -> BLOCKED + flagged for admin review.

DEFAULT_ALLOWLIST = {
    "banking_internal": {
        "description": "SecureMesh Bank internal services -- mesh-only",
        "domains": ["securemesh.local", "nodevault.local", "bank.local"],
        "risk": "trusted"
    },
    "os_security_updates": {
        "description": "OS and security patch sources -- required for compliance",
        "domains": [
            "archive.ubuntu.com", "security.ubuntu.com",
            "deb.debian.org", "download.windowsupdate.com",
            "esm.ubuntu.com"
        ],
        "risk": "trusted"
    },
    "core_infrastructure": {
        "description": "DNS, NTP, and certificate validation -- required for network function",
        "domains": [
            "pool.ntp.org", "time.windows.com",
            "ocsp.digicert.com", "ocsp.pki.goog"
        ],
        "risk": "trusted"
    },
    "approved_business_tools": {
        "description": "Pre-approved productivity / business software",
        "domains": [
            "outlook.office365.com", "login.microsoftonline.com",
            "slack.com", "zoom.us", "github.com"
        ],
        "risk": "trusted"
    }
}

# ── HIGH-RISK CATEGORY SIGNALS ──────────────────────────────────────────────
# Used to enrich alerts with WHY something looks risky (not required for
# the block decision itself -- under zero-trust, anything not allowlisted
# is blocked regardless -- but this helps the admin triage faster).

RISK_KEYWORDS = {
    "gambling":     ["bet", "casino", "poker", "slots", "wager"],
    "streaming":    ["netflix", "hulu", "twitch", "youtube", "spotify"],
    "social_media": ["facebook", "instagram", "tiktok", "twitter", "x.com", "snapchat", "reddit"],
    "file_sharing": ["torrent", "piratebay", "mega.nz", "mediafire"],
    "adult":        ["xvideos", "pornhub", "xnxx"],
    "shopping":     ["amazon", "ebay", "walmart", "target.com"],
}

# High-risk geographic TLDs (mirrors the geo-blocking already configured
# at the firewall layer -- this is the application-layer equivalent)
HIGH_RISK_TLDS = [".ru", ".kp", ".by", ".ir", ".sy"]


def _load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return default
    return default


def _save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_allowlist():
    return _load_json(ALLOWLIST_FILE, DEFAULT_ALLOWLIST)


def save_allowlist(allowlist):
    _save_json(ALLOWLIST_FILE, allowlist)


def load_alerts():
    return _load_json(ALERTS_FILE, [])


def save_alerts(alerts):
    _save_json(ALERTS_FILE, alerts)


def _domain_in_allowlist(domain, allowlist):
    domain = domain.lower().strip().rstrip(".")
    for category, info in allowlist.items():
        for allowed in info["domains"]:
            allowed = allowed.lower()
            if domain == allowed or domain.endswith("." + allowed):
                return category, info
    return None, None


def _detect_risk_signals(domain):
    domain_l = domain.lower()
    signals = []
    for category, keywords in RISK_KEYWORDS.items():
        if any(kw in domain_l for kw in keywords):
            signals.append(category)
    for tld in HIGH_RISK_TLDS:
        if domain_l.endswith(tld):
            signals.append("high_risk_geo_tld")
    return signals


def classify_domain(domain, node="unknown", employee="unknown"):
    """
    Core zero-trust decision function.

    Returns a dict:
      {
        "domain": ...,
        "decision": "ALLOW" | "BLOCK",
        "category": category name or None,
        "risk_signals": [...],
        "reason": human-readable explanation
      }
    """
    domain = domain.lower().strip().rstrip(".")
    allowlist = load_allowlist()
    category, info = _domain_in_allowlist(domain, allowlist)
    risk_signals = _detect_risk_signals(domain)

    if category:
        decision = "ALLOW"
        reason = "Domain matches approved category '{0}': {1}".format(
            category, info["description"]
        )
    else:
        decision = "BLOCK"
        if risk_signals:
            reason = ("Domain not in zero-trust allowlist. Risk signals detected: "
                      + ", ".join(risk_signals))
        else:
            reason = ("Domain not in zero-trust allowlist. No business-need category "
                      "matched -- default-deny applies.")

    # ML risk scoring -- independent of the allow/block decision above.
    # Used to prioritize alerts: a blocked request to youtube.com is low
    # priority, a blocked request to a DGA-looking domain is high priority.
    ml_result = ml_classifier.score_domain(domain)

    result = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "domain": domain,
        "node": node,
        "employee": employee,
        "decision": decision,
        "category": category,
        "risk_signals": risk_signals,
        "reason": reason,
        "ml_risk_score": ml_result["ml_risk_score"],
        "ml_label": ml_result["ml_label"],
        "ml_severity": ml_result["ml_severity"],
        "ml_available": ml_result["ml_available"],
    }

    # Log every decision (allow AND block) for audit purposes
    log = _load_json(LOG_FILE, [])
    log.insert(0, result)
    log = log[:500]  # keep last 500 entries
    _save_json(LOG_FILE, log)

    # If blocked, create/update a pending alert for admin review
    if decision == "BLOCK":
        alerts = load_alerts()
        existing = next((a for a in alerts
                         if a["domain"] == domain and a["status"] == "pending"), None)
        if existing:
            existing["request_count"] = existing.get("request_count", 1) + 1
            existing["last_requested"] = result["timestamp"]
            employees = set(existing.get("employees", []))
            employees.add(employee)
            existing["employees"] = list(employees)
            existing["ml_risk_score"] = result["ml_risk_score"]
            existing["ml_label"] = result["ml_label"]
            existing["ml_severity"] = result["ml_severity"]
        else:
            alerts.insert(0, {
                "id": len(alerts) + 1,
                "domain": domain,
                "node": node,
                "employees": [employee],
                "request_count": 1,
                "first_requested": result["timestamp"],
                "last_requested": result["timestamp"],
                "risk_signals": risk_signals,
                "ml_risk_score": result["ml_risk_score"],
                "ml_label": result["ml_label"],
                "ml_severity": result["ml_severity"],
                "status": "pending",  # pending | approved | denied
            })
        # Sort pending alerts by ML risk score (highest first) so the
        # admin sees the most dangerous-looking domains at the top
        pending = [a for a in alerts if a["status"] == "pending"]
        resolved = [a for a in alerts if a["status"] != "pending"]
        pending.sort(key=lambda a: a.get("ml_risk_score", 0), reverse=True)
        save_alerts(pending + resolved)

    return result


def approve_domain(domain, category="admin_approved"):
    """Admin approves a previously-blocked domain -- adds it to the allowlist."""
    domain = domain.lower().strip().rstrip(".")
    allowlist = load_allowlist()
    if category not in allowlist:
        allowlist[category] = {
            "description": "Domains approved by admin via AI Security panel",
            "domains": [],
            "risk": "admin_approved"
        }
    if domain not in allowlist[category]["domains"]:
        allowlist[category]["domains"].append(domain)
    save_allowlist(allowlist)

    alerts = load_alerts()
    for a in alerts:
        if a["domain"] == domain and a["status"] == "pending":
            a["status"] = "approved"
    save_alerts(alerts)
    return allowlist


def deny_domain(domain):
    """Admin explicitly denies -- domain stays blocked, alert marked resolved."""
    domain = domain.lower().strip().rstrip(".")
    alerts = load_alerts()
    for a in alerts:
        if a["domain"] == domain and a["status"] == "pending":
            a["status"] = "denied"
    save_alerts(alerts)


# ── BASE RULESET GENERATOR ───────────────────────────────────────────────────

NODE_IPS = {
    "dc":      "10.0.0.1",
    "seattle": "10.0.0.2",
    "sf":      "10.0.0.3",
}


def generate_base_ruleset(node_key):
    """
    Generates a zero-trust nftables ruleset for a given node.

    Policy:
      - Default DROP on input, forward, AND output
      - Allow loopback
      - Allow established/related
      - Allow mesh traffic to/from the other two nodes (trusted internal)
      - Allow DNS (port 53) -- queries are inspected by the AI policy
        engine before any resulting connection is allowed
      - Allow NTP (port 123) for time sync / cert validation
      - Allowlisted destination IPs are inserted dynamically by
        approve_domain() / dns_watch.py
      - Everything else: logged and dropped
    """
    my_ip = NODE_IPS.get(node_key, "10.0.0.1")
    others = [ip for k, ip in NODE_IPS.items() if k != node_key]
    node_upper = node_key.upper()
    others_set = ", ".join(others)

    ruleset = """table inet filter {{
    # Zero-Trust Base Ruleset -- Node: {node_key} ({my_ip})
    # Generated by AI Policy Engine -- default DROP, explicit ALLOW only

    chain input {{
        type filter hook input priority 0; policy drop;

        iif lo accept
        ct state established,related accept

        # Mesh peers -- trusted by definition (internal network)
        ip saddr {{ {others_set} }} accept

        # DNS replies (needed for resolution of allowlisted domains)
        udp sport 53 ct state established accept

        log prefix "{node_upper}-DROP-IN: " drop
    }}

    chain forward {{
        type filter hook forward priority 0; policy drop;
        ct state established,related accept
        ip saddr {{ {others_set} }} accept
        ip daddr {{ {others_set} }} accept
    }}

    chain output {{
        type filter hook output priority 0; policy drop;

        oif lo accept
        ct state established,related accept

        # Mesh peers
        ip daddr {{ {others_set} }} accept

        # DNS -- required to resolve any domain (queries are inspected
        # by the AI policy engine before the connection is allowed)
        udp dport 53 accept
        tcp dport 53 accept

        # NTP -- time sync, required for cert validation
        udp dport 123 accept

        # -- Allowlisted destination IPs are inserted below this line --
        # by dns_watch.py / approve_domain() -- DO NOT remove this comment
        # AI-POLICY-ALLOWLIST-ANCHOR

        log prefix "{node_upper}-DROP-OUT: " drop
    }}
}}
""".format(node_key=node_key, my_ip=my_ip, others_set=others_set, node_upper=node_upper)
    return ruleset


def add_allowed_ip(node_key, ip_address, comment=""):
    """
    Called when a domain is approved and resolves to an IP -- returns the
    nft command needed to allow outbound traffic to that IP on 80/443.
    Caller executes this via `ip netns exec <ns> nft ...`.
    """
    cmds = [
        'nft insert rule inet filter output ip daddr {0} tcp dport {{80,443}} accept comment "{1}"'.format(
            ip_address, comment)
    ]
    return cmds


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        result = classify_domain(sys.argv[1],
                                  node=sys.argv[2] if len(sys.argv) > 2 else "dc",
                                  employee=sys.argv[3] if len(sys.argv) > 3 else "test_user")
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python3 ai_policy.py <domain> [node] [employee]")
        print("\nCurrent allowlist categories:")
        for cat, info in load_allowlist().items():
            print("  {0}: {1} domains -- {2}".format(cat, len(info['domains']), info['description']))
