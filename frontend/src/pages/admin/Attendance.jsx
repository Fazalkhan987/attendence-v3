import { useState } from "react";
import { Badge, Empty, Field, Modal, Notice, PageHead } from "../../components/ui";
import api, { errMsg } from "../../services/api";
import { fmtDate, fmtDateTime, fmtTime, fromLocalInput, hhmm, isoDaysAgo, isoToday, label, minutes, toLocalInput } from "../../utils/format";
import { useApi } from "../../utils/hooks";

const STATUSES = ["present", "late", "absent", "on_leave", "half_day", "incomplete", "excused"];

export default function Attendance() {
  const [f, setF] = useState({ date_from: isoDaysAgo(6), date_to: isoToday(), department_id: "", employee_id: "", status: "" });
  const { data, error, reload } = useApi("/attendance", f);
  const deps = useApi("/departments");
  const emps = useApi("/employees");
  const [edit, setEdit] = useState(null);
  const [manual, setManual] = useState(null);
  const [history, setHistory] = useState(null);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  return (
    <>
      <PageHead title="Attendance">
        <button className="primary" onClick={() => setManual({ employee_id: "", schedule_id: "", work_date: isoToday(), status: "present", check_in: "", check_out: "", reason: "" })}>Add manual record</button>
      </PageHead>
      <div className="filters">
        <Field label="From"><input type="date" value={f.date_from} onChange={set("date_from")} /></Field>
        <Field label="To"><input type="date" value={f.date_to} onChange={set("date_to")} /></Field>
        <Field label="Department"><select value={f.department_id} onChange={set("department_id")}><option value="">All</option>{deps.data?.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}</select></Field>
        <Field label="Employee"><select value={f.employee_id} onChange={set("employee_id")}><option value="">All</option>{emps.data?.map((e) => <option key={e.id} value={e.id}>{e.full_name}</option>)}</select></Field>
        <Field label="Status"><select value={f.status} onChange={set("status")}><option value="">All</option>{STATUSES.map((s) => <option key={s} value={s}>{label(s)}</option>)}</select></Field>
      </div>
      <Notice>{error}</Notice>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Date</th><th>Employee</th><th>Session</th><th>Check-in</th><th>Check-out</th><th>Worked</th><th>Status</th><th>Source</th><th></th></tr></thead>
          <tbody>
            {data?.map((a) => (
              <tr key={a.id}>
                <td>{fmtDate(a.work_date)}</td>
                <td>{a.employee_name}<div className="muted">{a.employee_code}</div></td>
                <td>{a.schedule_name}<div className="muted">{hhmm(a.schedule_start)}–{hhmm(a.schedule_end)}</div></td>
                <td>{fmtTime(a.check_in)}</td>
                <td>{fmtTime(a.check_out)} {a.is_early_departure && <span className="badge b-late">Early</span>}</td>
                <td>{minutes(a.worked_minutes)}</td>
                <td><Badge value={a.status} /></td>
                <td>{label(a.source)}</td>
                <td className="row-actions">
                  <button className="small" onClick={() => setEdit({ ...a, check_in: toLocalInput(a.check_in), check_out: toLocalInput(a.check_out), reason: "" })}>Correct</button>
                  <button className="small" onClick={async () => setHistory({ a, rows: (await api.get(`/attendance/${a.id}/corrections`)).data })}>History</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {data?.length === 0 && <Empty>No attendance records for these filters.</Empty>}
      </div>
      {edit && <EditModal rec={edit} onClose={() => setEdit(null)} onSaved={() => { setEdit(null); reload(); }} />}
      {manual && <ManualModal init={manual} emps={emps.data || []} onClose={() => setManual(null)} onSaved={() => { setManual(null); reload(); }} />}
      {history && (
        <Modal title={`Change history — ${history.a.employee_name}, ${fmtDate(history.a.work_date)}`} wide onClose={() => setHistory(null)}>
          {history.rows.length === 0 ? <Empty>No manual changes.</Empty> : (
            <div className="table-wrap"><table>
              <thead><tr><th>When</th><th>By</th><th>Before</th><th>After</th><th>Reason</th></tr></thead>
              <tbody>{history.rows.map((c) => (
                <tr key={c.id}><td>{fmtDateTime(c.changed_at)}</td><td>{c.changed_by_email || "—"}</td>
                  <td className="wrap">{summ(c.previous)}</td><td className="wrap">{summ(c.updated)}</td><td className="wrap">{c.reason}</td></tr>
              ))}</tbody></table></div>
          )}
        </Modal>
      )}
    </>
  );
}

const summ = (s) => (s?.status ? `${label(s.status)} · in ${fmtTime(s.check_in)} · out ${fmtTime(s.check_out)}` : "—");

function EditModal({ rec, onClose, onSaved }) {
  const [v, setV] = useState(rec);
  const [err, setErr] = useState("");
  const set = (k) => (e) => setV({ ...v, [k]: e.target.value });
  const save = async (e) => {
    e.preventDefault(); setErr("");
    try {
      await api.patch(`/attendance/${rec.id}`, { check_in: fromLocalInput(v.check_in), check_out: fromLocalInput(v.check_out), status: v.status, reason: v.reason });
      onSaved();
    } catch (x) { setErr(errMsg(x)); }
  };
  return (
    <Modal title={`Correct attendance — ${rec.employee_name}`} onClose={onClose}>
      <form onSubmit={save}>
        <Notice>{err}</Notice>
        <div className="form-grid">
          <Field label="Check-in"><input type="datetime-local" value={v.check_in} onChange={set("check_in")} /></Field>
          <Field label="Check-out"><input type="datetime-local" value={v.check_out} onChange={set("check_out")} /></Field>
          <div className="full"><Field label="Status"><select value={v.status} onChange={set("status")}>{STATUSES.map((s) => <option key={s} value={s}>{label(s)}</option>)}</select></Field></div>
          <div className="full"><Field label="Reason for the change" hint="Recorded in the audit trail"><textarea value={v.reason} onChange={set("reason")} required minLength={3} /></Field></div>
        </div>
        <div className="form-actions"><button type="button" onClick={onClose}>Cancel</button><button className="primary">Save correction</button></div>
      </form>
    </Modal>
  );
}

function ManualModal({ init, emps, onClose, onSaved }) {
  const [v, setV] = useState(init);
  const [err, setErr] = useState("");
  const sched = useApi(v.employee_id ? `/employees/${v.employee_id}/schedules` : "/schedules");
  const set = (k) => (e) => setV({ ...v, [k]: e.target.value });
  const save = async (e) => {
    e.preventDefault(); setErr("");
    try {
      await api.post("/attendance/manual", { employee_id: Number(v.employee_id), schedule_id: Number(v.schedule_id), work_date: v.work_date, status: v.status,
        check_in: fromLocalInput(v.check_in), check_out: fromLocalInput(v.check_out), reason: v.reason });
      onSaved();
    } catch (x) { setErr(errMsg(x)); }
  };
  return (
    <Modal title="Add manual attendance record" onClose={onClose}>
      <form onSubmit={save}>
        <Notice>{err}</Notice>
        <div className="form-grid">
          <Field label="Employee"><select value={v.employee_id} onChange={(e) => setV({ ...v, employee_id: e.target.value, schedule_id: "" })} required><option value="">Select…</option>{emps.map((e) => <option key={e.id} value={e.id}>{e.full_name} ({e.employee_code})</option>)}</select></Field>
          <Field label="Session"><select value={v.schedule_id} onChange={set("schedule_id")} required disabled={!v.employee_id}><option value="">Select…</option>{v.employee_id && sched.data?.map((s) => <option key={s.id} value={s.id}>{s.name} ({hhmm(s.start_time)}–{hhmm(s.end_time)})</option>)}</select></Field>
          <Field label="Date"><input type="date" value={v.work_date} onChange={set("work_date")} required /></Field>
          <Field label="Status"><select value={v.status} onChange={set("status")}>{STATUSES.map((s) => <option key={s} value={s}>{label(s)}</option>)}</select></Field>
          <Field label="Check-in (optional)"><input type="datetime-local" value={v.check_in} onChange={set("check_in")} /></Field>
          <Field label="Check-out (optional)"><input type="datetime-local" value={v.check_out} onChange={set("check_out")} /></Field>
          <div className="full"><Field label="Reason"><textarea value={v.reason} onChange={set("reason")} required minLength={3} /></Field></div>
        </div>
        <div className="form-actions"><button type="button" onClick={onClose}>Cancel</button><button className="primary">Save record</button></div>
      </form>
    </Modal>
  );
}
