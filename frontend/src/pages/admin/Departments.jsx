import { useState } from "react";
import { Empty, Field, Modal, Notice, PageHead, Badge } from "../../components/ui";
import api, { errMsg } from "../../services/api";
import { useApi } from "../../utils/hooks";

const blank = { name: "", code: "", description: "", head_id: "", is_active: true };

export default function Departments() {
  const { data, error, reload } = useApi("/departments");
  const emps = useApi("/employees");
  const [form, setForm] = useState(null);
  const [err, setErr] = useState("");

  const save = async (e) => {
    e.preventDefault();
    setErr("");
    const body = { ...form, head_id: form.head_id ? Number(form.head_id) : null };
    try {
      form.id ? await api.put(`/departments/${form.id}`, body) : await api.post("/departments", body);
      setForm(null);
      reload();
    } catch (x) { setErr(errMsg(x)); }
  };
  const deactivate = async (d) => {
    if (!confirm(`Deactivate ${d.name}?`)) return;
    try { await api.delete(`/departments/${d.id}`); reload(); } catch (x) { alert(errMsg(x)); }
  };
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });

  return (
    <>
      <PageHead title="Departments"><button className="primary" onClick={() => { setErr(""); setForm(blank); }}>Add department</button></PageHead>
      <Notice>{error}</Notice>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Name</th><th>Code</th><th>Head</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {data?.map((d) => (
              <tr key={d.id}>
                <td>{d.name}</td><td>{d.code}</td>
                <td>{emps.data?.find((e) => e.id === d.head_id)?.full_name || "—"}</td>
                <td><Badge value={d.is_active ? "active" : "inactive"} /></td>
                <td className="row-actions">
                  <button className="small" onClick={() => { setErr(""); setForm({ ...d, head_id: d.head_id || "", description: d.description || "" }); }}>Edit</button>
                  {d.is_active && <button className="small danger" onClick={() => deactivate(d)}>Deactivate</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {data?.length === 0 && <Empty>No departments yet. Add the first one to start registering employees.</Empty>}
      </div>
      {form && (
        <Modal title={form.id ? "Edit department" : "Add department"} onClose={() => setForm(null)}>
          <form onSubmit={save}>
            <Notice>{err}</Notice>
            <div className="form-grid">
              <Field label="Name"><input value={form.name} onChange={set("name")} required minLength={2} /></Field>
              <Field label="Code"><input value={form.code} onChange={set("code")} required minLength={2} /></Field>
              <Field label="Department head (supervisor)">
                <select value={form.head_id} onChange={set("head_id")}>
                  <option value="">None</option>
                  {emps.data?.map((e) => <option key={e.id} value={e.id}>{e.full_name} ({e.employee_code})</option>)}
                </select>
              </Field>
              <label className="check"><input type="checkbox" checked={form.is_active} onChange={set("is_active")} />Active</label>
              <div className="full"><Field label="Description"><textarea value={form.description} onChange={set("description")} /></Field></div>
            </div>
            <div className="form-actions"><button type="button" onClick={() => setForm(null)}>Cancel</button><button className="primary">Save department</button></div>
          </form>
        </Modal>
      )}
    </>
  );
}
