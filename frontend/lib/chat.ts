import type { ChatMessage } from "./types";

export type FeedItem =
  | {
      kind: "message";
      id: string;
      messageId: number;
      username: string;
      color: string | null;
      content: string;
      at: string;
    }
  | { kind: "system"; id: string; text: string; at: string };

export function fromHistory(m: ChatMessage): FeedItem {
  return {
    kind: "message",
    id: `m-${m.id}`,
    messageId: m.id,
    username: m.author_username ?? "unknown",
    color: m.author_avatar_color,
    content: m.content,
    at: m.created_at,
  };
}

/** Merge history with live items; a message seen twice (history + live) shows once. */
export function mergeFeed(history: FeedItem[], live: FeedItem[]): FeedItem[] {
  const seen = new Set(history.map((i) => i.id));
  const extra = live.filter((i) => !seen.has(i.id));
  return [...history, ...extra].sort(
    (a, b) => new Date(a.at).getTime() - new Date(b.at).getTime()
  );
}

export function initials(name: string): string {
  return name.slice(0, 2).toUpperCase();
}

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function formatDay(iso: string): string {
  const d = new Date(iso);
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);
  if (d.toDateString() === today.toDateString()) return "Today";
  if (d.toDateString() === yesterday.toDateString()) return "Yesterday";
  return d.toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" });
}

export interface FeedRow {
  item: FeedItem;
  /** Day label to show above this row (first row of a new day), else null. */
  day: string | null;
  /** Same sender as the previous message within the grouping window. */
  grouped: boolean;
  mine: boolean;
}

const GROUP_GAP_MS = 5 * 60 * 1000;

/** Pure view-model: decides day separators and message grouping. */
export function buildRows(items: FeedItem[], me: string): FeedRow[] {
  let lastDay = "";
  let lastSender = "";
  let lastTime = 0;
  return items.map((item) => {
    const dayLabel = formatDay(item.at);
    const day = dayLabel !== lastDay ? dayLabel : null;
    lastDay = dayLabel;

    if (item.kind === "system") {
      lastSender = "";
      return { item, day, grouped: false, mine: false };
    }
    const t = new Date(item.at).getTime();
    const grouped = item.username === lastSender && t - lastTime < GROUP_GAP_MS;
    lastSender = item.username;
    lastTime = t;
    return { item, day, grouped, mine: item.username === me };
  });
}
