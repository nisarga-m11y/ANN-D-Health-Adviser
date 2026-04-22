import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { fetchCurrentUser, loginUser, registerUser } from "../api/auth";

const AuthContext = createContext(null);

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
        const currentUser = await fetchCurrentUser();
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

  function logout() {
    localStorage.removeItem("auth_token");
    setUser(null);
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
