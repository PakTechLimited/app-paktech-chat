"use client";

import { useEffect, useRef } from "react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";
import { buildRows, formatTime, initials, type FeedItem } from "@/lib/chat";

interface Props {
  items: FeedItem[];
  me: string;
  loading: boolean;
}

export function MessageFeed({ items, me, loading }: Props) {
  const scroller = useRef<HTMLDivElement>(null);
  const stickToBottom = useRef(true);

  // Follow new messages only while the reader is already at the bottom.
  useEffect(() => {
    const el = scroller.current;
    if (el && stickToBottom.current) el.scrollTop = el.scrollHeight;
  }, [items]);

  function onScroll() {
    const el = scroller.current;
    if (!el) return;
    stickToBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  }

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-sm text-muted-foreground">Loading messages…</p>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 text-center">
        <div>
          <p className="font-medium text-foreground">No messages yet</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Say hello and start the conversation.
          </p>
        </div>
      </div>
    );
  }

  const rows = buildRows(items, me);

  return (
    <div
      ref={scroller}
      onScroll={onScroll}
      className="flex-1 space-y-1 overflow-y-auto px-4 py-4 md:px-6"
    >
      {rows.map(({ item, day, grouped, mine }) => {
        const separator = day ? (
          <div key={`day-${item.id}`} className="my-3 flex items-center gap-3">
            <div className="h-px flex-1 bg-border" />
            <span className="text-xs text-muted-foreground">{day}</span>
            <div className="h-px flex-1 bg-border" />
          </div>
        ) : null;

        if (item.kind === "system") {
          return (
            <div key={item.id} className="animate-in fade-in-0 duration-300">
              {separator}
              <p className="py-1 text-center text-xs text-muted-foreground">{item.text}</p>
            </div>
          );
        }

        return (
          <div key={item.id} className="animate-in fade-in-0 slide-in-from-bottom-2 duration-300">
            {separator}
            <div className={cn("flex gap-2.5", mine && "flex-row-reverse", grouped ? "mt-0.5" : "mt-3")}>
              {grouped ? (
                <div className="w-8 shrink-0" />
              ) : (
                <Avatar className="mt-0.5 h-8 w-8 shrink-0">
                  <AvatarFallback
                    className="text-[11px] font-semibold text-white"
                    style={{ backgroundColor: item.color ?? "#7c5cbf" }}
                  >
                    {initials(item.username)}
                  </AvatarFallback>
                </Avatar>
              )}
              <div className={cn("flex max-w-[78%] flex-col", mine ? "items-end" : "items-start")}>
                {!grouped && (
                  <div className="mb-1 flex items-baseline gap-2 text-xs">
                    <span className="font-medium text-foreground">{item.username}</span>
                    <span className="text-muted-foreground">{formatTime(item.at)}</span>
                  </div>
                )}
                {/* Rendered as text: React escapes it, so message HTML can never run. */}
                <div
                  className={cn(
                    "rounded-2xl px-3.5 py-2 text-sm leading-relaxed break-words whitespace-pre-wrap",
                    mine
                      ? "rounded-tr-md bg-linear-to-br from-brand-from to-brand-to text-white"
                      : "rounded-tl-md border border-border bg-card text-foreground"
                  )}
                >
                  {item.content}
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
