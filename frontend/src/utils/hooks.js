import { useCallback, useEffect, useState } from "react";
import api, { errMsg } from "../services/api";

export function useApi(url, params) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const key = JSON.stringify(params || {});
  const reload = useCallback(async () => {
    try {
      const clean = Object.fromEntries(Object.entries(params || {}).filter(([, v]) => v !== "" && v != null));
      const res = await api.get(url, { params: clean });
      setData(res.data);
      setError("");
    } catch (e) {
      setError(errMsg(e));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url, key]);
  useEffect(() => { reload(); }, [reload]);
  return { data, error, reload };
}
