"""Send the daily Good Magical Morning alert to every phone that turned it on.

Runs in GitHub Actions (.github/workflows/morning-alert.yml). Needs env:
  PUSH_ENDPOINT  the Apps Script /exec URL (holds the subscription list)
  PUSH_KEY       shared secret for reading that list
  VAPID_PRIVATE  the VAPID private key (PEM)
  SCHEDULE       the cron line that started this run (empty for a manual test)
"""
import json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo
from pywebpush import webpush, WebPushException

NY = ZoneInfo("America/New_York")
TITLE = "hot news waitin' ☕️"
URL = "https://today.goodmagicalmorning.com/"
# Two cron lines cover daylight and standard time; only the one that lands near 9:00 in New York sends.
SLOTS = {-4: "50 12 * * *", -5: "50 13 * * *"}


def wait_for_send_time():
    sched = os.environ.get("SCHEDULE", "")
    if not sched:
        return True  # manual run: send right away
    now = datetime.now(NY)
    if SLOTS.get(int(now.utcoffset().total_seconds() // 3600)) != sched:
        print("other daylight-saving slot; nothing to do")
        return False
    target = now.replace(hour=9, minute=0, second=0, microsecond=0)
    if now < target:
        print(f"waiting {int((target - now).total_seconds())}s until 9:00")
        time.sleep((target - now).total_seconds())
    return True


def main():
    if not wait_for_send_time():
        return
    endpoint, key = os.environ["PUSH_ENDPOINT"], os.environ["PUSH_KEY"]
    with open("vapid.pem", "w") as f:
        f.write(os.environ["VAPID_PRIVATE"])
    q = urllib.parse.urlencode({"action": "subs", "key": key})
    subs = json.load(urllib.request.urlopen(f"{endpoint}?{q}", timeout=60)).get("subs", [])
    print(f"{len(subs)} phone(s) signed up")
    payload = json.dumps({"title": TITLE, "body": "", "url": URL})
    sent = gone = failed = 0
    for raw in subs:
        sub = json.loads(raw)
        try:
            webpush(sub, payload, vapid_private_key="vapid.pem",
                    vapid_claims={"sub": "https://today.goodmagicalmorning.com"}, ttl=4 * 3600)
            sent += 1
        except WebPushException as e:
            code = e.response.status_code if e.response is not None else None
            if code in (404, 410):  # phone unsubscribed or app removed
                gone += 1
                data = urllib.parse.urlencode({"type": "unsubscribe", "endpoint": sub["endpoint"]}).encode()
                urllib.request.urlopen(endpoint, data=data, timeout=60)
            else:
                failed += 1
                print(f"push failed ({code}): {e}")
    print(f"sent {sent}, removed {gone}, failed {failed}")
    if failed and not sent:
        sys.exit(1)


if __name__ == "__main__":
    main()
