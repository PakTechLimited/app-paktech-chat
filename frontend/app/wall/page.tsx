"use client";

import { AppShell } from "@/components/app-shell";
import { WallView } from "@/components/wall/wall-view";

export default function WallPage() {
  return (
    <AppShell>
      <WallView />
    </AppShell>
  );
}
