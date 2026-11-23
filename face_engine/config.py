import os

from dotenv import load_dotenv

load_dotenv()


def _b(name, default):
    return os.getenv(name, str(default)).lower() in ("1", "true", "yes")


BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/api/v1").rstrip("/")
CAMERA_ID = os.getenv("CAMERA_ID", "CAM-01")
CAMERA_SECRET = os.getenv("CAMERA_SECRET", "")
_src = os.getenv("CAMERA_SOURCE", "0")
CAMERA_SOURCE = int(_src) if _src.isdigit() else _src      # webcam index or RTSP/HTTP URL
SERVICE_TOKEN = os.getenv("FACE_ENGINE_TOKEN", "")

MODEL_NAME = os.getenv("MODEL_NAME", "buffalo_l")           # SCRFD detector + ArcFace (ResNet50) recogniser
CTX_ID = int(os.getenv("CTX_ID", "-1"))                     # -1 = CPU, 0 = first GPU
DET_SIZE = (640, 640)

# live recognition
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.5"))
MATCH_MARGIN = float(os.getenv("MATCH_MARGIN", "0.05"))     # best vs second-best employee
CONFIRM_FRAMES = int(os.getenv("CONFIRM_FRAMES", "5"))
CONFIRM_WINDOW_SECONDS = float(os.getenv("CONFIRM_WINDOW_SECONDS", "4"))
COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_SECONDS", "120"))
PROCESS_EVERY_N_FRAMES = int(os.getenv("PROCESS_EVERY_N_FRAMES", "3"))
GALLERY_REFRESH_SECONDS = int(os.getenv("GALLERY_REFRESH_SECONDS", "60"))
LIVE_MIN_FACE_SIZE = int(os.getenv("LIVE_MIN_FACE_SIZE", "70"))
LIVE_MIN_DET_SCORE = float(os.getenv("LIVE_MIN_DET_SCORE", "0.6"))
LIVENESS_ENABLED = _b("LIVENESS_ENABLED", True)
LIVENESS_MIN_MOTION = float(os.getenv("LIVENESS_MIN_MOTION", "0.004"))
LIVENESS_MAX_MOTION = float(os.getenv("LIVENESS_MAX_MOTION", "0.25"))
SHOW_PREVIEW = _b("SHOW_PREVIEW", False)

# enrollment quality gates
ENROLL_MIN_FACE_SIZE = int(os.getenv("ENROLL_MIN_FACE_SIZE", "100"))
ENROLL_MIN_DET_SCORE = float(os.getenv("ENROLL_MIN_DET_SCORE", "0.7"))
ENROLL_MIN_SHARPNESS = float(os.getenv("ENROLL_MIN_SHARPNESS", "40"))
ENROLL_MAX_YAW = float(os.getenv("ENROLL_MAX_YAW", "35"))
