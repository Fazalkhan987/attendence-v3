# Database

```mermaid
erDiagram
  users ||--o| employees : "has profile"
  departments ||--o{ employees : contains
  employees ||--o{ face_embeddings : enrolls
  departments ||--o{ schedules : owns
  schedules ||--o{ schedule_assignments : assigned
  employees ||--o{ schedule_assignments : works
  cameras ||--o{ recognition_events : emits
  employees ||--o{ recognition_events : recognised
  employees ||--o{ attendance : has
  schedules ||--o{ attendance : session
  employees ||--o{ leave_requests : requests
  leave_types ||--o{ leave_requests : typed
  attendance ||--o{ attendance_corrections : audited
  users ||--o{ audit_logs : performs
```

Key constraints: `attendance (employee_id, schedule_id, work_date)` UNIQUE; `recognition_events (camera_id, event_uuid)` UNIQUE;
`schedules` CHECK end_time > start_time; `leave_requests` CHECK end_date >= start_date.
Recognition events and attendance are separate tables; one employee may produce many events but one row per session per day.

Retention: face embeddings are deleted on deactivation or consent withdrawal; recognition events after `EVENT_RETENTION_DAYS`.
