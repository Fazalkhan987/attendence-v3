import { useState } from "react";
import { Badge, Empty, Field, Notice, PageHead } from "../../components/ui";
import { fmtDateTime, fmtTime, isoToday, label } from "../../utils/format";
import { useApi } from "../../utils/hooks";

export default function Activity() {
  const [tab, setTab] = useState("events");
  const [day, setDay] = useState(isoToday());
  const events = useApi("/recognition/events", { day });
  const logs = useApi("/reports/audit-logs", { limit: 300 });

  return (
    <>
      <PageHead title="System activity">
        <button onClick={() => (tab === "events" ? events.reload() : logs.reload())}>Refresh</button>
      </PageHead>
      <div className="tabs">
        <button className={tab === "events" ? "on" : ""} onClick={() => setTab("events")}>Recognition events</button>
        <button className={tab === "audit" ? "on" : ""} onClick={() => setTab("audit")}>Audit log</button>
      </div>
      {tab === "events" ? (
        <>
          <div className="filters"><Field label="Day"><input type="date" value={day} onChange={(e) => setDay(e.target.value)} /></Field></div>
          <Notice>{events.error}</Notice>
          <div className="table-wrap"><table>
            <thead><tr><th>Time</th><th>Employee</th><th>Camera</th><th>Confidence</th><th>Decision</th><th>Reason</th><th>Action</th></tr></thead>
            <tbody>{events.data?.map((e) => (
              <tr key={e.id}><td>{fmtTime(e.event_time)}</td><td>{e.employee_name || e.employee_code}</td><td>{e.camera_code}</td>
                <td>{(e.confidence * 100).toFixed(1)}%</td><td><Badge value={e.decision} /></td><td>{label(e.reason)}</td><td>{label(e.action) || "—"}</td></tr>
            ))}</tbody></table>
            {events.data?.length === 0 && <Empty>No recognition events on this day.</Empty>}
          </div>
        </>
      ) : (
        <>
          <Notice>{logs.error}</Notice>
          <div className="table-wrap"><table>
            <thead><tr><th>When</th><th>User</th><th>Action</th><th>Entity</th><th>IP</th></tr></thead>
            <tbody>{logs.data?.map((l) => (
              <tr key={l.id}><td>{fmtDateTime(l.created_at)}</td><td>{l.user_email || "—"}</td><td>{label(l.action)}</td><td>{l.entity} {l.entity_id}</td><td>{l.ip}</td></tr>
            ))}</tbody></table>
            {logs.data?.length === 0 && <Empty>No audit entries.</Empty>}
          </div>
        </>
      )}
    </>
  );
}
