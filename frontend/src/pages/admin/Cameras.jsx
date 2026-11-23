import { useState } from "react";
import { Badge, Empty, Field, Modal, Notice, PageHead } from "../../components/ui";
import api, { errMsg } from "../../services/api";
import { useApi } from "../../utils/hooks";

const blank = { camera_code: "", name: "", location: "", department_id: "", camera_type: "both", stream_url: "", is_active: true };

export default function Cameras() {
  const { data, error, reload } = useApi("/cameras");
  const deps = useApi("/departments");
  const [form, setForm] = useState(null);
  const [err, setErr] = useState("");
  const [secret, setSecret] = useState(null);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  const save = async (e) => {
    e.preventDefault(); setErr("");
    const body = { ...form, department_id: form.department_id ? Number(form.department_id) : null, stream_url: form.stream_url || null, location: form.location || null };
    try {
      if (form.id) { await api.put(`/cameras/${form.id}`, body); }
      else { const { data: c } = await api.post("/cameras", body); setSecret(c); }
      setForm(null); reload();
    } catch (x) { setErr(errMsg(x)); }
  };
  const rotate = async (c) => {
    if (!confirm(`Rotate the secret for ${c.camera_code}? The face engine must be updated.`)) return;
    const { data: r } = await api.post(`/cameras/${c.id}/rotate-secret`); setSecret(r);
  };
  const toggle = async (c) => { await api.put(`/cameras/${c.id}`, { is_active: !c.is_active }); reload(); };

  return (
    <>
      <PageHead title="Cameras"><button className="primary" onClick={() => { setErr(""); setForm(blank); }}>Add camera</button></PageHead>
      <Notice>{error}</Notice>
      {secret && (
        <Notice kind="warn">
          Secret for <b>{secret.camera_code}</b> — copy it now into the face engine’s <code>CAMERA_SECRET</code>. It is not shown again.
          <code className="secret">{secret.secret}</code>
          <button className="small" style={{ marginTop: 8 }} onClick={() => setSecret(null)}>I have saved it</button>
        </Notice>
      )}
      <div className="table-wrap">
        <table>
          <thead><tr><th>Camera ID</th><th>Name</th><th>Location</th><th>Department</th><th>Role</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {data?.map((c) => (
              <tr key={c.id}>
                <td>{c.camera_code}</td><td>{c.name}</td><td>{c.location || "—"}</td>
                <td>{deps.data?.find((d) => d.id === c.department_id)?.name || "All"}</td>
                <td>{c.camera_type}</td><td><Badge value={c.is_active ? "active" : "inactive"} /></td>
                <td className="row-actions">
                  <button className="small" onClick={() => { setErr(""); setForm({ ...c, department_id: c.department_id || "", location: c.location || "", stream_url: c.stream_url || "" }); }}>Edit</button>
                  <button className="small" onClick={() => toggle(c)}>{c.is_active ? "Disable" : "Enable"}</button>
                  <button className="small" onClick={() => rotate(c)}>Rotate secret</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {data?.length === 0 && <Empty>No cameras registered. Add one to connect a face engine.</Empty>}
      </div>
      {form && (
        <Modal title={form.id ? "Edit camera" : "Add camera"} onClose={() => setForm(null)}>
          <form onSubmit={save}>
            <Notice>{err}</Notice>
            <div className="form-grid">
              <Field label="Camera ID"><input value={form.camera_code} onChange={set("camera_code")} required disabled={!!form.id} pattern="[A-Za-z0-9._-]+" /></Field>
              <Field label="Name"><input value={form.name} onChange={set("name")} required /></Field>
              <Field label="Location"><input value={form.location} onChange={set("location")} placeholder="Main entrance" /></Field>
              <Field label="Department" hint="Only this department’s employees are recognised"><select value={form.department_id} onChange={set("department_id")}><option value="">All departments</option>{deps.data?.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}</select></Field>
              <Field label="Used for"><select value={form.camera_type} onChange={set("camera_type")}><option value="entry">Check-in only</option><option value="exit">Check-out only</option><option value="both">Check-in and check-out</option></select></Field>
              <Field label="Stream URL (optional)"><input value={form.stream_url} onChange={set("stream_url")} placeholder="rtsp://…" /></Field>
              <label className="check"><input type="checkbox" checked={form.is_active} onChange={set("is_active")} />Active</label>
            </div>
            <div className="form-actions"><button type="button" onClick={() => setForm(null)}>Cancel</button><button className="primary">Save camera</button></div>
          </form>
        </Modal>
      )}
    </>
  );
}
