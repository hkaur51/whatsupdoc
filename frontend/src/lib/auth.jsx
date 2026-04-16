import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api } from "./api.js";

const AuthCtx = createContext(null);
const STORAGE_KEY = "whatsupdoc_auth";

function readStored() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [state, setState] = useState(() => readStored() || { token: null, user: null });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (state?.token) localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    else localStorage.removeItem(STORAGE_KEY);
  }, [state]);

  // Validate token on mount; log out silently if it's stale.
  useEffect(() => {
    (async () => {
      if (!state.token) return;
      try {
        const me = await api("/auth/me", { token: state.token });
        setState((s) => ({ ...s, user: me }));
      } catch {
        setState({ token: null, user: null });
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const signup = useCallback(async ({ name, email, password }) => {
    setLoading(true);
    try {
      const res = await api("/auth/signup", { method: "POST", body: { name, email, password } });
      setState({ token: res.token, user: res.user });
      return res.user;
    } finally {
      setLoading(false);
    }
  }, []);

  const login = useCallback(async ({ email, password }) => {
    setLoading(true);
    try {
      const res = await api("/auth/login", { method: "POST", body: { email, password } });
      setState({ token: res.token, user: res.user });
      return res.user;
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(() => setState({ token: null, user: null }), []);

  return (
    <AuthCtx.Provider value={{ ...state, loading, signup, login, logout }}>
      {children}
    </AuthCtx.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}
