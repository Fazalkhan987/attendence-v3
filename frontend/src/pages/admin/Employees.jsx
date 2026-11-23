import { useState } from "react";
import { Badge, Empty, Field, Modal, Notice, PageHead } from "../../components/ui";
import WebcamCapture from "../../components/WebcamCapture";
import { useAuth } from "../../context/AuthContext";
import api, { errMsg } from "../../services/api";
import { fmtDate } from "../../utils/format";
import { useApi } from "../../utils/hooks";
import { isoToday } from "../../utils/format";

const blank = () => ({
  employee_code: "", full_name: "", email: "", phone: "", address: "", photo: "", department_id: "",
  designation: "", joining_date: isoToday(), status: "active", supervisor_id: "", face_consent: false,
  createLogin: true, login_email: "", password: "", role: "employee", account_active: true,
});

export default function Employees() {
  const { me } = useAuth();
  const isAdmin = me.user.role === "admin";
  const [q, setQ] = useState("");
  const [dept, setDept] = useState("");
  const { data, error, reload } = useApi("/employees", { q, department_id: dept });
  const deps = useApi("/departments");
  const all = useApi("/employees");
  const [form, setForm] = useState(null);
  const [err, setErr] = useState("");
  const [enroll, setEnroll] = useState(null);
  const [enrollMsg, setEnrollMsg] = useState(null);
  const [busy, setBusy] = useState(false);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  const edit = (e) => { setErr(""); setForm({ ...blank(), ...e, phone: e.phone || "", address: e.address || "", photo: e.photo || "",
    supervisor_id: e.supervisor_id || "", createLogin: false, login_email: "", password: "", role: e.account_role || "employee",
    account_active: e.account_active ?? true, hasAccount: !!e.user_id }); };

  const onPhoto = (ev) => {
    const f = ev.target.files?.[0];
    if (!f) return;
    if (f.size > 400_000) return setErr("Photo must be under 400 KB.");
    const r = new FileReader();
    r.onload = () => setForm((p) => ({ ...p, photo: r.result }));
    r.readAsDataURL(f);
  };

  const save = async (ev) => {
    ev.preventDefault();
    setErr("");
    const base = {
      full_name: form.full_name, email: form.email, phone: form.phone || null, address: form.address || null,
      photo: form.photo || null, department_id: Number(form.department_id), designation: form.designation,
      joining_date: form.joining_date, status: form.status, supervisor_id: form.supervisor_id ? Number(form.supervisor_id) : null,
      face_consent: form.face_consent,
    };
    try {
      if (form.id) {
        const account = {};
        if (form.password) account.password = form.password;
        if (form.login_email) account.email = form.login_email;
        if (isAdmin) { account.role = form.role; account.is_active = form.account_active; }
        const body = { ...base };
        if (form.hasAccount || form.password) body.account = account;
        await api.put(`/employees/${form.id}`, body);
      } else {
        const body = { ...base, employee_code: form.employee_code };
        if (form.createLogin) body.account = { email: form.login_email || form.email, password: form.password, role: form.role, is_active: true };
        await api.post("/employees", body);
      }
      setForm(null);
      reload(); all.reload();
    } catch (x) { setErr(errMsg(x)); }
  };

  const deactivate = async (e) => {
    if (!confirm(`Deactivate ${e.full_name}? Their login and face data will be removed.`)) return;
    try { await api.delete(`/employees/${e.id}`); reload(); } catch (x) { alert(errMsg(x)); }
  };

  const doEnroll = async (images) => {
    setBusy(true); setEnrollMsg(null);
    try {
      const { data: r } = await api.post(`/employees/${enroll.id}/face/enroll`, { images });
      setEnrollMsg({ kind: "ok", text: `Enrolled ${r.samples_stored} samples.${r.rejected.length ? ` ${r.rejected.length} rejected (${[...new Set(r.rejected)].join(", ")}).` : ""}` });
      reload();
    } catch (x) { setEnrollMsg({ kind: "error", text: errMsg(x) }); }
    finally { setBusy(false); }
  };

  const removeFace = async (e) => {
    if (!confirm(`Delete stored face data for ${e.full_name}?`)) return;
    await api.delete(`/employees/${e.id}/face`);
    reload();
  };

  return (
    <>
      <PageHead title="Employees">
        {isAdmin && <button className="primary" onClick={() => { setErr(""); setForm(blank()); }}>Add employee</button>}
      </PageHead>
      <div className="filters">
        <Field label="Search"><input placeholder="Name, ID or email" value={q} onChange={(e) => setQ(e.target.value)} /></Field>
        <Field label="Department">
          <select value={dept} onChange={(e) => setDept(e.target.value)}>
            <option value="">All</option>{deps.data?.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </Field>
      </div>
      <Notice>{error}</Notice>
      <div className="table-wrap">
        <table>
          <thead><tr><th>ID</th><th>Name</th><th>Department</th><th>Designation</th><th>Joined</th><th>Status</th><th>Face</th><th></th></tr></thead>
          <tbody>
            {data?.map((e) => (
              <tr key={e.id}>
                <td>{e.employee_code}</td><td>{e.full_name}<div className="muted">{e.email}</div></td>
                <td>{e.department_name}</td><td>{e.designation}</td><td>{fmtDate(e.joining_date)}</td>
                <td><Badge value={e.status} /></td>
                <td>{e.face_samples > 0 ? <span className="badge b-present">{e.face_samples} samples</span> : <span className="badge">Not enrolled</span>}</td>
                <td className="row-actions">
                  {isAdmin && <>
                    <button className="small" onClick={() => edit(e)}>Edit</button>
                    <button className="small" disabled={!e.face_consent || e.status !== "active"} title={e.face_consent ? "" : "Biometric consent is required"} onClick={() => { setEnrollMsg(null); setEnroll(e); }}>Enroll face</button>
                    {e.face_samples > 0 && <button className="small danger" onClick={() => removeFace(e)}>Delete face</button>}
                    {e.status === "active" && <button className="small danger" onClick={() => deactivate(e)}>Deactivate</button>}
                  </>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {data?.length === 0 && <Empty>No employees match. {isAdmin ? "Add an employee to get started." : ""}</Empty>}
      </div>

      {form && (
        <Modal title={form.id ? `Edit ${form.employee_code}` : "Add employee"} wide onClose={() => setForm(null)}>
          <form onSubmit={save}>
            <Notice>{err}</Notice>
            <div className="form-grid">
              <Field label="Employee ID"><input value={form.employee_code} onChange={set("employee_code")} required disabled={!!form.id} pattern="[A-Za-z0-9._-]+" /></Field>
              <Field label="Full name"><input value={form.full_name} onChange={set("full_name")} required /></Field>
              <Field label="Email"><input type="email" value={form.email} onChange={set("email")} required /></Field>
              <Field label="Phone"><input value={form.phone} onChange={set("phone")} /></Field>
              <div className="full"><Field label="Address"><input value={form.address} onChange={set("address")} /></Field></div>
              <Field label="Department">
                <select value={form.department_id} onChange={set("department_id")} required>
                  <option value="">Select…</option>{deps.data?.filter((d) => d.is_active).map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                </select>
              </Field>
              <Field label="Designation"><input value={form.designation} onChange={set("designation")} required /></Field>
              <Field label="Joining date"><input type="date" value={form.joining_date} onChange={set("joining_date")} required /></Field>
              <Field label="Employment status">
                <select value={form.status} onChange={set("status")}>{["active", "inactive", "suspended", "terminated"].map((s) => <option key={s}>{s}</option>)}</select>
              </Field>
              <Field label="Supervisor">
                <select value={form.supervisor_id} onChange={set("supervisor_id")}>
                  <option value="">None</option>{all.data?.filter((e) => e.id !== form.id).map((e) => <option key={e.id} value={e.id}>{e.full_name}</option>)}
                </select>
              </Field>
              <Field label="Profile photo (optional)" hint="JPEG or PNG, under 400 KB"><input type="file" accept="image/*" onChange={onPhoto} /></Field>
              <label className="check full"><input type="checkbox" checked={form.face_consent} onChange={set("face_consent")} />
                <span>The employee has given explicit consent to the collection and storage of their facial biometric data for attendance. They can withdraw consent at any time, which deletes their face data.</span></label>
            </div>
            <fieldset>
              <legend>System account</legend>
              {!form.id && <label className="check"><input type="checkbox" checked={form.createLogin} onChange={set("createLogin")} />Create a login for this employee</label>}
              {(form.createLogin || form.id) && (
                <div className="form-grid" style={{ marginTop: 10 }}>
                  <Field label="Login email" hint={form.id ? "Leave empty to keep" : "Defaults to employee email"}><input type="email" value={form.login_email} onChange={set("login_email")} /></Field>
                  <Field label={form.id ? "New password" : "Password"} hint="At least 8 characters"><input type="password" value={form.password} onChange={set("password")} minLength={8} required={!form.id && form.createLogin} autoComplete="new-password" /></Field>
                  {isAdmin && <Field label="System role"><select value={form.role} onChange={set("role")}><option>employee</option><option>supervisor</option><option>admin</option></select></Field>}
                  {form.id && isAdmin && <label className="check"><input type="checkbox" checked={form.account_active} onChange={set("account_active")} />Account active</label>}
                </div>
              )}
            </fieldset>
            <div className="form-actions"><button type="button" onClick={() => setForm(null)}>Cancel</button><button className="primary">Save employee</button></div>
          </form>
        </Modal>
      )}

      {enroll && (
        <Modal title={`Enroll face — ${enroll.full_name}`} onClose={() => setEnroll(null)}>
          {enrollMsg && <Notice kind={enrollMsg.kind}>{enrollMsg.text}</Notice>}
          <WebcamCapture count={8} onDone={doEnroll} disabled={busy} />
          {busy && <p className="muted">Processing samples…</p>}
        </Modal>
      )}
    </>
  );
}
