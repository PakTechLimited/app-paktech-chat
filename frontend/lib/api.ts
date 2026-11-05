import type { TokenResponse, User, Post, Comment, AdminUser, PlatformStats } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function authHeaders(token: string | null): HeadersInit {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handleResponse<T>(res: Response): Promise<T> {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || "Request failed");
  }
  return data as T;
}

// --- Silent refresh -------------------------------------------------------
// On a 401 we exchange the stored refresh token for a new access token once
// (single-flight, so parallel requests share one refresh call), then retry.
// If the refresh fails the session is dead: clear storage and tell the
// AuthProvider via a window event so the UI returns to the login screen.

export const AUTH_EVENTS = {
  refreshed: "pt:token-refreshed",
  loggedOut: "pt:logged-out",
} as const;

let refreshInFlight: Promise<string | null> | null = null;

function readStore(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = readStore("pt_refresh");
  if (!refreshToken) return null;
  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return null;
    const data = (await res.json()) as TokenResponse;
    localStorage.setItem("pt_token", data.access_token);
    localStorage.setItem("pt_refresh", data.refresh_token);
    window.dispatchEvent(
      new CustomEvent(AUTH_EVENTS.refreshed, { detail: data })
    );
    return data.access_token;
  } catch {
    return null;
  }
}

function endSession() {
  try {
    localStorage.clear();
  } catch {
    /* storage unavailable */
  }
  window.dispatchEvent(new Event(AUTH_EVENTS.loggedOut));
}

/** fetch() with the current access token; refreshes once on 401. */
async function authedFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const send = (token: string | null) =>
    fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { ...(init.headers || {}), ...authHeaders(token) },
    });

  const res = await send(readStore("pt_token"));
  if (res.status !== 401) return res;

  refreshInFlight ??= refreshAccessToken().finally(() => {
    refreshInFlight = null;
  });
  const newToken = await refreshInFlight;
  if (!newToken) {
    endSession();
    return res;
  }
  return send(newToken);
}

export const api = {
  auth: {
    login: (email: string, password: string) =>
      fetch(`${API_BASE}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      }).then((res) => handleResponse<TokenResponse>(res)),

    register: (
      username: string,
      email: string,
      password: string,
      display_name?: string
    ) =>
      fetch(`${API_BASE}/api/v1/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, email, password, display_name }),
      }).then((res) => handleResponse<TokenResponse>(res)),

    refresh: (refresh_token: string) =>
      fetch(`${API_BASE}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token }),
      }).then((res) => handleResponse<TokenResponse>(res)),

    me: () =>
      authedFetch(`/api/v1/auth/me`).then((res) => handleResponse<User>(res)),
  },

  posts: {
    list: (token: string | null, tag?: string) => {
      const url = new URL(`${API_BASE}/api/v1/posts/`);
      if (tag) url.searchParams.set("tag", tag);
      return fetch(url.toString(), { headers: authHeaders(token) }).then(
        (res) => handleResponse<Post[]>(res)
      );

    },

    create: (token: string, content: string, tag?: string | null) =>
      authedFetch(`/api/v1/posts/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, tag }),
      }).then((res) => handleResponse<Post>(res)),

    toggleLike: (token: string, postId: number) =>
      authedFetch(`/api/v1/posts/${postId}/like`, {
        method: "POST",
      }).then((res) => handleResponse<{ liked: boolean; likes_count: number }>(res)),

    comments: (postId: number) =>
      fetch(`${API_BASE}/api/v1/posts/${postId}/comments`).then((res) =>
        handleResponse<Comment[]>(res)
      ),

    addComment: (token: string, postId: number, content: string) =>
      authedFetch(`/api/v1/posts/${postId}/comments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      }).then((res) => handleResponse<Comment>(res)),
  },
  admin: {
    listUsers: (token: string) =>
      authedFetch(`/api/v1/admin/users`).then((res) => handleResponse<AdminUser[]>(res)),

    deactivateUser: (token: string, userId: number) =>
      authedFetch(`/api/v1/admin/users/${userId}/deactivate`, {
        method: "PATCH",
      }).then((res) => handleResponse<{ id: number; is_active: boolean }>(res)),

    activateUser: (token: string, userId: number) =>
      authedFetch(`/api/v1/admin/users/${userId}/activate`, {
        method: "PATCH",
      }).then((res) => handleResponse<{ id: number; is_active: boolean }>(res)),

    deletePost: (token: string, postId: number) =>
      authedFetch(`/api/v1/admin/posts/${postId}`, {
        method: "DELETE",
      }),

    stats: (token: string) =>
      authedFetch(`/api/v1/admin/stats`).then((res) => handleResponse<PlatformStats>(res)),
  },
};

export function wsUrl(roomId: number, username: string): string {
  const proto = API_BASE.startsWith("https") ? "wss" : "ws";
  const host = API_BASE.replace(/^https?:\/\//, "");
  return `${proto}://${host}/ws/${roomId}?username=${encodeURIComponent(username)}`;
}
