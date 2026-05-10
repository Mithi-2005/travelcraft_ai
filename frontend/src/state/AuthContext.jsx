import { createContext, startTransition, useContext, useEffect, useMemo, useState } from "react";
import { ApiError, getCurrentUser, loginUser, logoutUser, registerUser } from "../lib/api";

const AuthContext = createContext(null);
const AUTH_SNAPSHOT_KEY = "travelcraft_auth_user";

function loadStoredUser() {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(AUTH_SNAPSHOT_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function storeUserSnapshot(user) {
  if (typeof window === "undefined") return;
  if (!user) {
    window.localStorage.removeItem(AUTH_SNAPSHOT_KEY);
    return;
  }
  window.localStorage.setItem(AUTH_SNAPSHOT_KEY, JSON.stringify(user));
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => loadStoredUser());
  const [loadingSession, setLoadingSession] = useState(true);
  const [authError, setAuthError] = useState("");

  const clearAuthState = () => {
    startTransition(() => {
      setUser(null);
    });
    storeUserSnapshot(null);
    setAuthError("");
  };

  const refreshSession = async () => {
    setLoadingSession(true);
    try {
      const data = await getCurrentUser();
      startTransition(() => {
        setUser(data.user);
      });
      storeUserSnapshot(data.user);
      setAuthError("");
      return data.user;
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        startTransition(() => {
          setUser(null);
        });
        storeUserSnapshot(null);
        setAuthError("");
        return null;
      } else {
        const storedUser = loadStoredUser();
        if (!storedUser) {
          startTransition(() => {
            setUser(null);
          });
        } else {
          startTransition(() => {
            setUser(storedUser);
          });
        }
        setAuthError(error.message || "Unable to restore session.");
      }
      return storedUser || null;
    } finally {
      setLoadingSession(false);
    }
  };

  useEffect(() => {
    refreshSession();
  }, []);

  const login = async (payload) => {
    const data = await loginUser(payload);
    setUser(data.user);
    storeUserSnapshot(data.user);
    setAuthError("");
    return data.user;
  };

  const register = async (payload) => {
    const data = await registerUser(payload);
    setUser(data.user);
    storeUserSnapshot(data.user);
    setAuthError("");
    return data.user;
  };

  const logout = async () => {
    try {
      await logoutUser();
    } finally {
      clearAuthState();
    }
  };

  const value = useMemo(
    () => ({
      user,
      loadingSession,
      authError,
      refreshSession,
      login,
      register,
      logout,
      clearAuthState,
    }),
    [user, loadingSession, authError],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuthContext() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuthContext must be used inside AuthProvider");
  }
  return context;
}
