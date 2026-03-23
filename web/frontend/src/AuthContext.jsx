import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { getStoredToken, getStoredUser, storeAuth, clearAuth, exchangeCode, getMe } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(getStoredUser());
  const [loading, setLoading] = useState(false);

  // Handle OAuth callback code in URL.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    if (code) {
      setLoading(true);
      exchangeCode(code)
        .then((data) => {
          storeAuth(data.token, data.user);
          setUser(data.user);
          // Clean URL.
          window.history.replaceState({}, "", window.location.pathname);
        })
        .catch((err) => {
          console.error("OAuth callback failed:", err);
        })
        .finally(() => setLoading(false));
    }
  }, []);

  // Validate stored token on mount.
  useEffect(() => {
    const token = getStoredToken();
    if (token && !loading) {
      getMe()
        .then((u) => setUser(u))
        .catch(() => {
          clearAuth();
          setUser(null);
        });
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const logout = useCallback(() => {
    clearAuth();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}
