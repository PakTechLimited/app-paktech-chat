import type {
  TokenResponse,
  User,
  Post,
  Comment,
  AdminUser,
  PlatformStats,
  Room,
  ChatMessage,
  AITurn,
} from "./types";

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

// --- Session handling -----------------------------------------------------
// The access token lives only in this module's memory: nothing in
// localStorage for an XSS payload to steal. It is restored after a page load
// by exchanging the httpOnly refresh cookie (see AuthProvider).
//
// On a 401 we refresh once (single-flight within the tab, serialised across
// tabs with the Web Locks API) and retry. Serialising matters: refresh tokens
// rotate, so two tabs refreshing with the same cookie at the same moment would
// look like a replay and the server would revoke every session.

export const AUTH_EVENTS = {
  refreshed: "pt:token-refreshed",
  loggedOut: "pt:logged-out",
} as const;

// Required on every cookie-authenticated endpoint. A custom header forces a
// CORS preflight, which only our own origin passes (CSRF defence in depth).
const CSRF_HEADERS = { "X-Requested-With": "pt" } as const;

// Non-secret "a session probably exists" hint for the Next.js proxy, which
// cannot see the API's httpOnly cookie. UX only: the API enforces real auth.
const SESSION_HINT = "pt_session";

let accessToken: string | null = null;
let refreshInFlight: Promise<string | null> | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

function setSessionHint(on: boolean) {
  document.cookie = on
    ? `${SESSION_HINT}=1; path=/; max-age=${30 * 24 * 3600}; SameSite=Lax`
    : `${SESSION_HINT}=; path=/; max-age=0; SameSite=Lax`;
}

/** Remember a freshly issued session (login, register, refresh). */
function startLocalSession(data: TokenResponse) {
  accessToken = data.access_token;
  setSessionHint(true);
  try {
    // Tokens used to be kept here; drop leftovers from older builds.
    localStorage.removeItem("pt_token");
    localStorage.removeItem("pt_user");
  } catch {
    /* storage unavailable */
  }
  window.dispatchEvent(new CustomEvent(AUTH_EVENTS.refreshed, { detail: data }));
}

async function refreshOnce(): Promise<string | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: "POST",
      credentials: "include",
      headers: CSRF_HEADERS,
    });
    if (!res.ok) return null;
    const data = (await res.json()) as TokenResponse;
    startLocalSession(data);
    return data.access_token;
  } catch {
    return null;
  }
}

async function refreshAccessToken(): Promise<string | null> {
  // The lock is held across the whole request, so a second tab starts its
  // refresh only after the first has stored the rotated cookie.
  if (typeof navigator !== "undefined" && navigator.locks) {
    return navigator.locks.request("pt-refresh", refreshOnce);
  }
  return refreshOnce();
}

/** Exchange the refresh cookie for a new access token (one call at a time). */
export function refreshSession(): Promise<string | null> {
  refreshInFlight ??= refreshAccessToken().finally(() => {
    refreshInFlight = null;
  });
  return refreshInFlight;
}

export function endSession() {
  accessToken = null;
  setSessionHint(false);
  window.dispatchEvent(new Event(AUTH_EVENTS.loggedOut));
}

/** fetch() with the current access token; refreshes once on 401. */
async function authedFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const send = (token: string | null) =>
    fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { ...(init.headers || {}), ...authHeaders(token) },
    });

  const res = await send(accessToken);
  if (res.status !== 401) return res;

  const newToken = await refreshSession();
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
        credentials: "include",
        headers: { "Content-Type": "application/json", ...CSRF_HEADERS },
        body: JSON.stringify({ email, password }),
      })
        .then((res) => handleResponse<TokenResponse>(res))
        .then((data) => {
          startLocalSession(data);
          return data;
        }),

    register: (
      username: string,
      email: string,
      password: string,
      display_name?: string
    ) =>
      fetch(`${API_BASE}/api/v1/auth/register`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json", ...CSRF_HEADERS },
        body: JSON.stringify({ username, email, password, display_name }),
      })
        .then((res) => handleResponse<TokenResponse>(res))
        .then((data) => {
          startLocalSession(data);
          return data;
        }),

    logout: () =>
      fetch(`${API_BASE}/api/v1/auth/logout`, {
        method: "POST",
        credentials: "include",
        headers: CSRF_HEADERS,
      }),

    me: () =>
      authedFetch(`/api/v1/auth/me`).then((res) => handleResponse<User>(res)),
  },

  rooms: {
    list: () =>
      authedFetch(`/api/v1/rooms/`).then((res) => handleResponse<Room[]>(res)),

    create: (name: string, description?: string) =>
      authedFetch(`/api/v1/rooms/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, description: description || null }),
      }).then((res) => handleResponse<Room>(res)),
  },

  messages: {
    list: (roomId: number, limit = 50) =>
      authedFetch(`/api/v1/messages/${roomId}?limit=${limit}`).then((res) =>
        handleResponse<ChatMessage[]>(res)
      ),
  },

  posts: {
    list: (opts: { tag?: string | null; before?: number | null } = {}) => {
      const qs = new URLSearchParams();
      if (opts.tag) qs.set("tag", opts.tag);
      if (opts.before) qs.set("before", String(opts.before));
      const q = qs.toString();
      return authedFetch(`/api/v1/posts/${q ? `?${q}` : ""}`).then((res) =>
        handleResponse<Post[]>(res)
      );
    },

    create: (content: string, tag?: string | null) =>
      authedFetch(`/api/v1/posts/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, tag: tag || null }),
      }).then((res) => handleResponse<Post>(res)),

    remove: async (postId: number) => {
      const res = await authedFetch(`/api/v1/posts/${postId}`, { method: "DELETE" });
      if (!res.ok) await handleResponse<never>(res);
    },

    toggleLike: (postId: number) =>
      authedFetch(`/api/v1/posts/${postId}/like`, { method: "POST" }).then((res) =>
        handleResponse<{ liked: boolean; likes_count: number }>(res)
      ),

    comments: (postId: number) =>
      authedFetch(`/api/v1/posts/${postId}/comments`).then((res) =>
        handleResponse<Comment[]>(res)
      ),

    addComment: (postId: number, content: string) =>
      authedFetch(`/api/v1/posts/${postId}/comments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      }).then((res) => handleResponse<Comment>(res)),
  },

  ai: {
    chat: (message: string, history: AITurn[] = []) =>
      authedFetch(`/api/v1/ai/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, history }),
      }).then((res) => handleResponse<{ reply: string }>(res)),
  },

  admin: {
    listUsers: () =>
      authedFetch(`/api/v1/admin/users`).then((res) => handleResponse<AdminUser[]>(res)),

    deactivateUser: (userId: number) =>
      authedFetch(`/api/v1/admin/users/${userId}/deactivate`, {
        method: "PATCH",
      }).then((res) => handleResponse<{ id: number; is_active: boolean }>(res)),

    activateUser: (userId: number) =>
      authedFetch(`/api/v1/admin/users/${userId}/activate`, {
        method: "PATCH",
      }).then((res) => handleResponse<{ id: number; is_active: boolean }>(res)),

    deletePost: (postId: number) =>
      authedFetch(`/api/v1/admin/posts/${postId}`, {
        method: "DELETE",
      }),

    stats: () =>
      authedFetch(`/api/v1/admin/stats`).then((res) => handleResponse<PlatformStats>(res)),
  },
};

/** WebSocket URL for a room. No identity in the URL: the client authenticates
 * with its access token in the first frame (see use-room-socket.ts). */
export function wsUrl(roomId: number): string {
  const proto = API_BASE.startsWith("https") ? "wss" : "ws";
  const host = API_BASE.replace(/^https?:\/\//, "");
  return `${proto}://${host}/ws/${roomId}`;
}
