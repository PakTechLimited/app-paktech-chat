"use client";

import { useEffect, useRef, useState } from "react";
import { Bot, SendHorizontal, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import type { AITurn } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

const MAX_LENGTH = 2000;
const MAX_HISTORY = 10; // server keeps the last 10 turns of context
const SUGGESTIONS = [
  "Explain a Kubernetes readiness vs liveness probe",
  "How do I roll back a failed Helm release?",
  "What is the difference between Terraform plan and apply?",
  "Give me a checklist for securing an AKS cluster",
];

interface Entry extends AITurn {
  error?: boolean;
}

export function AiChat() {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [value, setValue] = useState("");
  const [thinking, setThinking] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [entries, thinking]);

  async function ask(text: string) {
    const message = text.trim();
    if (!message || thinking) return;

    // Context = recent successful turns, trimmed so it always starts with a user turn.
    const ok = entries.filter((e) => !e.error);
    let history: AITurn[] = ok
      .slice(-MAX_HISTORY)
      .map(({ role, content }) => ({ role, content }));
    if (history[0]?.role === "assistant") history = history.slice(1);

    setEntries((prev) => [...prev, { role: "user", content: message }]);
    setValue("");
    setThinking(true);
    try {
      const { reply } = await api.ai.chat(message, history);
      setEntries((prev) => [...prev, { role: "assistant", content: reply }]);
    } catch (err) {
      setEntries((prev) => [
        ...prev,
        {
          role: "assistant",
          error: true,
          content: err instanceof Error ? err.message : "The assistant is unavailable.",
        },
      ]);
    } finally {
      setThinking(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-0 w-full max-w-3xl flex-1 flex-col">
      <div className="flex-1 space-y-4 overflow-y-auto px-4 py-6">
        {entries.length === 0 && (
          <div className="py-8 text-center">
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-[#7c5cbf] to-[#c46bb5]">
              <Sparkles className="h-6 w-6 text-white" />
            </div>
            <h2 className="text-lg font-semibold text-foreground">PakTech AI</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Ask anything about DevOps, cloud and your stack.
            </p>
            <div className="mx-auto mt-6 grid max-w-xl gap-2 sm:grid-cols-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => ask(s)}
                  className="rounded-xl border border-border bg-card p-3 text-left text-sm text-muted-foreground transition-colors hover:border-primary hover:text-foreground"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {entries.map((e, i) => (
          <div key={i} className={cn("flex gap-2.5", e.role === "user" && "flex-row-reverse")}>
            {e.role === "assistant" && (
              <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/20">
                <Bot className="h-4 w-4 text-primary" />
              </div>
            )}
            {/* Plain text: model output is never injected as HTML. */}
            <div
              className={cn(
                "max-w-[85%] rounded-2xl px-3.5 py-2 text-sm leading-relaxed break-words whitespace-pre-wrap",
                e.role === "user"
                  ? "rounded-tr-md bg-gradient-to-br from-[#7c5cbf] to-[#c46bb5] text-white"
                  : e.error
                    ? "rounded-tl-md border border-destructive/40 bg-destructive/10 text-foreground"
                    : "rounded-tl-md border border-border bg-card text-foreground"
              )}
            >
              {e.content}
            </div>
          </div>
        ))}

        {thinking && (
          <div className="flex items-center gap-2.5 text-sm text-muted-foreground">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/20">
              <Bot className="h-4 w-4 text-primary" />
            </div>
            Thinking…
          </div>
        )}
        <div ref={bottom} />
      </div>

      <div className="border-t border-border px-4 py-3">
        <div className="flex items-end gap-2">
          <Textarea
            value={value}
            rows={1}
            maxLength={MAX_LENGTH}
            disabled={thinking}
            placeholder="Ask PakTech AI…"
            className="max-h-40 min-h-10 resize-none"
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                ask(value);
              }
            }}
          />
          <Button
            size="icon-lg"
            onClick={() => ask(value)}
            disabled={thinking || !value.trim()}
            aria-label="Send"
          >
            <SendHorizontal />
          </Button>
        </div>
        <p className="mt-1.5 text-[11px] text-muted-foreground">
          AI can make mistakes. Don&apos;t paste secrets. Enter to send.
        </p>
      </div>
    </div>
  );
}
