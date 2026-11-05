"use client";

import { useState } from "react";
import { SendHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

const MAX_LENGTH = 4000;

interface Props {
  roomName: string;
  disabled: boolean;
  onSend: (content: string) => boolean;
  onTyping: () => void;
}

export function MessageInput({ roomName, disabled, onSend, onTyping }: Props) {
  const [value, setValue] = useState("");

  function submit() {
    const text = value.trim();
    if (!text || disabled) return;
    if (onSend(text)) setValue("");
  }

  return (
    <div className="border-t border-border px-4 py-3 md:px-6">
      <div className="flex items-end gap-2">
        <Textarea
          value={value}
          rows={1}
          maxLength={MAX_LENGTH}
          disabled={disabled}
          placeholder={disabled ? "Reconnecting…" : `Message #${roomName}`}
          className="max-h-40 min-h-10 resize-none"
          onChange={(e) => {
            setValue(e.target.value);
            onTyping();
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
        />
        <Button
          size="icon-lg"
          onClick={submit}
          disabled={disabled || !value.trim()}
          aria-label="Send message"
        >
          <SendHorizontal />
        </Button>
      </div>
      <p className="mt-1.5 text-[11px] text-muted-foreground">
        Enter to send · Shift+Enter for a new line
      </p>
    </div>
  );
}
