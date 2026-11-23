import { PageHead, Notice } from "../../components/ui";
import { useApi } from "../../utils/hooks";
import { fmtDate, label } from "../../utils/format";

export default function Dashboard() {
  const { data, error, reload } = useApi("/reports/dashboard");
  const a = data?.attendance_today || {};
  const cards = [
    ["Active employees", data?.employees, ""],
    ["Present today", a.present, ""],
    ["Late today", a.late, "late"],
    ["Absent today", a.absent, "absent"],
    ["On leave", a.on_leave, "leave"],
    ["Pending leave requests", data?.pending_leave, "late"],
    ["Recognitions accepted today", data?.accepted_events_today, ""],
    ["Active cameras", data?.active_cameras, ""],
  ];
  return (
    <>
      <PageHead title="Dashboard">
        <span className="muted">{data && fmtDate(data.date)}</span>
        <button onClick={reload}>Refresh</button>
      </PageHead>
      <Notice>{error}</Notice>
      <div className="stats">
        {cards.map(([t, v, c]) => (
          <div key={t} className={`stat ${c}`}><b>{v ?? "–"}</b><span>{t}</span></div>
        ))}
      </div>
      <div className="card">
        <h3>Today by status</h3>
        <p className="muted">Absent is only recorded after each session ends and the verification period has passed.</p>
        <div className="actions">
          {Object.entries(a).map(([k, v]) => <span key={k} className={`badge b-${k}`}>{label(k)}: {v}</span>)}
        </div>
      </div>
    </>
  );
}
