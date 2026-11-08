"""
Simulate an incoming WhatsApp announcement webhook.

Usage:
    python scripts/simulate_announcement.py "<GOOGLE_FORMS_URL>"
    python scripts/simulate_announcement.py --url "<GOOGLE_FORMS_URL>" --server "http://localhost:8000"

This sends a properly authenticated POST request to /api/registration/announcement,
mimicking an Android notification listener (MacroDroid / Tasker).
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime

import httpx

from app.config import get_settings


def main():
    parser = argparse.ArgumentParser(description="Simulate WhatsApp registration announcement.")
    parser.add_argument("url", nargs="?", help="Google Forms URL to test")
    parser.add_argument("--server", default="http://127.0.0.1:8000", help="Base server URL (default: http://127.0.0.1:8000)")
    parser.add_argument("--group", default="Silent Zone Announcements", help="Mock WhatsApp group name")
    args = parser.parse_args()

    if not args.url:
        print("Error: Please provide a Google Forms URL.")
        print("Example: python scripts/simulate_announcement.py 'https://docs.google.com/forms/d/e/.../viewform'")
        sys.exit(1)

    settings = get_settings()
    secret = settings.WEBHOOK_SECRET

    payload = {
        "source_app": "com.whatsapp",
        "group_name": args.group,
        "message_text": f"Silent Zone Registration is now open! Please fill the form immediately: {args.url}",
        "form_url": args.url,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Secret": secret,
    }

    endpoint = f"{args.server.rstrip('/')}/api/registration/announcement"
    print(f"[*] Posting announcement webhook to: {endpoint}")
    print(f"[*] Target Form URL: {args.url}")

    try:
        start_time = time.time()
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(endpoint, json=payload, headers=headers)
        duration = time.time() - start_time

        print(f"[*] Status code: {resp.status_code} ({duration:.2f}s)")
        print(f"[*] Response JSON: {resp.json()}")

        if resp.status_code == 200:
            data = resp.json()
            if data.get("accepted"):
                print("\n[SUCCESS] Webhook accepted! Playwright automation has started in the background.")
                print(f"[SUCCESS] Check live progress on Dashboard: {args.server}/")
            else:
                print(f"\n[NOTICE] Webhook responded with: {data.get('reason')}")
        else:
            print(f"\n[ERROR] Request failed with HTTP {resp.status_code}")

    except Exception as e:
        print(f"\n[ERROR] Failed to send webhook: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

