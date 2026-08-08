"""
AI Policy Engine -- Admin Notification System
================================================
Sends notifications when an employee request is BLOCKED by the
zero-trust policy engine.

Two channels:
  1. Console / log file  (always works, no config needed)
  2. Email via SMTP      (optional -- requires config.json)

To enable email:
  1. Copy config.example.json to config.json
  2. Fill in your SMTP details (Gmail users: use an "App Password",
     not your normal password -- see Google Account > Security >
     App Passwords)
  3. Restart admin.py
"""

import json
import os
import smtplib
import datetime
from email.mime.text import MIMEText

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
NOTIFY_LOG  = os.path.join(BASE_DIR, "notifications.log")

DEFAULT_CONFIG = {
    "email_enabled": False,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_username": "",
    "smtp_app_password": "",
    "admin_email": "",
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception:
            return DEFAULT_CONFIG
    return DEFAULT_CONFIG


def _log_to_file(message):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(NOTIFY_LOG, "a") as f:
        f.write(f"[{ts}] {message}\n")


def send_email(subject, body, config=None):
    config = config or load_config()
    if not config.get("email_enabled"):
        return False, "Email notifications disabled (configure config.json to enable)"
    if not all([config.get("smtp_username"), config.get("smtp_app_password"), config.get("admin_email")]):
        return False, "Email config incomplete -- check config.json"

    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = config["smtp_username"]
        msg["To"] = config["admin_email"]

        with smtplib.SMTP(config["smtp_server"], config["smtp_port"]) as server:
            server.starttls()
            server.login(config["smtp_username"], config["smtp_app_password"])
            server.sendmail(config["smtp_username"], config["admin_email"], msg.as_string())
        return True, "Email sent to " + config["admin_email"]
    except Exception as e:
        return False, "Email failed: " + str(e)


def notify_blocked_request(alert):
    """
    Called whenever a domain is blocked. Always logs to file/console.
    Sends email if configured.
    """
    subject = "[AI Firewall] Blocked request: {0}".format(alert["domain"])
    ml_score = alert.get("ml_risk_score")
    ml_line = ""
    if ml_score is not None:
        ml_line = "ML risk score:  {0:.0%} ({1})\n".format(ml_score, alert.get("ml_label", "unknown"))

    body = (
        "The AI Policy Engine blocked a request to a non-allowlisted domain.\n\n"
        "Domain:        {domain}\n"
        "Node:          {node}\n"
        "Employee(s):   {employees}\n"
        "Request count: {request_count}\n"
        "Risk signals:  {risk_signals}\n"
        "{ml_line}"
        "First seen:    {first_requested}\n"
        "Last seen:     {last_requested}\n\n"
        "This is a zero-trust network -- the domain remains BLOCKED until "
        "an admin approves it in the Admin GUI (AI Security tab)."
    ).format(
        domain=alert["domain"], node=alert["node"],
        employees=", ".join(alert["employees"]),
        request_count=alert["request_count"],
        risk_signals=", ".join(alert["risk_signals"]) or "none",
        ml_line=ml_line,
        first_requested=alert["first_requested"],
        last_requested=alert["last_requested"],
    )

    _log_to_file(f"BLOCKED: {alert['domain']} (node={alert['node']}, "
                  f"employees={alert['employees']}, count={alert['request_count']})")
    print("\n" + "=" * 60)
    print("AI FIREWALL ALERT -- ADMIN NOTIFICATION")
    print("=" * 60)
    print(body)
    print("=" * 60 + "\n")

    ok, msg = send_email(subject, body)
    _log_to_file("Email notification: " + msg)
    return ok, msg


if __name__ == "__main__":
    # Test alert
    test_alert = {
        "domain": "test-blocked-site.com",
        "node": "dc",
        "employees": ["jdoe"],
        "request_count": 1,
        "risk_signals": [],
        "first_requested": "2025-06-15 12:00:00",
        "last_requested": "2025-06-15 12:00:00",
    }
    notify_blocked_request(test_alert)
