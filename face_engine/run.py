"""Live recognition loop:  python run.py"""
import logging
import time
from datetime import datetime

import cv2

import config
from camera import VideoStream
from detection import detect, face_size, get_analyzer
from event_sender import EventSender, fetch_gallery
from recognition import Gallery, IdentityConfirmer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("engine")


def refresh(gallery: Gallery):
    try:
        gallery.load(fetch_gallery())
        log.info("gallery loaded: %d employees, %d embeddings", len(gallery.codes), len(gallery.matrix))
    except Exception as e:
        log.warning("gallery refresh failed: %s", e)


def main():
    get_analyzer()
    sender, confirmer, gallery = EventSender(), IdentityConfirmer(), Gallery()
    stream = VideoStream(config.CAMERA_SOURCE).start()
    last_sent: dict[str, float] = {}
    last_refresh, n = 0.0, 0
    refresh(gallery)
    last_refresh = time.time()
    log.info("Face engine running on camera %s", config.CAMERA_ID)

    try:
        while True:
            frame = stream.read()
            if frame is None:
                time.sleep(0.05)
                continue
            n += 1
            now = time.time()
            if now - last_refresh > config.GALLERY_REFRESH_SECONDS:
                refresh(gallery)
                last_refresh = now
            if n % config.PROCESS_EVERY_N_FRAMES:
                continue

            for f in detect(frame):
                label, color = "unknown", (0, 0, 255)
                if f.det_score >= config.LIVE_MIN_DET_SCORE and face_size(f) >= config.LIVE_MIN_FACE_SIZE:
                    code, score = gallery.match(f.normed_embedding)
                    if code:
                        label, color = f"{code} {score:.2f}", (0, 200, 0)
                        confirmed = confirmer.add(code, now, f.kps, f.bbox, score)
                        if confirmed is not None and now - last_sent.get(code, 0) >= config.COOLDOWN_SECONDS:
                            sender.send(code, confirmed, datetime.now().astimezone().isoformat(timespec="seconds"))
                            last_sent[code] = now
                if config.SHOW_PREVIEW:
                    x1, y1, x2, y2 = [int(v) for v in f.bbox]
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(frame, label, (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            if config.SHOW_PREVIEW:
                cv2.imshow("Face engine", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    finally:
        stream.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
