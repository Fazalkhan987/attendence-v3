import { useState } from "react";
import { Badge, Empty, Field, Modal, Notice, PageHead } from "../../components/ui";
import { useAuth } from "../../context/AuthContext";
import api, { errMsg } from "../../services/api";
import { DAYS, fmtDate, hhmm, isoToday } from "../../utils/format";
import { useApi } from "../../utils/hooks";

const blank = { name: "", department_id: "", camera_id: "", start_time: "09:00", end_time: "17:00", working_days: [0, 1, 2, 3, 4],
  grace_minutes: 20, checkin_early_minutes: 60, checkout_before_minutes: 30, checkout_after_minutes: 60, is_active: true };

export default function Schedules() {
  const { me } = useAuth();
  const isAdmin = me.user.role === "admin";
  const { data, error, reload } = useApi("/schedules");
  const deps = useApi("/departments");
  const cams = useApi("/cameras");
  const [form, setForm] = useState(null);
  const [err, setErr] = useState("");
  const [assign, setAssign] = useState(null);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  const toggleDay = (d) => setForm({ ...form, working_days: form.working_days.includes(d) ? form.working_days.filter((x) => x !== d) : [...form.working_days, d].sort() });

  const save = async (e) => {
    e.preventDefault();
    setErr("");
    const num = ["grace_minutes", "checkin_early_minutes", "checkout_before_minutes", "checkout_after_minutes"];
    const body = { ...form, department_id: Number(form.department_id), camera_id: form.camera_id ? Number(form.camera_id) : null };
    num.forEach((k) => (body[k] = Number(body[k])));
    ["department_name", "camera_code", "id"].forEach((k) => delete body[k]);
    try {
      form.id ? await api.put(`/schedules/${form.id}`, body) : await api.post("/schedules", body);
      setForm(null); reload();
    } catch (x) { setErr(errMsg(x)); }
  };
  const deactivate = async (s) => { if (confirm(`Deactivate ${s.name}?`)) { await api.delete(`/schedules/${s.id}`); reload(); } };

  return (
    <>
      <PageHead title="Work schedules">
        {isAdmin && <button className="primary" onClick={() => { setErr(""); setForm(blank); }}>Add schedule</button>}
      </PageHead>
      <p className="muted">Each schedule is one working session. Assign an employee to several non-overlapping schedules (for example Morning and Afternoon) to support multiple sessions per day.</p>
      <Notice>{error}</Notice>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Session</th><th>Department</th><th>Hours</th><th>Days</th><th>Grace</th><th>Camera</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {data?.map((s) => (
              <tr key={s.id}>
                <td>{s.name}</td><td>{s.department_name}</td><td>{hhmm(s.start_time)}–{hhmm(s.end_time)}</td>
                <td>{s.working_days.map((d) => DAYS[d]).join(", ")}</td><td>{s.grace_minutes} min</td>
                <td>{s.camera_code || "Any"}</td><td><Badge value={s.is_active ? "active" : "inactive"} /></td>
                <td className="row-actions">
                  <button className="small" onClick={() => setAssign(s)}>Employees</button>
                  {isAdmin && <button className="small" onClick={() => { setErr(""); setForm({ ...s, camera_id: s.camera_id || "", start_time: hhmm(s.start_time), end_time: hhmm(s.end_time) }); }}>Edit</button>}
                  {isAdmin && s.is_active && <button className="small danger" onClick={() => deactivate(s)}>Deactivate</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {data?.length === 0 && <Empty>No schedules yet.</Empty>}
      </div>

      {form && (
        <Modal title={form.id ? "Edit schedule" : "Add schedule"} wide onClose={() => setForm(null)}>
          <form onSubmit={save}>
            <Notice>{err}</Notice>
            <div className="form-grid">
              <Field label="Session name"><input value={form.name} onChange={set("name")} required placeholder="Morning shift" /></Field>
              <Field label="Department">
                <select value={form.department_id} onChange={set("department_id")} required>
                  <option value="">Select…</option>{deps.data?.filter((d) => d.is_active).map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                </select>
              </Field>
              <Field label="Start time"><input type="time" value={form.start_time} onChange={set("start_time")} required /></Field>
              <Field label="End time"><input type="time" value={form.end_time} onChange={set("end_time")} required /></Field>
              <div className="full"><Field label="Working days">
                <div className="days">{DAYS.map((d, i) => (
                  <label key={d} className={form.working_days.includes(i) ? "on" : ""}><input type="checkbox" checked={form.working_days.includes(i)} onChange={() => toggleDay(i)} />{d}</label>
                ))}</div></Field></div>
              <Field label="Grace period (min)" hint="Check-in up to this long after start counts as present"><input type="number" min="0" value={form.grace_minutes} onChange={set("grace_minutes")} /></Field>
              <Field label="Check-in opens (min before start)"><input type="number" min="0" value={form.checkin_early_minutes} onChange={set("checkin_early_minutes")} /></Field>
              <Field label="Check-out opens (min before end)"><input type="number" min="0" value={form.checkout_before_minutes} onChange={set("checkout_before_minutes")} /></Field>
              <Field label="Check-out closes (min after end)"><input type="number" min="0" value={form.checkout_after_minutes} onChange={set("checkout_after_minutes")} /></Field>
              <Field label="Check-in camera / location" hint="Leave empty to accept any entry camera">
                <select value={form.camera_id} onChange={set("camera_id")}><option value="">Any camera</option>{cams.data?.map?.((c) => c.camera_code && <option key={c.id} value={c.id}>{c.camera_code} — {c.name}</option>)}</select>
              </Field>
              <label className="check"><input type="checkbox" checked={form.is_active} onChange={set("is_active")} />Active</label>
            </div>
            <div className="form-actions"><button type="button" onClick={() => setForm(null)}>Cancel</button><button className="primary">Save schedule</button></div>
          </form>
        </Modal>
      )}
      {assign && <AssignModal schedule={assign} isAdmin={isAdmin} onClose={() => setAssign(null)} />}
    </>
  );
}

function AssignModal({ schedule, isAdmin, onClose }) {
  const list = useApi(`/schedules/${schedule.id}/assignments`);
  const emps = useApi("/employees", { department_id: schedule.department_id, status: "active" });
  const [picked, setPicked] = useState([]);
  const [from, setFrom] = useState(isoToday());
  const [to, setTo] = useState("");
  const [msg, setMsg] = useState(null);

  const add = async () => {
    setMsg(null);
    try {
      await api.post(`/schedules/${schedule.id}/assignments`, { employee_ids: picked, effective_from: from, effective_to: to || null });
      setPicked([]); list.reload();
      setMsg({ kind: "ok", text: "Employees assigned." });
    } catch (x) { setMsg({ kind: "error", text: errMsg(x) }); }
  };
  const remove = async (id) => { await api.delete(`/schedules/assignments/${id}`); list.reload(); };
  const assigned = new Set(list.data?.map((a) => a.employee_id));

  return (
    <Modal title={`${schedule.name} — employees`} wide onClose={onClose}>
      {msg && <Notice kind={msg.kind}>{msg.text}</Notice>}
      <div className="table-wrap" style={{ marginBottom: 16 }}>
        <table>
          <thead><tr><th>Employee</th><th>From</th><th>To</th><th></th></tr></thead>
          <tbody>
            {list.data?.map((a) => (
              <tr key={a.id}><td>{a.employee_name} ({a.employee_code})</td><td>{fmtDate(a.effective_from)}</td><td>{a.effective_to ? fmtDate(a.effective_to) : "Open"}</td>
                <td>{isAdmin && <button className="small danger" onClick={() => remove(a.id)}>Remove</button>}</td></tr>
            ))}
          </tbody>
        </table>
        {list.data?.length === 0 && <Empty>Nobody is assigned yet.</Empty>}
      </div>
      {isAdmin && (
        <fieldset>
          <legend>Assign employees from this department</legend>
          <div style={{ maxHeight: 180, overflow: "auto" }}>
            {emps.data?.filter((e) => !assigned.has(e.id)).map((e) => (
              <label key={e.id} className="check"><input type="checkbox" checked={picked.includes(e.id)} onChange={() => setPicked(picked.includes(e.id) ? picked.filter((x) => x !== e.id) : [...picked, e.id])} />{e.full_name} ({e.employee_code})</label>
            ))}
          </div>
          <div className="form-grid" style={{ marginTop: 10 }}>
            <Field label="Effective from"><input type="date" value={from} onChange={(e) => setFrom(e.target.value)} /></Field>
            <Field label="Effective to (optional)"><input type="date" value={to} onChange={(e) => setTo(e.target.value)} /></Field>
          </div>
          <div className="form-actions"><button className="primary" disabled={!picked.length} onClick={add}>Assign {picked.length || ""} selected</button></div>
        </fieldset>
      )}
    </Modal>
  );
}
