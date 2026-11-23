# Smart Employee Attendance Management System (Face Recognition)

FastAPI + PostgreSQL backend, React frontend, and an independent InsightFace (SCRFD + ArcFace) face engine.

```
frontend (React) ──REST/JWT──► backend (FastAPI) ──► PostgreSQL
                                   ▲   │ enrolment (service token)
        signed events (HMAC)       │   ▼
        face_engine/run.py ────────┘  face_engine/server.py (:8001)
```

## Run

1. **PostgreSQL**: `createdb attendance`
2. **Backend**
   ```
   cd backend && python -m venv .venv && . .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env     # set JWT_SECRET, FERNET_KEY, FACE_ENGINE_TOKEN, DATABASE_URL
   uvicorn app.main:app --reload --port 8000
   ```

   First start creates tables and the admin from `ADMIN_EMAIL` / `ADMIN_PASSWORD`. API docs: http://localhost:8000/docs
3. **Face engine enrolment service** (same `FACE_ENGINE_TOKEN` as the backend)
   ```
   cd face_engine && pip install -r requirements.txt && cp .env.example .env
   uvicorn server:app --port 8001
   ```
4. **Frontend**: `cd frontend && npm install && npm run dev` → http://localhost:5173
5. In the UI: create a department → add employee (tick biometric consent) → **Enroll face** (webcam) → add a schedule and assign the employee → add a camera and copy its secret.
6. **Live recognition**: put the camera ID/secret into `face_engine/.env`, then `python run.py` (webcam index `CAMERA_SOURCE=0`, or an RTSP URL for CCTV).

## Key rules (all enforced in the backend)

- Face engine sends only `{event_id, employee_id, camera_id, confidence, timestamp}`, HMAC-SHA256 signed with the camera secret (`X-Camera-Id`, `X-Timestamp`, `X-Signature`); replay-protected by timestamp window + unique `(camera_id, event_id)`.
- Backend validates employee, status, camera, department, schedule, session window, approved leave, duplicates, confidence; it alone writes attendance.
- Check-in saved immediately; Present up to `start + grace`, Late afterwards. Absent / On Leave / Incomplete are only created after `end + ABSENT_VERIFICATION_MINUTES` (background job every 5 min).
- Check-out only inside the schedule's check-out window and only from exit-capable cameras.
- Manual edits require a reason and create `attendance_corrections` + `audit_logs` rows.
- Embeddings are Fernet-encrypted at rest and never returned to the browser; deleting consent / deactivating an employee deletes them. Recognition events are purged after `EVENT_RETENTION_DAYS`.
- Backups: `backend/scripts/backup.sh` (cron daily).

## Known limits

- Presentation-attack defence is a lightweight motion check; for production add a passive anti-spoofing model (e.g. Silent-Face-Anti-Spoofing) or IR/depth camera.
- Use HTTPS (reverse proxy) between all components in any real deployment.
- Overnight shifts (end time before start time) are not supported.
