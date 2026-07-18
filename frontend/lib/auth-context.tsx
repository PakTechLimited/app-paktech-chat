"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import { api } from "./api";
import type { AuthUser } from "./types";

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

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const storedToken = localStorage.getItem("pt_token");
    const storedUser = localStorage.getItem("pt_user");
    if (storedToken && storedUser) {
      setToken(storedToken);
      setUser(JSON.parse(storedUser));
    }
    setIsLoading(false);
  }, []);

  function persistAuth(newToken: string, refreshToken: string, newUser: AuthUser) {
    localStorage.setItem("pt_token", newToken);
    localStorage.setItem("pt_refresh", refreshToken);
    localStorage.setItem("pt_user", JSON.stringify(newUser));
    setToken(newToken);
    setUser(newUser);
  }

  async function login(email: string, password: string) {
    const data = await api.auth.login(email, password);
persistAuth(data.access_token, data.refresh_token, {
      id: data.user_id,
      username: data.username,
      display_name: data.display_name,
      avatar_color: data.avatar_color,
      role: data.role,
    });
  }

  async function register(
    username: string,
    email: string,
    password: string,
    displayName?: string
  ) {
    const data = await api.auth.register(username, email, password, displayName);
persistAuth(data.access_token, data.refresh_token, {
      id: data.user_id,
      username: data.username,
      display_name: data.display_name,
      avatar_color: data.avatar_color,
      role: data.role,
    });
  }

  function logout() {
    localStorage.clear();
    setToken(null);
    setUser(null);
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
