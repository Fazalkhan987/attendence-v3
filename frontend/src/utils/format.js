export const fmtTime = (iso) =>
  iso ? new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—";
export const fmtDateTime = (iso) => (iso ? new Date(iso).toLocaleString() : "—");
export const fmtDate = (d) => (d ? new Date(d + "T00:00:00").toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" }) : "—");
export const hhmm = (t) => (t ? t.slice(0, 5) : "—");
export const minutes = (m) => (m == null ? "—" : `${Math.floor(m / 60)}h ${String(m % 60).padStart(2, "0")}m`);
export const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
export const label = (s) => (s || "").replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
export const isoToday = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);
export const isoDaysAgo = (n) => new Date(Date.now() - n * 86400000 - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);
export const toLocalInput = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
};
export const fromLocalInput = (v) => (v ? new Date(v).toISOString() : null);
