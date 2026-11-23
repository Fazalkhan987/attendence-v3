import { createContext, useContext, useEffect, useState } from "react";
import api from "../services/api";

const Ctx = createContext(null);

export function AuthProvider({ children }) {
  const [me, setMe] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    if (!localStorage.getItem("token")) { setLoading(false); return null; }
    try {
      const { data } = await api.get("/auth/me");
      setMe(data);
      return data;
    } catch {
      localStorage.removeItem("token");
      setMe(null);
      return null;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    localStorage.setItem("token", data.access_token);
    return load();
  };
  const logout = () => { localStorage.removeItem("token"); setMe(null); };

  return <Ctx.Provider value={{ me, loading, login, logout }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);
