export interface User {
  id: number;
  username: string;
  email: string;
  display_name: string | null;
  avatar_color: string | null;
  bio: string | null;
  is_verified: boolean;
  role: "member" | "admin";
}

export interface AuthUser {
  id: number;
  username: string;
  display_name: string | null;
  avatar_color: string;
  role: "member" | "admin";
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user_id: number;
  username: string;
  display_name: string | null;
  avatar_color: string;
  role: "member" | "admin";
}

export interface Room {
  id: number;
  name: string;
  description?: string;
}

export type WSEventType =
  | "message"
  | "user_joined"
  | "user_left"
  | "typing"
  | "typing_stop";

export interface WSEvent {
  type: WSEventType;
  username: string;
  content?: string;
  timestamp?: string;
  avatar_color?: string;
}

export interface PostAuthor {
  id: number;
  username: string;
  display_name: string | null;
  avatar_color: string | null;
}

export interface Post {
  id: number;
  content: string;
  tag: string | null;
  likes_count: number;
  comments_count: number;
  created_at: string;
  liked_by_me: boolean;
  author: PostAuthor;
}

export interface Comment {
  id: number;
  content: string;
  created_at: string;
  author: PostAuthor;
}

export interface AdminUser {
  id: number;
  username: string;
  email: string;
  display_name: string | null;
  avatar_color: string | null;
  role: "member" | "admin";
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface PlatformStats {
  total_users: number;
  active_users: number;
  total_messages: number;
  total_posts: number;
}
