import hashlib
import hmac
import json
import logging
import queue
import threading
import time
import uuid

import requests

import config

log = logging.getLogger("sender")


def _sign(ts: str, body: bytes) -> str:
    return hmac.new(config.CAMERA_SECRET.encode(), ts.encode() + b"." + body, hashlib.sha256).hexdigest()


def _headers(body: bytes) -> dict:
    ts = str(int(time.time()))
    return {"Content-Type": "application/json", "X-Camera-Id": config.CAMERA_ID,
            "X-Timestamp": ts, "X-Signature": _sign(ts, body)}


def fetch_gallery() -> list[dict]:
    r = requests.get(f"{config.BACKEND_URL}/faces/gallery", headers=_headers(b""), timeout=30)
    r.raise_for_status()
    return r.json()["employees"]


class EventSender:
    """Sends only confirmed recognition events. Retries on network errors / 5xx; drops on 4xx."""

    def __init__(self):
        self.q: queue.Queue = queue.Queue()
        threading.Thread(target=self._worker, daemon=True).start()

    def send(self, employee_code: str, confidence: float, timestamp_iso: str):
        self.q.put({"payload": {"event_id": uuid.uuid4().hex, "employee_id": employee_code,
                                "camera_id": config.CAMERA_ID, "confidence": round(confidence, 4),
                                "timestamp": timestamp_iso}, "tries": 0})

    def _worker(self):
        while True:
            item = self.q.get()
            body = json.dumps(item["payload"], separators=(",", ":")).encode()
            try:
                r = requests.post(f"{config.BACKEND_URL}/recognition/events", data=body,
                                  headers=_headers(body), timeout=10)
                if r.status_code >= 500:
                    raise requests.RequestException(f"HTTP {r.status_code}")
                log.info("event %s -> %s %s", item["payload"]["employee_id"], r.status_code,
                         r.json().get("reason") if r.headers.get("content-type", "").startswith("application/json") else "")
            except requests.RequestException as e:
                item["tries"] += 1
                if item["tries"] < 5:
                    log.warning("send failed (%s); retry %d", e, item["tries"])
                    time.sleep(2 ** item["tries"])
                    self.q.put(item)
                else:
                    log.error("dropping event after retries: %s", item["payload"]["event_id"])
