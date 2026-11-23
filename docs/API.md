# API (prefix /api/v1)

| Area | Endpoints |
|---|---|
| Auth | POST /auth/login, GET /auth/me, POST /auth/change-password |
| Departments | GET/POST /departments, PUT/DELETE /departments/{id} |
| Employees | GET/POST /employees, GET/PUT/DELETE /employees/{id}, GET /employees/{id}/schedules |
| Faces | POST /employees/{id}/face/enroll, DELETE /employees/{id}/face, GET /faces/gallery (camera-signed) |
| Cameras | GET/POST /cameras, PUT /cameras/{id}, POST /cameras/{id}/rotate-secret |
| Schedules | GET/POST /schedules, PUT/DELETE /schedules/{id}, GET/POST /schedules/{id}/assignments, DELETE /schedules/assignments/{id} |
| Recognition | POST /recognition/events (camera-signed), GET /recognition/events |
| Attendance | GET /attendance, PATCH /attendance/{id}, POST /attendance/manual, GET /attendance/{id}/corrections, POST /attendance/finalize |
| Leave | GET/POST /leave, PATCH /leave/{id}/review, POST /leave/{id}/cancel, GET/POST /leave/types |
| Reports | GET /reports/dashboard, /reports/summary, /reports/attendance.csv, /reports/audit-logs |

Event example:
```json
{"event_id":"c0ffee...","employee_id":"EMP-001","camera_id":"CAM-01","confidence":0.91,"timestamp":"2026-11-23T09:15:00+05:00"}
```
Headers: `X-Camera-Id`, `X-Timestamp` (unix seconds), `X-Signature` = hex HMAC-SHA256(secret, `"<timestamp>." + raw_body`).
