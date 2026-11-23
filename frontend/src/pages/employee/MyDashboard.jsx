import { useState } from "react";
import { Badge, Empty, Field, Notice, PageHead } from "../../components/ui";
import { useAuth } from "../../context/AuthContext";
import api, { errMsg } from "../../services/api";
import { DAYS, fmtDate, fmtTime, hhmm, isoDaysAgo, isoToday, minutes } from "../../utils/format";
import { useApi } from "../../utils/hooks";

export default function MyDashboard() {
  const { me } = useAuth();
  const emp = me.employee;
  const [tab, setTab] = useState("attendance");
  const [range, setRange] = useState({ date_from: isoDaysAgo(30), date_to: isoToday() });
  const att = useApi("/attendance", { ...range, limit: 1000 });
  const sched = useApi(emp ? `/employees/${emp.id}/schedules` : "/leave/types");
  const leave = useApi("/leave");
  const types = useApi("/leave/types");
  const [form, setForm] = useState({ leave_type_id: "", start_date: isoToday(), end_date: isoToday(), reason: "" });
  const [msg, setMsg] = useState(null);

  if (!emp) return <Notice>No employee profile is linked to this account. Contact your administrator.</Notice>;

  const submit = async (e) => {
    e.preventDefault(); setMsg(null);
    try {
      await api.post("/leave", { ...form, leave_type_id: Number(form.leave_type_id) });
      setMsg({ kind: "ok", text: "Leave request submitted." });
      leave.reload();
    } catch (x) { setMsg({ kind: "error", text: errMsg(x) }); }
  };
  const cancel = async (id) => { await api.post(`/leave/${id}/cancel`); leave.reload(); };

  return (
    <>
      <div className="profile">
        {emp.photo ? <img className="avatar" src={emp.photo} alt="" /> : <div className="avatar">{emp.full_name[0]}</div>}
        <div>
          <h1>{emp.full_name}</h1>
          <div className="muted">{emp.employee_code} · {emp.designation} · {emp.department_name}</div>
          <div className="muted">Supervisor: {emp.supervisor_name || "—"} · Joined {fmtDate(emp.joining_date)}</div>
        </div>
      </div>
      <div className="tabs">
        {[["attendance", "Attendance history"], ["schedules", "My schedules"], ["leave", "Leave"]].map(([k, t]) => (
          <button key={k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{t}</button>
        ))}
      </div>

      {tab === "attendance" && (
        <>
          <div className="filters">
            <Field label="From"><input type="date" value={range.date_from} onChange={(e) => setRange({ ...range, date_from: e.target.value })} /></Field>
            <Field label="To"><input type="date" value={range.date_to} onChange={(e) => setRange({ ...range, date_to: e.target.value })} /></Field>
          </div>
          <Notice>{att.error}</Notice>
          <div className="table-wrap"><table>
            <thead><tr><th>Date</th><th>Session</th><th>Check-in</th><th>Check-out</th><th>Worked</th><th>Status</th></tr></thead>
            <tbody>{att.data?.map((a) => (
              <tr key={a.id}><td>{fmtDate(a.work_date)}</td><td>{a.schedule_name} <span className="muted">{hhmm(a.schedule_start)}–{hhmm(a.schedule_end)}</span></td>
                <td>{fmtTime(a.check_in)}</td><td>{fmtTime(a.check_out)}{a.is_early_departure && " (early)"}</td><td>{minutes(a.worked_minutes)}</td><td><Badge value={a.status} /></td></tr>
            ))}</tbody></table>
            {att.data?.length === 0 && <Empty>No attendance recorded in this period.</Empty>}
          </div>
        </>
      )}

      {tab === "schedules" && (
        <div className="table-wrap"><table>
          <thead><tr><th>Session</th><th>Hours</th><th>Days</th><th>Grace period</th></tr></thead>
          <tbody>{sched.data?.map?.((s) => (
            <tr key={s.id}><td>{s.name}</td><td>{hhmm(s.start_time)}–{hhmm(s.end_time)}</td><td>{s.working_days?.map((d) => DAYS[d]).join(", ")}</td><td>{s.grace_minutes} min</td></tr>
          ))}</tbody></table>
          {sched.data?.length === 0 && <Empty>No schedule has been assigned to you yet.</Empty>}
        </div>
      )}

      {tab === "leave" && (
        <div className="split">
          <form className="card" onSubmit={submit}>
            <h3>Request leave</h3>
            <p className="muted">One request can cover a range of days, but days cannot overlap another request.</p>
            {msg && <Notice kind={msg.kind}>{msg.text}</Notice>}
            <div className="form-grid">
              <div className="full"><Field label="Leave type"><select value={form.leave_type_id} onChange={(e) => setForm({ ...form, leave_type_id: e.target.value })} required><option value="">Select…</option>{types.data?.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</select></Field></div>
              <Field label="From"><input type="date" min={isoToday()} value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} required /></Field>
              <Field label="To"><input type="date" min={form.start_date} value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} required /></Field>
              <div className="full"><Field label="Reason"><textarea value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} /></Field></div>
            </div>
            <div className="form-actions"><button className="primary">Submit request</button></div>
          </form>
          <div>
            <h3 style={{ marginBottom: 10 }}>My requests</h3>
            <div className="table-wrap"><table>
              <thead><tr><th>Dates</th><th>Type</th><th>Status</th><th></th></tr></thead>
              <tbody>{leave.data?.map((l) => (
                <tr key={l.id}><td>{fmtDate(l.start_date)} – {fmtDate(l.end_date)}</td><td>{l.leave_type_name}</td>
                  <td><Badge value={l.status} />{l.review_note && <div className="muted">{l.review_note}</div>}</td>
                  <td>{l.status === "pending" && <button className="small" onClick={() => cancel(l.id)}>Cancel</button>}</td></tr>
              ))}</tbody></table>
              {leave.data?.length === 0 && <Empty>No leave requests yet.</Empty>}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
