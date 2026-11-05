"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import { api, AUTH_EVENTS, endSession, refreshSession } from "./api";
import type { AuthUser, TokenResponse } from "./types";

interface AuthContextValue {
  user: AuthUser | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (
    username: string,
    email: string,
    password: string,
    displayName?: string
  ) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function toUser(data: TokenResponse): AuthUser {
  return {
    id: data.user_id,
    username: data.username,
    display_name: data.display_name,
    avatar_color: data.avatar_color,
    role: data.role,
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // The API client announces every issued session (login, register, silent
    // refresh) and every end of session; this provider just mirrors them.
    const onRefreshed = (e: Event) => {
      const data = (e as CustomEvent<TokenResponse>).detail;
      setToken(data.access_token);
      setUser(toUser(data));
    };
    const onLoggedOut = () => {
      setToken(null);
      setUser(null);
    };
    window.addEventListener(AUTH_EVENTS.refreshed, onRefreshed);
    window.addEventListener(AUTH_EVENTS.loggedOut, onLoggedOut);

    // The access token only lives in memory, so after a page load restore the
    // session from the httpOnly refresh cookie (a no-op 401 when logged out).
    refreshSession().finally(() => setIsLoading(false));

    return () => {
      window.removeEventListener(AUTH_EVENTS.refreshed, onRefreshed);
      window.removeEventListener(AUTH_EVENTS.loggedOut, onLoggedOut);
    };
  }, []);

  async function login(email: string, password: string) {
    await api.auth.login(email, password);
  }

  async function register(
    username: string,
    email: string,
    password: string,
    displayName?: string
  ) {
    await api.auth.register(username, email, password, displayName);
  }

  function logout() {
    // Revoke the refresh token server-side and clear the cookie.
    api.auth.logout().catch(() => {});
    endSession();
  }

  return (
    <AuthContext.Provider
      value={{ user, token, isLoading, login, register, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
