"use client";

import { useAuth } from "@/lib/auth-context";
import { AuthScreen } from "@/components/auth/auth-screen";
import { AppHeader } from "@/components/app-header";
import { ChatShell } from "@/components/chat/chat-shell";

export default function Home() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-muted-foreground text-sm">Loading...</p>
      </div>
    );
  }

  if (!user) {
    return <AuthScreen />;
  }

  return (
    <div className="flex h-dvh flex-col">
      <AppHeader />
      <ChatShell />
    </div>
  );
}
