"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth-context";
import { ThemeToggle } from "@/components/theme-toggle";
import { Mail, Lock, Eye, EyeOff, MessageCircle, LayoutGrid, Sparkles } from "lucide-react";

// three.js is only fetched when this screen renders, so signed-in pages never download it.
const LoginGlobe = dynamic(() => import("./login-globe"), { ssr: false });

const features = [
  {
    icon: MessageCircle,
    title: "Real-time chat",
    desc: "WebSocket-powered messaging",
    tile: "bg-primary/15 text-primary",
  },
  {
    icon: LayoutGrid,
    title: "Social wall",
    desc: "Share posts, likes and comments",
    tile: "bg-teal-600/15 text-teal-700 dark:text-teal-300",
  },
  {
    icon: Sparkles,
    title: "AI assistant",
    desc: "Claude-powered smart replies",
    tile: "bg-fuchsia-600/15 text-fuchsia-700 dark:text-fuchsia-300",
  },
];

export function AuthScreen() {
  return (
    <div className="relative flex flex-1 items-center justify-center p-5">
      <ThemeToggle className="absolute right-4 top-4" />
      <div className="w-full max-w-4xl flex rounded-2xl overflow-hidden border border-border min-h-[580px]">
        <LeftPanel />
        <RightPanel />
      </div>
    </div>
  );
}

function LeftPanel() {
  return (
    <div className="hidden md:flex flex-col justify-between w-[44%] p-10 relative overflow-hidden bg-linear-to-br from-violet-50 via-white to-fuchsia-50 dark:from-[#0b0a1e] dark:via-[#160d2e] dark:to-[#0d1629]">
      <LoginGlobe className="pointer-events-none absolute right-0 top-[118px] h-[150px] w-[150px]" />
      <div>
        <div className="flex items-center gap-3 mb-9">
          <HexLogo />
          <div>
            <h2 className="text-[17px] font-semibold text-foreground">
              PakTech Chat
            </h2>
            <p className="text-[11px] text-muted-foreground">
              Connect · Share · Discover
            </p>
          </div>
        </div>

        <div className="mb-7">
          <h1 className="text-[26px] font-bold text-foreground leading-tight mb-2">
            Your team&apos;s
            <br />
            <span className="bg-linear-to-r from-brand-text-from to-brand-text-to bg-clip-text text-transparent">
              real-time hub
            </span>
          </h1>
          <p className="text-[13px] text-muted-foreground leading-relaxed">
            Chat, share ideas, get AI help —<br />
            all in one place for your team.
          </p>
        </div>

        <div className="flex flex-col gap-2.5">
          {features.map((f) => (
            <div
              key={f.title}
              className="flex items-center gap-3 bg-card border border-border rounded-xl px-3.5 py-2.5"
            >
              <div
                className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${f.tile}`}
              >
                <f.icon size={16} />
              </div>
              <div>
                <h4 className="text-[12px] font-medium text-foreground">
                  {f.title}
                </h4>
                <p className="text-[11px] text-muted-foreground mt-0.5">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="text-[11px] text-muted-foreground border-t border-border pt-3.5 mt-8">
        Built on AKS · Redis Pub/Sub · Secure by design
      </div>
    </div>
  );
}

function RightPanel() {
  const [tab, setTab] = useState("login");

  return (
    <div className="flex-1 bg-background border-l border-border flex items-center justify-center p-8 md:p-11">
      <div className="w-full max-w-[340px]">
        <h2 className="text-xl font-semibold text-foreground mb-1">
          Welcome back
        </h2>
        <p className="text-[13px] text-muted-foreground mb-6">
          Sign in to continue to your workspace
        </p>

        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="w-full mb-5">
            <TabsTrigger value="login" className="flex-1">
              Sign in
            </TabsTrigger>
            <TabsTrigger value="register" className="flex-1">
              Create account
            </TabsTrigger>
          </TabsList>

          <TabsContent value="login">
            <LoginForm />
          </TabsContent>
          <TabsContent value="register">
            <RegisterForm />
          </TabsContent>
        </Tabs>

        <SocialButtons />

        <p className="text-center text-[11px] text-muted-foreground mt-2.5">
          By signing in you agree to our{" "}
          <button className="text-primary underline-offset-2 hover:underline">Terms</button> and{" "}
          <button className="text-primary underline-offset-2 hover:underline">Privacy Policy</button>
        </p>
      </div>
    </div>
  );
}

function LoginForm() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!email || !password) {
      setError("Please fill in all fields.");
      return;
    }
    setLoading(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3.5">
      <div>
        <label className="block text-[11px] font-medium text-muted-foreground mb-1.5 uppercase tracking-wide">
          Email
        </label>
        <div className="relative">
          <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground/50" size={15} />
          <Input
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>
      <div>
        <label className="block text-[11px] font-medium text-muted-foreground mb-1.5 uppercase tracking-wide">
          Password
        </label>
        <div className="relative">
          <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground/50" size={15} />
          <Input
            type={showPw ? "text" : "password"}
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="pl-9 pr-9"
          />
          <button
            type="button"
            onClick={() => setShowPw(!showPw)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground/50 hover:text-muted-foreground"
          >
            {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
          </button>
        </div>
      </div>
      <div className="flex justify-between items-center text-[12px]">
        <label className="flex items-center gap-1.5 text-muted-foreground cursor-pointer">
          <input type="checkbox" className="accent-primary w-3 h-3" />
          Remember me
        </label>
        <button type="button" className="text-primary">
          Forgot password?
        </button>
      </div>
      {error && <p className="text-[12px] text-destructive text-center">{error}</p>}
      <Button
        type="submit"
        disabled={loading}
        className="w-full bg-linear-to-r from-brand-from to-brand-to hover:opacity-90 text-white"
      >
        {loading ? "Signing in..." : "Sign in →"}
      </Button>
    </form>
  );
}

function RegisterForm() {
  const { register } = useAuth();
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!username || !email || !password) {
      setError("Please fill in all required fields.");
      return;
    }
    setLoading(true);
    try {
      await register(username, email, password, displayName || undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3.5">
      <div className="grid grid-cols-2 gap-2.5">
        <div>
          <label className="block text-[11px] font-medium text-muted-foreground mb-1.5 uppercase tracking-wide">
            Username
          </label>
          <Input
            placeholder="your_handle"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-[11px] font-medium text-muted-foreground mb-1.5 uppercase tracking-wide">
            Display name
          </label>
          <Input
            placeholder="Ali Haidry"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
          />
        </div>
      </div>
      <div>
        <label className="block text-[11px] font-medium text-muted-foreground mb-1.5 uppercase tracking-wide">
          Email
        </label>
        <div className="relative">
          <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground/50" size={15} />
          <Input
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>
      <div>
        <label className="block text-[11px] font-medium text-muted-foreground mb-1.5 uppercase tracking-wide">
          Password
        </label>
        <div className="relative">
          <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground/50" size={15} />
          <Input
            type={showPw ? "text" : "password"}
            placeholder="Min 8 characters"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="pl-9 pr-9"
          />
          <button
            type="button"
            onClick={() => setShowPw(!showPw)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground/50 hover:text-muted-foreground"
          >
            {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
          </button>
        </div>
      </div>
      {error && <p className="text-[12px] text-destructive text-center">{error}</p>}
      <Button
        type="submit"
        disabled={loading}
        className="w-full bg-linear-to-r from-brand-from to-brand-to hover:opacity-90 text-white"
      >
        {loading ? "Creating account..." : "Create account →"}
      </Button>
    </form>
  );
}

function SocialButtons() {
  return (
    <>
      <div className="flex items-center gap-2.5 my-4">
        <div className="flex-1 h-px bg-gradient-to-r from-transparent to-border" />
        <span className="text-[11px] text-muted-foreground">or continue with</span>
        <div className="flex-1 h-px bg-gradient-to-l from-transparent to-border" />
      </div>
      <div className="grid grid-cols-2 gap-2 mb-3.5">
        <Button variant="outline" className="text-[13px]">
          Google
        </Button>
        <Button variant="outline" className="text-[13px]">
          GitHub
        </Button>
      </div>
    </>
  );
}

function HexLogo() {
  return (
    <svg width="52" height="52" viewBox="0 0 52 52" fill="none">
      <polygon
        points="26,5 46,16 46,36 26,47 6,36 6,16"
        fill="none"
        className="stroke-primary/40"
        strokeWidth="1"
      />
      <polygon
        points="26,12 39,19 39,33 26,40 13,33 13,19"
        fill="none"
        className="stroke-primary/50"
        strokeWidth=".8"
        strokeDasharray="3 2"
      />
      <polygon
        points="26,18 35,23 35,29 26,34 17,29 17,23"
        className="fill-card stroke-primary"
        stroke="currentColor"
        strokeWidth="1.4"
      />
      <path
        d="M22 27 L26 29 L30 27"
        stroke="#c46bb5"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      <path
        d="M26 29 L26 33"
        stroke="#4ecdc4"
        strokeWidth="1.6"
        strokeLinecap="round"
        fill="none"
      />
      <circle cx="26" cy="5" r="3" fill="#7c5cbf" />
      <circle cx="46" cy="16" r="2.5" fill="#9b7fd4" />
      <circle cx="46" cy="36" r="2.5" fill="#c46bb5" />
      <circle cx="26" cy="47" r="3" fill="#4ecdc4" />
      <circle cx="6" cy="36" r="2.5" fill="#9b7fd4" />
      <circle cx="6" cy="16" r="2.5" fill="#7c5cbf" />
    </svg>
  );
}
