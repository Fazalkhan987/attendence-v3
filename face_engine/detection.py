import cv2
import numpy as np

import config

_app = None


def get_analyzer():
    """Lazy singleton InsightFace pipeline (detection + landmarks + ArcFace embedding)."""
    global _app
    if _app is None:
        from insightface.app import FaceAnalysis
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if config.CTX_ID >= 0 else ["CPUExecutionProvider"]
        _app = FaceAnalysis(name=config.MODEL_NAME, providers=providers)
        _app.prepare(ctx_id=config.CTX_ID, det_size=config.DET_SIZE)
    return _app


def detect(frame: np.ndarray):
    return get_analyzer().get(frame)


def face_size(face) -> float:
    x1, y1, x2, y2 = face.bbox
    return float(min(x2 - x1, y2 - y1))


def sharpness(frame: np.ndarray, face) -> float:
    x1, y1, x2, y2 = [int(v) for v in face.bbox]
    h, w = frame.shape[:2]
    crop = frame[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
    if crop.size == 0:
        return 0.0
    return float(cv2.Laplacian(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())


def yaw_of(face) -> float:
    pose = getattr(face, "pose", None)
    return float(abs(pose[1])) if pose is not None else 0.0
