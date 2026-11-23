"""Enrollment: turn captured samples into quality-checked ArcFace embeddings."""
import base64

import cv2
import numpy as np

import config
from detection import detect, face_size, sharpness, yaw_of


def decode_image(data: str):
    if "," in data[:50]:
        data = data.split(",", 1)[1]
    buf = np.frombuffer(base64.b64decode(data), dtype=np.uint8)
    return cv2.imdecode(buf, cv2.IMREAD_COLOR)


def process_sample(data: str) -> dict:
    try:
        img = decode_image(data)
    except Exception:
        img = None
    if img is None:
        return {"ok": False, "reason": "unreadable_image"}
    faces = sorted(detect(img), key=face_size, reverse=True)
    if not faces:
        return {"ok": False, "reason": "no_face"}
    if len(faces) > 1 and face_size(faces[1]) > 0.5 * face_size(faces[0]):
        return {"ok": False, "reason": "multiple_faces"}
    f = faces[0]
    if f.det_score < config.ENROLL_MIN_DET_SCORE:
        return {"ok": False, "reason": "low_detection_confidence"}
    if face_size(f) < config.ENROLL_MIN_FACE_SIZE:
        return {"ok": False, "reason": "face_too_small"}
    if sharpness(img, f) < config.ENROLL_MIN_SHARPNESS:
        return {"ok": False, "reason": "blurry"}
    if yaw_of(f) > config.ENROLL_MAX_YAW:
        return {"ok": False, "reason": "face_not_frontal"}
    emb = np.asarray(f.normed_embedding, dtype=np.float32)
    return {"ok": True, "reason": None, "quality": float(f.det_score), "embedding": emb.tolist()}


def process_samples(images: list[str]) -> list[dict]:
    return [process_sample(i) for i in images]
