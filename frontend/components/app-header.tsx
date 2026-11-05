"use client";

import Link from "next/link";
import { LogOut, Shield } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export function AppHeader() {
  const { user, logout } = useAuth();
  if (!user) return null;

  const name = user.display_name || user.username;

  return (
    <header className="flex items-center justify-between border-b border-border px-4 py-3 md:px-6">
      <Link href="/" className="font-semibold text-foreground">
        PakTech Chat
      </Link>

      <div className="flex items-center gap-3">
        {user.role === "admin" && (
          <Button asChild variant="ghost" size="sm">
            <Link href="/admin">
              <Shield className="mr-1.5 h-4 w-4" />
              Admin
            </Link>
          </Button>
        )}
        <div className="flex items-center gap-2">
          <Avatar className="h-7 w-7">
            <AvatarFallback
              className="text-[10px] font-semibold text-white"
              style={{ backgroundColor: user.avatar_color }}
            >
              {name.slice(0, 2).toUpperCase()}
            </AvatarFallback>
          </Avatar>
          <span className="hidden text-sm text-foreground sm:inline">{name}</span>
          {user.role === "admin" && <Badge variant="secondary">Admin</Badge>}
        </div>
        <Button variant="outline" size="sm" onClick={logout}>
          <LogOut className="mr-1.5 h-4 w-4" />
          Log out
        </Button>
      </div>
    </header>
  );
}
