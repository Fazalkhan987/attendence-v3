import { useEffect } from "react";
import { label } from "../utils/format";

export function Modal({ title, onClose, children, wide }) {
  useEffect(() => {
    const h = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [onClose]);
  return (
    <div className="overlay" onMouseDown={onClose}>
      <div className={`modal ${wide ? "wide" : ""}`} role="dialog" aria-modal="true" aria-label={title} onMouseDown={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>{title}</h3>
          <button className="icon" onClick={onClose} aria-label="Close">×</button>
        </div>
        {children}
      </div>
    </div>
  );
}

export const Badge = ({ value }) => <span className={`badge b-${value}`}>{label(value)}</span>;

export const Notice = ({ kind = "error", children }) =>
  children ? <div className={`notice ${kind}`} role={kind === "error" ? "alert" : "status"}>{children}</div> : null;

export const Empty = ({ children }) => <div className="empty">{children}</div>;

export const Field = ({ label: l, children, hint }) => (
  <label className="field">
    <span>{l}</span>
    {children}
    {hint && <small>{hint}</small>}
  </label>
);

export const PageHead = ({ title, children }) => (
  <div className="page-head">
    <h1>{title}</h1>
    <div className="actions">{children}</div>
  </div>
);
