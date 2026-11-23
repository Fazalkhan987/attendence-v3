import { useState } from "react";
import { Empty, Field, Notice, PageHead } from "../../components/ui";
import api, { errMsg } from "../../services/api";
import { fmtDate, isoToday, minutes } from "../../utils/format";
import { useApi } from "../../utils/hooks";

export default function Reports() {
  const [f, setF] = useState({ date_from: isoToday().slice(0, 8) + "01", date_to: isoToday(), department_id: "" });
  const { data, error } = useApi("/reports/summary", f);
  const deps = useApi("/departments");
  const [err, setErr] = useState("");
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const download = async () => {
    try {
      const params = Object.fromEntries(Object.entries(f).filter(([, v]) => v));
      const r = await api.get("/reports/attendance.csv", { params, responseType: "blob" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(r.data);
      a.download = `attendance_${f.date_from}_${f.date_to}.csv`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (x) { setErr(errMsg(x)); }
  };

  const cols = ["present", "late", "half_day", "incomplete", "absent", "on_leave", "excused"];
  return (
    <>
      <PageHead title="Reports">
        <button onClick={() => window.print()}>Print</button>
        <button className="primary" onClick={download}>Download CSV</button>
      </PageHead>
      <div className="filters">
        <Field label="From"><input type="date" value={f.date_from} onChange={set("date_from")} /></Field>
        <Field label="To"><input type="date" value={f.date_to} onChange={set("date_to")} /></Field>
        <Field label="Department"><select value={f.department_id} onChange={set("department_id")}><option value="">All</option>{deps.data?.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}</select></Field>
      </div>
      <Notice>{error || err}</Notice>
      <p className="muted">Sessions counted per status between {data && fmtDate(data.date_from)} and {data && fmtDate(data.date_to)}.</p>
      <div className="table-wrap">
        <table>
          <thead><tr><th>ID</th><th>Employee</th>{cols.map((c) => <th key={c}>{c.replace("_", " ")}</th>)}<th>Hours worked</th></tr></thead>
          <tbody>
            {data?.rows.map((r) => (
              <tr key={r.employee_id}><td>{r.employee_code}</td><td>{r.employee_name}</td>{cols.map((c) => <td key={c}>{r[c]}</td>)}<td>{minutes(r.worked_minutes)}</td></tr>
            ))}
          </tbody>
        </table>
        {data?.rows.length === 0 && <Empty>No attendance in this period.</Empty>}
      </div>
    </>
  );
}
