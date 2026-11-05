"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { endSession, getAccessToken, refreshSession, wsUrl } from "./api";
import type { WSEvent } from "./types";

export type SocketStatus = "connecting" | "online" | "reconnecting" | "closed";

// Application close codes sent by the server (see websocket.py)
const CLOSE_UNAUTHORIZED = 4401;
const CLOSE_FORBIDDEN_ORIGIN = 4403;
const CLOSE_NO_SUCH_ROOM = 4404;

const TYPING_RESEND_MS = 2000;
const TYPING_IDLE_MS = 2500;

/**
 * One authenticated WebSocket per room.
 *
 * - First frame is {"type":"auth","token":...}; the server answers "ready".
 * - Expired access token (close 4401): refresh once via the cookie, reconnect,
 *   otherwise end the session.
 * - Network drops: exponential backoff reconnect (1s, 2s, 4s ... max 15s).
 */
export function useRoomSocket(roomId: number, onEvent: (event: WSEvent) => void) {
  const [status, setStatus] = useState<SocketStatus>("connecting");
  const wsRef = useRef<WebSocket | null>(null);
  const readyRef = useRef(false);
  const handlerRef = useRef(onEvent);
  const lastTypingSent = useRef(0);
  const typingStopTimer = useRef<ReturnType<typeof setTimeout> | undefined>(
    undefined
  );

  useEffect(() => {
    handlerRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    let cancelled = false;
    let retry = 0;
    let authRetried = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;

    const connect = () => {
      if (cancelled) return;
      const ws = new WebSocket(wsUrl(roomId));
      wsRef.current = ws;

      ws.onopen = () => {
        ws.send(
          JSON.stringify({ type: "auth", token: getAccessToken() })
        );
      };

      ws.onmessage = (msg) => {
        let event: WSEvent;
        try {
          event = JSON.parse(msg.data as string) as WSEvent;
        } catch {
          return;
        }
        if (event.type === "ready") {
          readyRef.current = true;
          retry = 0;
          authRetried = false;
          setStatus("online");
          return;
        }
        handlerRef.current(event);
      };

      ws.onclose = async (e) => {
        readyRef.current = false;
        if (cancelled) return;

        if (e.code === CLOSE_UNAUTHORIZED) {
          if (!authRetried) {
            authRetried = true;
            const token = await refreshSession();
            if (cancelled) return;
            if (token) {
              connect();
              return;
            }
          }
          endSession();
          return;
        }
        if (e.code === CLOSE_FORBIDDEN_ORIGIN || e.code === CLOSE_NO_SUCH_ROOM) {
          setStatus("closed");
          return;
        }
        setStatus("reconnecting");
        reconnectTimer = setTimeout(connect, Math.min(1000 * 2 ** retry++, 15000));
      };
    };

    connect();
    return () => {
      cancelled = true;
      clearTimeout(reconnectTimer);
      clearTimeout(typingStopTimer.current);
      wsRef.current?.close(1000);
    };
  }, [roomId]);

  const sendFrame = useCallback((frame: object): boolean => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN || !readyRef.current) return false;
    ws.send(JSON.stringify(frame));
    return true;
  }, []);

  const stopTyping = useCallback(() => {
    clearTimeout(typingStopTimer.current);
    if (lastTypingSent.current) {
      lastTypingSent.current = 0;
      sendFrame({ type: "typing_stop" });
    }
  }, [sendFrame]);

  const sendMessage = useCallback(
    (content: string): boolean => {
      const ok = sendFrame({ type: "message", content });
      if (ok) stopTyping();
      return ok;
    },
    [sendFrame, stopTyping]
  );

  /** Call on every keystroke; throttled so we don't flood the server. */
  const notifyTyping = useCallback(() => {
    const now = Date.now();
    if (now - lastTypingSent.current > TYPING_RESEND_MS) {
      if (sendFrame({ type: "typing" })) lastTypingSent.current = now;
    }
    clearTimeout(typingStopTimer.current);
    typingStopTimer.current = setTimeout(stopTyping, TYPING_IDLE_MS);
  }, [sendFrame, stopTyping]);

  return { status, sendMessage, notifyTyping, stopTyping };
}
