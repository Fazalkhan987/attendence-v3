import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const ADMIN_NAV = [
  ["/admin", "Dashboard", ["admin", "supervisor"], true],
  ["/admin/attendance", "Attendance", ["admin", "supervisor"]],
  ["/admin/leave", "Leave requests", ["admin", "supervisor"]],
  ["/admin/employees", "Employees", ["admin", "supervisor"]],
  ["/admin/departments", "Departments", ["admin"]],
  ["/admin/schedules", "Schedules", ["admin", "supervisor"]],
  ["/admin/cameras", "Cameras", ["admin"]],
  ["/admin/reports", "Reports", ["admin", "supervisor"]],
  ["/admin/activity", "System activity", ["admin"]],
];

export default function Layout({ mode }) {
  const { me, logout } = useAuth();
  const nav = useNavigate();
  const items = mode === "admin"
    ? ADMIN_NAV.filter((n) => n[2].includes(me.user.role))
    : [["/me", "My attendance", null, true]];
  return (
    <div className="shell">
      <aside className="rail">
        <div className="brand">Smart<span>Attendance</span></div>
        <nav>
          {items.map(([to, text, , end]) => (
            <NavLink key={to} to={to} end={!!end}>{text}</NavLink>
          ))}
        </nav>
        <div className="rail-foot">
          <div className="who">{me.employee?.full_name || me.user.email}</div>
          <div className="role">{me.user.role}</div>
          <button className="ghost" onClick={() => { logout(); nav("/login"); }}>Sign out</button>
        </div>
      </aside>
      <main className="content"><Outlet /></main>
    </div>
  );
}
