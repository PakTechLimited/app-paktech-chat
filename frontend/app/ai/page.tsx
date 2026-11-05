"use client";

import { AppShell } from "@/components/app-shell";
import { AiChat } from "@/components/ai/ai-chat";

export default function AiPage() {
  return (
    <AppShell>
      <AiChat />
    </AppShell>
  );
}
