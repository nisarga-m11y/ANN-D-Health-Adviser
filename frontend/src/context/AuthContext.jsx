import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { fetchCurrentUser, loginUser, registerUser } from "../api/auth";
import { clearChatHistory } from "../api/chat";

const AuthContext = createContext(null);
const AUTH_BOOTSTRAP_TIMEOUT_MS = 4000;

function withTimeout(promise, timeoutMs, timeoutMessage) {
  return Promise.race([
    promise,
    new Promise((_, reject) => {
      setTimeout(() => reject(new Error(timeoutMessage)), timeoutMs);
    }),
  ]);
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function bootstrapAuth() {
      const token = localStorage.getItem("auth_token");
      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const currentUser = await withTimeout(
          fetchCurrentUser(),
          AUTH_BOOTSTRAP_TIMEOUT_MS,
          "Auth bootstrap timed out",
        );
        setUser(currentUser);
        if (currentUser?.name) {
          localStorage.setItem("auth_user_name", String(currentUser.name));
        }
        if (currentUser?.email) {
          localStorage.setItem("auth_user_email", String(currentUser.email));
          localStorage.setItem("auth_login_email", String(currentUser.email));
        }
      } catch {
        localStorage.removeItem("auth_token");
        localStorage.removeItem("auth_user_name");
        localStorage.removeItem("auth_user_email");
        localStorage.removeItem("auth_login_email");
      } finally {
        setLoading(false);
      }
    }

    bootstrapAuth();
  }, []);

  async function login(payload) {
    const data = await loginUser(payload);
    localStorage.setItem("auth_token", data.token);
    if (data?.user?.name) {
      localStorage.setItem("auth_user_name", String(data.user.name));
    }
    if (data?.user?.email) {
      localStorage.setItem("auth_user_email", String(data.user.email));
      localStorage.setItem("auth_login_email", String(data.user.email));
    } else if (payload?.email) {
      localStorage.setItem("auth_login_email", String(payload.email));
    }
    setUser(data.user);
    return data;
  }

  async function register(payload) {
    const data = await registerUser(payload);
    localStorage.setItem("auth_token", data.token);
    if (data?.user?.name) {
      localStorage.setItem("auth_user_name", String(data.user.name));
    }
    if (data?.user?.email) {
      localStorage.setItem("auth_user_email", String(data.user.email));
      localStorage.setItem("auth_login_email", String(data.user.email));
    } else if (payload?.email) {
      localStorage.setItem("auth_login_email", String(payload.email));
    }
    setUser(data.user);
    return data;
  }

  async function logout() {
    try {
      await clearChatHistory();
    } catch {
      // Keep logout resilient even if history cleanup fails.
    } finally {
      localStorage.removeItem("auth_token");
      localStorage.removeItem("auth_user_name");
      localStorage.removeItem("auth_user_email");
      localStorage.removeItem("auth_login_email");
      setUser(null);
    }
  }

  const value = useMemo(
    () => ({ user, loading, login, register, logout, isAuthenticated: !!user }),
    [user, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
