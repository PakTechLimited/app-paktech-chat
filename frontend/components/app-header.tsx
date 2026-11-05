"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bot, LayoutGrid, LogOut, MessageSquare, Shield } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Chat", icon: MessageSquare },
  { href: "/wall", label: "Wall", icon: LayoutGrid },
  { href: "/ai", label: "AI", icon: Bot },
];

export function AppHeader() {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  if (!user) return null;

  const name = user.display_name || user.username;

  return (
    <header className="flex items-center justify-between border-b border-border px-4 py-3 md:px-6">
      <div className="flex items-center gap-4 md:gap-6">
        <Link href="/" className="hidden font-semibold text-foreground sm:block">
          PakTech Chat
        </Link>
        <nav className="flex items-center gap-1">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm transition-colors",
                  active
                    ? "bg-primary/15 font-medium text-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                <Icon className="h-4 w-4" />
                {label}
              </Link>
            );
          })}
        </nav>
      </div>

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
