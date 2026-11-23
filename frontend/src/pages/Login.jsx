import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { Field, Notice } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { errMsg } from "../services/api";

export default function Login() {
  const { me, login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (me) return <Navigate to={me.user.role === "employee" ? "/me" : "/admin"} replace />;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const m = await login(email, password);
      nav(m?.user.role === "employee" ? "/me" : "/admin");
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login">
      <div className="login-art">
        <h2>Attendance that records itself.</h2>
        <p>Cameras recognise registered employees, the server applies each schedule, and every correction is kept on the record.</p>
      </div>
      <div className="login-form">
        <form onSubmit={submit}>
          <h1>Sign in</h1>
          <Notice>{error}</Notice>
          <Field label="Email"><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus /></Field>
          <Field label="Password"><input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required /></Field>
          <button className="primary" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
        </form>
      </div>
    </div>
  );
}
