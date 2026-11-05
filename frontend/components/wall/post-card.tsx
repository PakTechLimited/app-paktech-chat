"use client";

import { useState } from "react";
import { Heart, MessageCircle, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { formatRelative, initials } from "@/lib/chat";
import type { AuthUser, Comment, Post } from "@/lib/types";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface Props {
  post: Post;
  me: AuthUser;
  onChange: (post: Post) => void;
  onDeleted: (postId: number) => void;
  onTagClick: (tag: string) => void;
}

function AuthorAvatar({
  name,
  color,
  size = "h-9 w-9",
}: {
  name: string;
  color: string | null;
  size?: string;
}) {
  return (
    <Avatar className={cn(size, "shrink-0")}>
      <AvatarFallback
        className="text-[11px] font-semibold text-white"
        style={{ backgroundColor: color ?? "#7c5cbf" }}
      >
        {initials(name)}
      </AvatarFallback>
    </Avatar>
  );
}

export function PostCard({ post, me, onChange, onDeleted, onTagClick }: Props) {
  const [comments, setComments] = useState<Comment[] | null>(null);
  const [showComments, setShowComments] = useState(false);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const canDelete = post.author.id === me.id || me.role === "admin";
  const name = post.author.display_name || post.author.username;

  async function toggleLike() {
    // Optimistic: flip immediately, roll back if the server refuses.
    const before = post;
    onChange({
      ...post,
      liked_by_me: !post.liked_by_me,
      likes_count: post.likes_count + (post.liked_by_me ? -1 : 1),
    });
    try {
      const r = await api.posts.toggleLike(post.id);
      onChange({ ...post, liked_by_me: r.liked, likes_count: r.likes_count });
    } catch (err) {
      onChange(before);
      toast.error(err instanceof Error ? err.message : "Could not update like");
    }
  }

  async function toggleComments() {
    const next = !showComments;
    setShowComments(next);
    if (next && comments === null) {
      try {
        setComments(await api.posts.comments(post.id));
      } catch {
        toast.error("Could not load comments");
        setShowComments(false);
      }
    }
  }

  async function submitComment(e: React.FormEvent) {
    e.preventDefault();
    const text = draft.trim();
    if (!text || busy) return;
    setBusy(true);
    try {
      const c = await api.posts.addComment(post.id, text);
      setComments((prev) => [...(prev ?? []), c]);
      onChange({ ...post, comments_count: post.comments_count + 1 });
      setDraft("");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not add comment");
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    try {
      await api.posts.remove(post.id);
      onDeleted(post.id);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not delete post");
      setConfirmDelete(false);
    }
  }

  return (
    <article className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-start gap-3">
        <AuthorAvatar name={name} color={post.author.avatar_color} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
            <span className="font-medium text-foreground">{name}</span>
            <span className="text-xs text-muted-foreground">
              @{post.author.username} · {formatRelative(post.created_at)}
            </span>
            {post.tag && (
              <button onClick={() => onTagClick(post.tag!)} aria-label={`Filter by ${post.tag}`}>
                <Badge variant="secondary">#{post.tag}</Badge>
              </button>
            )}
          </div>
          {/* Text only: React escapes it, so post HTML can never execute. */}
          <p className="mt-1.5 text-sm leading-relaxed break-words whitespace-pre-wrap text-foreground">
            {post.content}
          </p>

          <div className="mt-3 flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleLike}
              aria-pressed={post.liked_by_me}
              className={cn(post.liked_by_me && "text-[#c46bb5]")}
            >
              <Heart className={cn(post.liked_by_me && "fill-current")} />
              {post.likes_count}
            </Button>
            <Button variant="ghost" size="sm" onClick={toggleComments}>
              <MessageCircle />
              {post.comments_count}
            </Button>
            {canDelete &&
              (confirmDelete ? (
                <div className="ml-auto flex items-center gap-1">
                  <Button variant="destructive" size="sm" onClick={remove}>
                    Confirm delete
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => setConfirmDelete(false)}>
                    Cancel
                  </Button>
                </div>
              ) : (
                <Button
                  variant="ghost"
                  size="sm"
                  className="ml-auto text-muted-foreground"
                  onClick={() => setConfirmDelete(true)}
                  aria-label="Delete post"
                >
                  <Trash2 />
                </Button>
              ))}
          </div>

          {showComments && (
            <div className="mt-3 space-y-3 border-t border-border pt-3">
              {comments === null ? (
                <p className="text-xs text-muted-foreground">Loading comments…</p>
              ) : comments.length === 0 ? (
                <p className="text-xs text-muted-foreground">No comments yet.</p>
              ) : (
                comments.map((c) => {
                  const cname = c.author.display_name || c.author.username;
                  return (
                    <div key={c.id} className="flex gap-2.5">
                      <AuthorAvatar name={cname} color={c.author.avatar_color} size="h-7 w-7" />
                      <div className="min-w-0">
                        <p className="text-xs">
                          <span className="font-medium text-foreground">{cname}</span>{" "}
                          <span className="text-muted-foreground">
                            {formatRelative(c.created_at)}
                          </span>
                        </p>
                        <p className="text-sm break-words whitespace-pre-wrap text-foreground">
                          {c.content}
                        </p>
                      </div>
                    </div>
                  );
                })
              )}
              <form onSubmit={submitComment} className="flex gap-2">
                <Input
                  value={draft}
                  maxLength={500}
                  placeholder="Write a comment…"
                  onChange={(e) => setDraft(e.target.value)}
                />
                <Button type="submit" size="sm" disabled={busy || !draft.trim()} className="h-8">
                  Reply
                </Button>
              </form>
            </div>
          )}
        </div>
      </div>
    </article>
  );
}
