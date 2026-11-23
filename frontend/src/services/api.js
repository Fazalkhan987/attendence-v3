import axios from "axios";

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1" });

api.interceptors.request.use((c) => {
  const t = localStorage.getItem("token");
  if (t) c.headers.Authorization = `Bearer ${t}`;
  return c;
});

api.interceptors.response.use(
  (r) => r,
  (e) => {
    if (e.response?.status === 401 && !e.config.url.includes("/auth/login")) {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    return Promise.reject(e);
  }
);

export const errMsg = (e) => {
  const d = e.response?.data?.detail;
  if (!d) return e.message;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => `${(x.loc || []).slice(1).join(".")}: ${x.msg}`).join("; ");
  return JSON.stringify(d);
};

export default api;
