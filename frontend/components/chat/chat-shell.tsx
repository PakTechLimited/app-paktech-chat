"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Hash } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { fromHistory, mergeFeed, type FeedItem } from "@/lib/chat";
import { useRoomSocket, type SocketStatus } from "@/lib/use-room-socket";
import type { AuthUser, Room, WSEvent } from "@/lib/types";
import { cn } from "@/lib/utils";
import { CreateRoomDialog } from "./create-room-dialog";
import { MessageFeed } from "./message-feed";
import { MessageInput } from "./message-input";

const TYPING_EXPIRY_MS = 4000;

const STATUS_LABEL: Record<SocketStatus, string> = {
  connecting: "Connecting…",
  online: "Live",
  reconnecting: "Reconnecting…",
  closed: "Unavailable",
};

function StatusPill({ status }: { status: SocketStatus }) {
  const color =
    status === "online"
      ? "bg-[#4ecdc4]"
      : status === "closed"
        ? "bg-destructive"
        : "bg-amber-400";
  return (
    <span className="flex items-center gap-1.5 rounded-full border border-border px-2.5 py-1 text-xs text-muted-foreground">
      <span className={cn("h-1.5 w-1.5 rounded-full", color, status === "online" && "animate-live")} />
      {STATUS_LABEL[status]}
    </span>
  );
}

function typingText(names: string[]): string {
  if (names.length === 0) return "";
  if (names.length === 1) return `${names[0]} is typing…`;
  if (names.length === 2) return `${names[0]} and ${names[1]} are typing…`;
  return "Several people are typing…";
}

/** One open room: history + live socket. Keyed by room id so state resets on switch. */
function RoomView({ room, me }: { room: Room; me: AuthUser }) {
  const [items, setItems] = useState<FeedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [typing, setTyping] = useState<string[]>([]);
  const typingTimers = useRef(new Map<string, ReturnType<typeof setTimeout>>());

  const clearTyping = useCallback((name: string) => {
    clearTimeout(typingTimers.current.get(name));
    typingTimers.current.delete(name);
    setTyping((prev) => prev.filter((n) => n !== name));
  }, []);

  const handleEvent = useCallback(
    (ev: WSEvent) => {
      const name = ev.username ?? "";
      const at = ev.timestamp ?? new Date().toISOString();
      switch (ev.type) {
        case "message": {
          if (ev.id === undefined) return;
          clearTyping(name);
          const item: FeedItem = {
            kind: "message",
            id: `m-${ev.id}`,
            messageId: ev.id,
            username: name,
            color: ev.avatar_color ?? null,
            content: ev.content ?? "",
            at,
          };
          setItems((prev) => mergeFeed(prev, [item]));
          break;
        }
        case "user_joined":
        case "user_left": {
          if (name === me.username) return;
          const text = `${name} ${ev.type === "user_joined" ? "joined" : "left"}`;
          if (ev.type === "user_left") clearTyping(name);
          setItems((prev) =>
            mergeFeed(prev, [{ kind: "system", id: `s-${ev.type}-${name}-${at}`, text, at }])
          );
          break;
        }
        case "typing": {
          if (name === me.username) return;
          clearTimeout(typingTimers.current.get(name));
          typingTimers.current.set(
            name,
            setTimeout(() => clearTyping(name), TYPING_EXPIRY_MS)
          );
          setTyping((prev) => (prev.includes(name) ? prev : [...prev, name]));
          break;
        }
        case "typing_stop":
          clearTyping(name);
          break;
        case "error":
          toast.error(ev.content ?? "Something went wrong");
          break;
      }
    },
    [clearTyping, me.username]
  );

  const { status, sendMessage, notifyTyping } = useRoomSocket(room.id, handleEvent);

  useEffect(() => {
    let cancelled = false;
    api.messages
      .list(room.id)
      .then((history) => {
        if (cancelled) return;
        setItems((prev) => mergeFeed(history.map(fromHistory), prev));
        setLoading(false);
      })
      .catch(() => {
        if (cancelled) return;
        setLoading(false);
        toast.error("Could not load message history");
      });
    const timers = typingTimers.current;
    return () => {
      cancelled = true;
      timers.forEach((t) => clearTimeout(t));
      timers.clear();
    };
  }, [room.id]);

  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col">
      <div className="flex items-center justify-between border-b border-border px-4 py-3 md:px-6">
        <div className="min-w-0">
          <h2 className="flex items-center gap-1 font-semibold text-foreground">
            <Hash className="h-4 w-4 text-muted-foreground" />
            {room.name}
          </h2>
          {room.description && (
            <p className="truncate text-xs text-muted-foreground">{room.description}</p>
          )}
        </div>
        <StatusPill status={status} />
      </div>

      <MessageFeed items={items} me={me.username} loading={loading} />

      <div className="flex h-5 items-center gap-1.5 px-4 text-xs text-muted-foreground md:px-6" aria-live="polite">
        {typing.length > 0 && (
          <span className="inline-flex items-center gap-0.5" aria-hidden="true">
            {[0, 150, 300].map((d) => (
              <span
                key={d}
                className="h-1 w-1 animate-typing rounded-full bg-muted-foreground"
                style={{ animationDelay: `${d}ms` }}
              />
            ))}
          </span>
        )}
        {typingText(typing)}
      </div>
      <MessageInput
        roomName={room.name}
        disabled={status !== "online"}
        onSend={sendMessage}
        onTyping={notifyTyping}
      />
    </div>
  );
}

export function ChatShell() {
  const { user } = useAuth();
  const [rooms, setRooms] = useState<Room[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api.rooms
      .list()
      .then((list) => {
        if (cancelled) return;
        setRooms(list);
        const first = list.find((r) => r.name === "general") ?? list[0];
        setActiveId((prev) => prev ?? first?.id ?? null);
      })
      .catch(() => !cancelled && toast.error("Could not load rooms"))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  if (!user) return null;

  const active = rooms.find((r) => r.id === activeId) ?? null;

  function roomCreated(room: Room) {
    setRooms((prev) => [...prev, room].sort((a, b) => a.name.localeCompare(b.name)));
    setActiveId(room.id);
  }

  return (
    <div className="flex min-h-0 flex-1">
      {/* Desktop room list */}
      <aside className="hidden w-60 shrink-0 flex-col border-r border-border md:flex">
        <div className="flex items-center justify-between px-4 py-3">
          <span className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
            Rooms
          </span>
          <CreateRoomDialog onCreated={roomCreated} />
        </div>
        <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 pb-3">
          {rooms.map((r) => (
            <button
              key={r.id}
              onClick={() => setActiveId(r.id)}
              className={cn(
                "flex w-full items-center gap-1.5 rounded-lg px-3 py-2 text-left text-sm transition-colors",
                r.id === activeId
                  ? "bg-primary/15 font-medium text-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <Hash className="h-3.5 w-3.5 shrink-0" />
              <span className="truncate">{r.name}</span>
            </button>
          ))}
        </nav>
      </aside>

      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        {/* Mobile room switcher */}
        <div className="flex items-center gap-2 overflow-x-auto border-b border-border px-3 py-2 md:hidden">
          {rooms.map((r) => (
            <button
              key={r.id}
              onClick={() => setActiveId(r.id)}
              className={cn(
                "shrink-0 rounded-full border px-3 py-1 text-xs",
                r.id === activeId
                  ? "border-primary bg-primary/15 text-foreground"
                  : "border-border text-muted-foreground"
              )}
            >
              #{r.name}
            </button>
          ))}
          <CreateRoomDialog onCreated={roomCreated} />
        </div>

        {active ? (
          <RoomView key={active.id} room={active} me={user} />
        ) : (
          <div className="flex flex-1 items-center justify-center">
            <p className="text-sm text-muted-foreground">
              {loading ? "Loading rooms…" : "No rooms yet. Create the first one."}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
