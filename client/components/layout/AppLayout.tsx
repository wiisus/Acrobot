import { Outlet } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { User, Settings2, Info, Search } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";
import { useEffect, useState } from "react";

export function AppLayout() {
  return (
    <div className="min-h-screen w-full bg-gradient-to-b from-[#0a0c12] via-[#0a0c12] to-[#0b0f1a] text-foreground selection:bg-brand-blue/30 selection:text-white">
      <div className="pointer-events-none fixed inset-0 z-0">
        <div className="absolute -top-32 -left-32 h-80 w-80 rounded-full bg-brand-blue/20 blur-3xl" />
        <div className="absolute top-1/3 -right-24 h-72 w-72 rounded-full bg-brand-pink/20 blur-3xl" />
        <div className="absolute bottom-10 left-1/4 h-64 w-64 rounded-full bg-brand-blue/20 blur-3xl" />
      </div>
      <div className="relative z-10 flex">
        <main className="flex min-h-screen w-full flex-1 flex-col">
          <Header />
          <div className="mx-auto w-full max-w-6xl flex-1 p-4 md:p-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}

function Header() {
  return (
    <header className="sticky top-0 z-20 bg-transparent backdrop-blur supports-[backdrop-filter]:bg-transparent">
      <div className="flex items-center gap-3 px-4 py-3 md:px-6">
        <div className="relative hidden flex-1 items-center md:flex">
          <Search className="pointer-events-none absolute left-3 h-4 w-4 text-white/60" />
          <Input
            className={cn(
              "h-10 w-full border-white/10 bg-white/5 pl-9 text-white placeholder:text-white/40 focus-visible:ring-brand-blue",
              "rounded-xl"
            )}
            placeholder="Search chats, files, commands..."
          />
        </div>
        <div className="ml-auto flex items-center gap-2">
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="ghost" className="rounded-xl border border-white/15 bg-white/10 text-white hover:bg-white/15">
                <Info className="h-4 w-4 text-white/90" />
                <span className="sr-only">Info</span>
              </Button>
            </DialogTrigger>
            <DialogContent className="border-white/10 bg-[#0b0f1a] text-white">
              <DialogHeader>
                <DialogTitle className="font-semibold tracking-tight">Information Center</DialogTitle>
              </DialogHeader>
              <p className="text-sm text-white/70">
                This utility interface features neon-accented dark UI, smooth animations, and high-performance controls suitable for gaming.
              </p>
            </DialogContent>
          </Dialog>

          <Dialog>
            <DialogTrigger asChild>
              <Button variant="ghost" className="rounded-xl border border-white/15 bg-white/10 text-white hover:bg-white/15">
                <Settings2 className="h-4 w-4 text-white/90" />
                <span className="sr-only">Settings</span>
              </Button>
            </DialogTrigger>
            <DialogContent className="border-white/10 bg-[#0b0f1a] text-white">
              <DialogHeader>
                <DialogTitle className="font-semibold tracking-tight">Appearance</DialogTitle>
              </DialogHeader>
              <ThemeControls />
            </DialogContent>
          </Dialog>

          <Dialog>
            <DialogTrigger asChild>
              <Button className="rounded-xl bg-gradient-to-r from-brand-blue to-brand-pink text-white shadow-[0_0_20px_theme(colors.brand.blue/30)] hover:shadow-[0_0_26px_theme(colors.brand.pink/35)]">
                <User className="h-4 w-4" />
                Profile
              </Button>
            </DialogTrigger>
            <DialogContent className="border-white/10 bg-[#0b0f1a] text-white">
              <DialogHeader>
                <DialogTitle className="font-semibold tracking-tight">Profile Editor</DialogTitle>
              </DialogHeader>
              <div className="grid gap-3">
                <label className="text-sm text-white/70">Username</label>
                <Input className="rounded-lg border-white/10 bg-white/5 text-white placeholder:text-white/40 focus-visible:ring-brand-blue" placeholder="Enter username" />
                <label className="text-sm text-white/70">Config Name</label>
                <Input className="rounded-lg border-white/10 bg-white/5 text-white placeholder:text-white/40 focus-visible:ring-brand-pink" placeholder="My PvP Preset" />
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>
    </header>
  );
}

function ThemeControls() {
  const getLS = (k: string) => {
    try { return localStorage.getItem(k); } catch { return null; }
  };
  const setLS = (k: string, v: string) => {
    try { localStorage.setItem(k, v); } catch {}
  };
  const [highContrast, setHighContrast] = useState<boolean>(() => getLS("winai_hc") === "1");
  const [accent, setAccent] = useState<string>(() => getLS("winai_accent") || "blue-pink");
  const [bubble, setBubble] = useState<string>(() => getLS("winai_bubble") || "glass");

  useEffect(() => {
    document.documentElement.classList.toggle("hc", highContrast);
    setLS("winai_hc", highContrast ? "1" : "0");
    window.dispatchEvent(new Event("themechange"));
  }, [highContrast]);

  useEffect(() => {
    // Update accent variables
    if (accent === "blue-pink") {
      document.documentElement.style.setProperty("--brand-blue", "199 100% 60%");
      document.documentElement.style.setProperty("--brand-pink", "312 95% 62%");
    } else if (accent === "blue") {
      document.documentElement.style.setProperty("--brand-blue", "199 100% 60%");
      document.documentElement.style.setProperty("--brand-pink", "199 100% 60%");
    } else if (accent === "pink") {
      document.documentElement.style.setProperty("--brand-blue", "312 95% 62%");
      document.documentElement.style.setProperty("--brand-pink", "312 95% 62%");
    }
    setLS("winai_accent", accent);
    window.dispatchEvent(new Event("themechange"));
  }, [accent]);

  useEffect(() => {
    document.documentElement.dataset.bubble = bubble;
    setLS("winai_bubble", bubble);
    window.dispatchEvent(new Event("themechange"));
  }, [bubble]);

  return (
    <div className="grid gap-4 text-sm">
      <div className="flex items-center justify-between rounded-md border border-white/10 bg-white/5 p-3">
        <div>
          <div className="font-medium text-white">High contrast</div>
          <div className="text-xs text-white/60">Boosts icon/text contrast in the top bar and UI</div>
        </div>
        <Switch checked={highContrast} onCheckedChange={setHighContrast as any} className="data-[state=checked]:bg-brand-blue data-[state=unchecked]:bg-white/20" />
      </div>

      <div className="rounded-md border border-white/10 bg-white/5 p-3">
        <div className="mb-2 font-medium text-white">Accent</div>
        <div className="flex gap-2">
          <Button onClick={() => setAccent("blue-pink")} className={cn("rounded-md px-3 py-1 text-xs", accent === "blue-pink" ? "bg-gradient-to-r from-brand-blue to-brand-pink" : "bg-white/10")}>Blue/Pink</Button>
          <Button onClick={() => setAccent("blue")} className={cn("rounded-md px-3 py-1 text-xs", accent === "blue" ? "bg-brand-blue" : "bg-white/10")}>Blue</Button>
          <Button onClick={() => setAccent("pink")} className={cn("rounded-md px-3 py-1 text-xs", accent === "pink" ? "bg-brand-pink" : "bg-white/10")}>Pink</Button>
        </div>
      </div>

      <div className="rounded-md border border-white/10 bg-white/5 p-3">
        <div className="mb-2 font-medium text-white">Chat bubble</div>
        <div className="flex gap-2">
          <Button onClick={() => setBubble("glass")} className={cn("rounded-md px-3 py-1 text-xs", bubble === "glass" ? "bg-white/15" : "bg-white/10")}>Glass</Button>
          <Button onClick={() => setBubble("solid")} className={cn("rounded-md px-3 py-1 text-xs", bubble === "solid" ? "bg-white/15" : "bg-white/10")}>Solid</Button>
        </div>
      </div>
    </div>
  );
}
