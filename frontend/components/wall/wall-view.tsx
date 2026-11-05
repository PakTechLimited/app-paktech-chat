"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { Post } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { PostCard } from "./post-card";

const PAGE_SIZE = 20;
const MAX_LENGTH = 2000;
const SUGGESTED_TAGS = ["devops", "kubernetes", "azure", "terraform", "security", "question"];

export function WallView() {
  const { user } = useAuth();
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(false);
  const [filter, setFilter] = useState<string | null>(null);

  const [draft, setDraft] = useState("");
  const [draftTag, setDraftTag] = useState<string | null>(null);
  const [posting, setPosting] = useState(false);

  // Load the first page whenever the tag filter changes.
  useEffect(() => {
    let cancelled = false;
    api.posts
      .list({ tag: filter })
      .then((page) => {
        if (cancelled) return;
        setPosts(page);
        setHasMore(page.length === PAGE_SIZE);
      })
      .catch(() => !cancelled && toast.error("Could not load the wall"))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [filter]);

  const changeFilter = useCallback((tag: string | null) => {
    setLoading(true);
    setFilter(tag);
  }, []);

  async function loadMore() {
    const last = posts[posts.length - 1];
    if (!last) return;
    try {
      const page = await api.posts.list({ tag: filter, before: last.id });
      setPosts((prev) => [...prev, ...page]);
      setHasMore(page.length === PAGE_SIZE);
    } catch {
      toast.error("Could not load more posts");
    }
  }

  async function publish(e: React.FormEvent) {
    e.preventDefault();
    const content = draft.trim();
    if (!content || posting) return;
    setPosting(true);
    try {
      const post = await api.posts.create(content, draftTag);
      // Show it now unless a different tag filter is active.
      if (!filter || filter === post.tag) setPosts((prev) => [post, ...prev]);
      setDraft("");
      setDraftTag(null);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not publish");
    } finally {
      setPosting(false);
    }
  }

  if (!user) return null;

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-2xl space-y-4 px-4 py-6">
        <form onSubmit={publish} className="rounded-xl border border-border bg-card p-4">
          <Textarea
            value={draft}
            maxLength={MAX_LENGTH}
            rows={3}
            placeholder="Share something with the team…"
            className="resize-none bg-transparent"
            onChange={(e) => setDraft(e.target.value)}
          />
          <div className="mt-3 flex flex-wrap items-center gap-2">
            {SUGGESTED_TAGS.map((t) => (
              <button
                type="button"
                key={t}
                onClick={() => setDraftTag(draftTag === t ? null : t)}
                aria-pressed={draftTag === t}
                className={cn(
                  "rounded-full border px-2.5 py-0.5 text-xs transition-colors",
                  draftTag === t
                    ? "border-primary bg-primary/15 text-foreground"
                    : "border-border text-muted-foreground hover:text-foreground"
                )}
              >
                #{t}
              </button>
            ))}
            <span className="ml-auto text-xs text-muted-foreground">
              {draft.length}/{MAX_LENGTH}
            </span>
            <Button type="submit" size="sm" disabled={posting || !draft.trim()}>
              {posting ? "Posting…" : "Post"}
            </Button>
          </div>
        </form>

        {filter && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            Showing #{filter}
            <Button variant="ghost" size="xs" onClick={() => changeFilter(null)}>
              Clear filter
            </Button>
          </div>
        )}

        {loading ? (
          <p className="py-10 text-center text-sm text-muted-foreground">Loading…</p>
        ) : posts.length === 0 ? (
          <div className="py-10 text-center">
            <p className="font-medium text-foreground">Nothing here yet</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {filter ? "No posts with this tag." : "Be the first to post."}
            </p>
          </div>
        ) : (
          posts.map((p) => (
            <PostCard
              key={p.id}
              post={p}
              me={user}
              onChange={(next) => setPosts((prev) => prev.map((x) => (x.id === next.id ? next : x)))}
              onDeleted={(id) => setPosts((prev) => prev.filter((x) => x.id !== id))}
              onTagClick={changeFilter}
            />
          ))
        )}

        {hasMore && !loading && (
          <div className="flex justify-center pb-4">
            <Button variant="outline" onClick={loadMore}>
              Load more
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
