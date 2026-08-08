"""
AI Security -- Domain Risk Model Training
============================================
Trains a machine learning model to score how "suspicious" a domain
NAME looks -- a classic technique used for DGA (Domain Generation
Algorithm) and phishing-domain detection.

This is INDEPENDENT of the zero-trust allow/block policy:
  - The zero-trust policy engine (ai_policy.py) decides ALLOW/BLOCK
    based on a fixed business-need allowlist (deterministic).
  - This ML model adds a "ml_risk_score" (0.0-1.0) used to PRIORITIZE
    alerts -- e.g. a blocked request to "youtube.com" gets a low
    score, but a blocked request to "xj3kq9fh2z.tk" gets a high score
    because the string itself resembles algorithmically-generated /
    phishing domains.

Approach: character n-gram TF-IDF + Random Forest classifier.
This is the standard lightweight approach used in published DGA
detection research (e.g. Yadav et al., Antonakakis et al.) and runs
fast enough for real-time inference on a Raspberry Pi.

Run:
  python3 train_model.py
Produces:
  domain_risk_model.joblib
"""

import os
import random
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "domain_risk_model.joblib")

# ── TRAINING DATA ────────────────────────────────────────────────────────────

# Class 0 = BENIGN -- domain string looks like a normal, human-chosen,
# legitimately-registered domain (regardless of whether it's on the
# business allowlist -- this is about string structure, not policy).
BENIGN_DOMAINS = [
    "google.com", "microsoft.com", "apple.com", "github.com", "slack.com",
    "zoom.us", "salesforce.com", "dropbox.com", "adobe.com", "paypal.com",
    "chase.com", "bankofamerica.com", "wellsfargo.com", "irs.gov", "usps.com",
    "fedex.com", "ups.com", "linkedin.com", "stackoverflow.com", "wikipedia.org",
    "nytimes.com", "cnn.com", "weather.com", "espn.com", "amazon.com",
    "walmart.com", "target.com", "costco.com", "hulu.com", "netflix.com",
    "youtube.com", "facebook.com", "instagram.com", "twitter.com", "reddit.com",
    "spotify.com", "twitch.tv", "tiktok.com", "snapchat.com", "pinterest.com",
    "outlook.com", "office365.com", "gmail.com", "yahoo.com", "bing.com",
    "ebay.com", "etsy.com", "airbnb.com", "uber.com", "lyft.com",
    "doordash.com", "grubhub.com", "expedia.com", "booking.com", "tripadvisor.com",
    "indeed.com", "glassdoor.com", "monster.com", "zillow.com", "redfin.com",
    "homedepot.com", "lowes.com", "bestbuy.com", "newegg.com", "wayfair.com",
    "starbucks.com", "mcdonalds.com", "chipotle.com", "dominos.com", "subway.com",
    "delta.com", "united.com", "southwest.com", "americanairlines.com", "jetblue.com",
    "marriott.com", "hilton.com", "hyatt.com", "ihg.com", "wynn.com",
    "discover.com", "capitalone.com", "americanexpress.com", "citibank.com", "usbank.com",
    "archive.ubuntu.com", "security.ubuntu.com", "deb.debian.org", "pool.ntp.org",
    "ocsp.digicert.com", "login.microsoftonline.com", "outlook.office365.com",
    "stripe.com", "squareup.com", "venmo.com", "robinhood.com", "coinbase.com",
    "att.com", "verizon.com", "tmobile.com", "comcast.com", "spectrum.com",
]

# Class 1 = SUSPICIOUS -- domain string structurally resembles algorithmically-
# generated (DGA) domains or phishing/typosquatting patterns.
random.seed(42)
_CONSONANTS = "bcdfghjklmnpqrstvwxyz"
_VOWELS = "aeiou"
_RISKY_TLDS = ["tk", "xyz", "top", "info", "biz", "ru", "cc", "click", "icu", "ws"]

def _gen_dga(n):
    """Generate pseudo-random alphanumeric strings that mimic DGA domains."""
    out = []
    for _ in range(n):
        length = random.randint(8, 16)
        chars = []
        for i in range(length):
            if random.random() < 0.35:
                chars.append(random.choice("0123456789"))
            elif i % 2 == 0:
                chars.append(random.choice(_CONSONANTS))
            else:
                chars.append(random.choice(_VOWELS + _CONSONANTS))
        name = "".join(chars)
        tld = random.choice(_RISKY_TLDS)
        out.append(f"{name}.{tld}")
    return out

# Phishing / typosquatting style domains (real attack patterns)
PHISHING_DOMAINS = [
    "paypal-secure-login.com", "login-verify-account.net", "amaz0n-support.com",
    "appleid-confirm.com", "secure-bankofamerica-login.com", "wellsfargo-alert.net",
    "microsoft-billing-update.com", "chase-online-verify.com", "netflix-payment-update.com",
    "facebook-security-check.net", "irs-tax-refund-verify.com", "usps-package-delay.info",
    "fedex-tracking-update.net", "linkedin-account-locked.com", "instagram-verify-id.net",
    "google-docs-share.xyz", "office365-login-update.net", "dropbox-file-shared.click",
    "coinbase-wallet-verify.com", "venmo-payment-alert.net",
]

SUSPICIOUS_DOMAINS = _gen_dga(80) + PHISHING_DOMAINS

print(f"Benign samples:     {len(BENIGN_DOMAINS)}")
print(f"Suspicious samples: {len(SUSPICIOUS_DOMAINS)}")

X = BENIGN_DOMAINS + SUSPICIOUS_DOMAINS
y = [0] * len(BENIGN_DOMAINS) + [1] * len(SUSPICIOUS_DOMAINS)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, random_state=42, stratify=y
)

# ── PIPELINE: char n-gram TF-IDF -> Random Forest ──────────────────────────
pipeline = Pipeline([
    ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=1)),
    ("clf", RandomForestClassifier(n_estimators=150, max_depth=12, random_state=42)),
])

pipeline.fit(X_train, y_train)

# ── EVALUATION ───────────────────────────────────────────────────────────────
y_pred = pipeline.predict(X_test)
acc = accuracy_score(y_test, y_pred)

print(f"\nTest accuracy: {acc:.3f}\n")
print("Classification report:")
print(classification_report(y_test, y_pred, target_names=["benign", "suspicious"]))
print("Confusion matrix:")
print(confusion_matrix(y_test, y_pred))

# ── SAVE MODEL ───────────────────────────────────────────────────────────────
joblib.dump(pipeline, MODEL_PATH)
print(f"\nModel saved to {MODEL_PATH}")

# ── QUICK SANITY CHECK ────────────────────────────────────────────────────────
print("\nSanity check on unseen domains:")
samples = [
    "facebook.com", "google.com", "slack.com",
    "xk29fj3kqz.tk", "9j2lq8wprm.icu", "paypal-account-verify.info",
    "chase.com", "kx7m2nq.ru"
]
probs = pipeline.predict_proba(samples)
for s, p in zip(samples, probs):
    print(f"  {s:35s} -> suspicious_score={p[1]:.3f}")
