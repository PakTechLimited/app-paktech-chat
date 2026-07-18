"use client";

import { useAuth } from "@/lib/auth-context";
import { AuthScreen } from "@/components/auth/auth-screen";

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
    <div className="flex flex-1 items-center justify-center">
      <div className="text-center">
        <p className="text-foreground text-lg font-medium mb-2">
          Welcome, {user.display_name || user.username}
        </p>
        <p className="text-muted-foreground text-sm">
          Chat app shell coming in the next step.
        </p>
      </div>
    </div>
  );
}
