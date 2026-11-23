import { useState } from "react";
import { Badge, Empty, Field, Modal, Notice, PageHead } from "../../components/ui";
import { useAuth } from "../../context/AuthContext";
import api, { errMsg } from "../../services/api";
import { fmtDate } from "../../utils/format";
import { useApi } from "../../utils/hooks";

export default function LeaveRequests() {
  const { me } = useAuth();
  const [status, setStatus] = useState("pending");
  const { data, error, reload } = useApi("/leave", { status });
  const types = useApi("/leave/types");
  const [review, setReview] = useState(null);
  const [err, setErr] = useState("");
  const [newType, setNewType] = useState("");

  const submit = async (decision) => {
    setErr("");
    try { await api.patch(`/leave/${review.id}/review`, { decision, note: review.note || null }); setReview(null); reload(); }
    catch (x) { setErr(errMsg(x)); }
  };
  const addType = async (e) => {
    e.preventDefault();
    try { await api.post("/leave/types", { name: newType }); setNewType(""); types.reload(); } catch (x) { alert(errMsg(x)); }
  };

  return (
    <>
      <PageHead title="Leave requests">
        <Field label="Status"><select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All</option>{["pending", "approved", "rejected", "cancelled"].map((s) => <option key={s}>{s}</option>)}</select></Field>
      </PageHead>
      <Notice>{error}</Notice>
      <div className="table-wrap">
        <table>
          <thead><tr><th>Employee</th><th>Type</th><th>From</th><th>To</th><th>Reason</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {data?.map((l) => (
              <tr key={l.id}>
                <td>{l.employee_name}<div className="muted">{l.employee_code}</div></td><td>{l.leave_type_name}</td>
                <td>{fmtDate(l.start_date)}</td><td>{fmtDate(l.end_date)}</td><td className="wrap">{l.reason || "—"}{l.review_note && <div className="muted">Note: {l.review_note}</div>}</td>
                <td><Badge value={l.status} /></td>
                <td>{l.status === "pending" && <button className="small" onClick={() => { setErr(""); setReview({ ...l, note: "" }); }}>Review</button>}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {data?.length === 0 && <Empty>No leave requests {status ? `with status “${status}”` : ""}.</Empty>}
      </div>
      {me.user.role === "admin" && (
        <form className="card" style={{ marginTop: 22, maxWidth: 520 }} onSubmit={addType}>
          <h3>Leave types</h3>
          <p className="muted">{types.data?.map((t) => t.name).join(", ")}</p>
          <div className="actions"><input placeholder="New leave type" value={newType} onChange={(e) => setNewType(e.target.value)} required minLength={2} style={{ flex: 1 }} /><button className="primary">Add type</button></div>
        </form>
      )}
      {review && (
        <Modal title={`Review leave — ${review.employee_name}`} onClose={() => setReview(null)}>
          <Notice>{err}</Notice>
          <p>{review.leave_type_name}: {fmtDate(review.start_date)} to {fmtDate(review.end_date)}</p>
          <Field label="Note to employee (optional)"><textarea value={review.note} onChange={(e) => setReview({ ...review, note: e.target.value })} /></Field>
          <div className="form-actions"><button className="danger" onClick={() => submit("rejected")}>Reject</button><button className="primary" onClick={() => submit("approved")}>Approve</button></div>
        </Modal>
      )}
    </>
  );
}
