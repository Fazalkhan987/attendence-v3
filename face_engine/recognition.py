from collections import defaultdict, deque

import numpy as np

import config


class Gallery:
    """In-memory matrix of enrolled embeddings (rows are L2-normalised)."""

    def __init__(self):
        self.codes: list[str] = []
        self.owner = np.empty(0, dtype=np.int32)
        self.matrix = np.empty((0, 512), dtype=np.float32)

    def load(self, employees: list[dict]):
        rows, owner = [], []
        self.codes = [e["employee_id"] for e in employees]
        for i, e in enumerate(employees):
            for v in e["embeddings"]:
                rows.append(v)
                owner.append(i)
        if rows:
            m = np.asarray(rows, dtype=np.float32)
            self.matrix = m / np.linalg.norm(m, axis=1, keepdims=True)
            self.owner = np.asarray(owner, dtype=np.int32)
        else:
            self.matrix, self.owner = np.empty((0, 512), dtype=np.float32), np.empty(0, dtype=np.int32)

    def match(self, emb: np.ndarray):
        """Return (employee_code | None, score). Unknown faces and ambiguous matches return None."""
        if not len(self.matrix):
            return None, 0.0
        sims = self.matrix @ (emb / np.linalg.norm(emb))
        per_emp = np.full(len(self.codes), -1.0, dtype=np.float32)
        np.maximum.at(per_emp, self.owner, sims)
        order = np.argsort(per_emp)[::-1]
        best = float(per_emp[order[0]])
        second = float(per_emp[order[1]]) if len(order) > 1 else -1.0
        if best < config.SIMILARITY_THRESHOLD or best - second < config.MATCH_MARGIN:
            return None, best
        return self.codes[order[0]], best


class IdentityConfirmer:
    """Confirms an identity only after N consistent frames inside a time window, plus a motion liveness cue."""

    def __init__(self):
        self.hist = defaultdict(lambda: deque(maxlen=60))

    def add(self, code: str, ts: float, kps: np.ndarray, bbox, score: float):
        w = max(1.0, float(bbox[2] - bbox[0]))
        h = self.hist[code]
        h.append((ts, np.asarray(kps, dtype=np.float32) / w, score))
        while h and ts - h[0][0] > config.CONFIRM_WINDOW_SECONDS:
            h.popleft()
        if len(h) < config.CONFIRM_FRAMES:
            return None
        if config.LIVENESS_ENABLED and not self._moves(h):
            return None
        mean_score = float(np.mean([x[2] for x in h]))
        h.clear()
        return mean_score

    @staticmethod
    def _moves(h) -> bool:
        """Reject perfectly static faces (printed photo on a stand) and wildly jumping detections."""
        pts = np.stack([x[1] for x in h])            # (frames, 5, 2), normalised by face width
        motion = float(pts.std(axis=0).mean())
        return config.LIVENESS_MIN_MOTION <= motion <= config.LIVENESS_MAX_MOTION
