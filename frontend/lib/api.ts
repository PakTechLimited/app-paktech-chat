import type { TokenResponse, User, Post, Comment, AdminUser, PlatformStats } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function authHeaders(token: string | null): HeadersInit {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handleResponse<T>(res: Response): Promise<T> {
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || "Request failed");
  }
  return data as T;
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

    me: (token: string) =>
      fetch(`${API_BASE}/api/v1/auth/me`, {
        headers: authHeaders(token),
      }).then((res) => handleResponse<User>(res)),
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
      fetch(`${API_BASE}/api/v1/posts/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...authHeaders(token),
        },
        body: JSON.stringify({ content, tag }),
      }).then((res) => handleResponse<Post>(res)),

    toggleLike: (token: string, postId: number) =>
      fetch(`${API_BASE}/api/v1/posts/${postId}/like`, {
        method: "POST",
        headers: authHeaders(token),
      }).then((res) => handleResponse<{ liked: boolean; likes_count: number }>(res)),

    comments: (postId: number) =>
      fetch(`${API_BASE}/api/v1/posts/${postId}/comments`).then((res) =>
        handleResponse<Comment[]>(res)
      ),

    addComment: (token: string, postId: number, content: string) =>
      fetch(`${API_BASE}/api/v1/posts/${postId}/comments`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...authHeaders(token),
        },
        body: JSON.stringify({ content }),
      }).then((res) => handleResponse<Comment>(res)),
  },
  admin: {
    listUsers: (token: string) =>
      fetch(`${API_BASE}/api/v1/admin/users`, {
        headers: authHeaders(token),
      }).then((res) => handleResponse<AdminUser[]>(res)),

    deactivateUser: (token: string, userId: number) =>
      fetch(`${API_BASE}/api/v1/admin/users/${userId}/deactivate`, {
        method: "PATCH",
        headers: authHeaders(token),
      }).then((res) => handleResponse<{ id: number; is_active: boolean }>(res)),

    activateUser: (token: string, userId: number) =>
      fetch(`${API_BASE}/api/v1/admin/users/${userId}/activate`, {
        method: "PATCH",
        headers: authHeaders(token),
      }).then((res) => handleResponse<{ id: number; is_active: boolean }>(res)),

    deletePost: (token: string, postId: number) =>
      fetch(`${API_BASE}/api/v1/admin/posts/${postId}`, {
        method: "DELETE",
        headers: authHeaders(token),
      }),

    stats: (token: string) =>
      fetch(`${API_BASE}/api/v1/admin/stats`, {
        headers: authHeaders(token),
      }).then((res) => handleResponse<PlatformStats>(res)),
  },
};

export function wsUrl(roomId: number, username: string): string {
  const proto = API_BASE.startsWith("https") ? "wss" : "ws";
  const host = API_BASE.replace(/^https?:\/\//, "");
  return `${proto}://${host}/ws/${roomId}?username=${encodeURIComponent(username)}`;
}
