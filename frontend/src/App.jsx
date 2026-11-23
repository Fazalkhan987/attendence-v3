import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { useAuth } from "./context/AuthContext";
import Login from "./pages/Login";
import Dashboard from "./pages/admin/Dashboard";
import Departments from "./pages/admin/Departments";
import Employees from "./pages/admin/Employees";
import Schedules from "./pages/admin/Schedules";
import Cameras from "./pages/admin/Cameras";
import Attendance from "./pages/admin/Attendance";
import LeaveRequests from "./pages/admin/LeaveRequests";
import Reports from "./pages/admin/Reports";
import Activity from "./pages/admin/Activity";
import MyDashboard from "./pages/employee/MyDashboard";

const home = (role) => (role === "employee" ? "/me" : "/admin");

function Guard({ roles, children }) {
  const { me, loading } = useAuth();
  if (loading) return <div className="boot">Loading…</div>;
  if (!me) return <Navigate to="/login" replace />;
  if (!roles.includes(me.user.role)) return <Navigate to={home(me.user.role)} replace />;
  return children;
}

export default function App() {
  const { me, loading } = useAuth();
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/admin" element={<Guard roles={["admin", "supervisor"]}><Layout mode="admin" /></Guard>}>
        <Route index element={<Dashboard />} />
        <Route path="attendance" element={<Attendance />} />
        <Route path="leave" element={<LeaveRequests />} />
        <Route path="employees" element={<Employees />} />
        <Route path="departments" element={<Guard roles={["admin"]}><Departments /></Guard>} />
        <Route path="schedules" element={<Schedules />} />
        <Route path="cameras" element={<Guard roles={["admin"]}><Cameras /></Guard>} />
        <Route path="reports" element={<Reports />} />
        <Route path="activity" element={<Guard roles={["admin"]}><Activity /></Guard>} />
      </Route>
      <Route path="/me" element={<Guard roles={["employee"]}><Layout mode="employee" /></Guard>}>
        <Route index element={<MyDashboard />} />
      </Route>
      <Route path="*" element={loading ? null : <Navigate to={me ? home(me.user.role) : "/login"} replace />} />
    </Routes>
  );
}
