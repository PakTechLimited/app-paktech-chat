"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import type { AdminUser, PlatformStats } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Users, MessageSquare, LayoutGrid, UserCheck } from "lucide-react";
import { toast } from "sonner";

export default function AdminPage() {
  const { user, token, isLoading } = useAuth();
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loadingData, setLoadingData] = useState(true);

  useEffect(() => {
    if (!token || !user || user.role !== "admin") return;
    Promise.all([api.admin.stats(token), api.admin.listUsers(token)])
      .then(([statsData, usersData]) => {
        setStats(statsData);
        setUsers(usersData);
      })
      .catch(() => toast.error("Failed to load admin data"))
      .finally(() => setLoadingData(false));
  }, [token, user]);

  async function toggleUserStatus(target: AdminUser) {
    if (!token) return;
    try {
      const result = target.is_active
        ? await api.admin.deactivateUser(token, target.id)
        : await api.admin.activateUser(token, target.id);
      setUsers((prev) =>
        prev.map((u) => (u.id === target.id ? { ...u, is_active: result.is_active } : u))
      );
      toast.success(
        result.is_active ? `${target.username} activated` : `${target.username} deactivated`
      );
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Action failed");
    }
  }

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-muted-foreground text-sm">Loading...</p>
      </div>
    );
  }

  if (!user || user.role !== "admin") {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="text-center">
          <p className="text-foreground text-lg font-medium mb-2">Access denied</p>
          <p className="text-muted-foreground text-sm">
            You need admin privileges to view this page.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 md:p-10">
      <div className="max-w-5xl mx-auto">
        <h1 className="text-xl font-semibold text-foreground mb-1">Admin panel</h1>
        <p className="text-sm text-muted-foreground mb-6">
          Platform overview and user management
        </p>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
          <StatCard icon={Users} label="Total users" value={stats?.total_users} />
          <StatCard icon={UserCheck} label="Active users" value={stats?.active_users} />
          <StatCard icon={MessageSquare} label="Messages" value={stats?.total_messages} />
          <StatCard icon={LayoutGrid} label="Posts" value={stats?.total_posts} />
        </div>

        <Separator className="mb-6" />

        <h2 className="text-sm font-medium text-foreground mb-3">All users</h2>

        {loadingData ? (
          <p className="text-sm text-muted-foreground">Loading users...</p>
        ) : (
          <div className="space-y-2">
            {users.map((u) => (
              <div
                key={u.id}
                className="flex items-center gap-3 bg-card border border-border rounded-lg px-4 py-3"
              >
                <Avatar className="w-9 h-9">
                  <AvatarFallback
                    style={{ background: u.avatar_color || "#7c5cbf" }}
                    className="text-white text-xs font-semibold"
                  >
                    {(u.display_name || u.username).slice(0, 2).toUpperCase()}
                  </AvatarFallback>
                </Avatar>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-foreground truncate">
                      {u.display_name || u.username}
                    </p>
                    {u.role === "admin" && (
                      <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                        Admin
                      </Badge>
                    )}
                    {!u.is_active && (
                      <Badge variant="destructive" className="text-[10px] px-1.5 py-0">
                        Deactivated
                      </Badge>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground truncate">{u.email}</p>
                </div>

                {u.id !== user.id && (
                  <Button
                    variant={u.is_active ? "outline" : "default"}
                    size="sm"
                    onClick={() => toggleUserStatus(u)}
                  >
                    {u.is_active ? "Deactivate" : "Activate"}
                  </Button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: number | undefined;
}) {
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <Icon size={16} className="text-primary mb-2" />
      <p className="text-2xl font-semibold text-foreground">{value ?? "—"}</p>
      <p className="text-xs text-muted-foreground mt-0.5">{label}</p>
    </div>
  );
}
