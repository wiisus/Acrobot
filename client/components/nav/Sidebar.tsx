import { cn } from "@/lib/utils";
import { MessageSquare, Sparkles, Workflow, Folder, Settings } from "lucide-react";
import { useState } from "react";

const tabs = [
  { key: "chat", label: "Chat", icon: <MessageSquare className="h-4 w-4" /> },
  { key: "skills", label: "Skills", icon: <Sparkles className="h-4 w-4" /> },
  { key: "automations", label: "Automations", icon: <Workflow className="h-4 w-4" /> },
  { key: "files", label: "Files", icon: <Folder className="h-4 w-4" /> },
  { key: "settings", label: "Settings", icon: <Settings className="h-4 w-4" /> },
];

export function Sidebar() {
  const [active, setActive] = useState("modules");
  return (
    <aside className="sticky top-0 hidden h-screen w-60 shrink-0 border-r border-white/5 bg-[#0a0c12]/80 backdrop-blur supports-[backdrop-filter]:bg-[#0a0c12]/60 md:block">
      <div className="flex h-14 items-center gap-2 border-b border-white/5 px-4">
        <div className="relative">
          <div className="absolute -inset-1 rounded-lg bg-gradient-to-r from-brand-blue to-brand-pink opacity-60 blur" />
          <div className="relative rounded-lg bg-[#0b0f1a] px-2 py-1 text-sm font-semibold tracking-wider text-white">WinAI</div>
        </div>
      </div>
      <nav className="p-3">
        <ul className="space-y-1">
          {tabs.map((t) => (
            <li key={t.key}>
              <button
                onClick={() => setActive(t.key)}
                className={cn(
                  "group flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-white/80 transition",
                  active === t.key
                    ? "bg-white/10 text-white shadow-[0_0_0_1px_rgba(255,255,255,.08),0_8px_24px_-8px_theme(colors.brand.blue/50)]"
                    : "hover:bg-white/5 hover:text-white",
                )}
              >
                <span
                  className={cn(
                    "grid place-items-center rounded-md p-1 transition",
                    active === t.key
                      ? "bg-gradient-to-br from-brand-blue/30 to-brand-pink/30 text-white"
                      : "bg-white/5 text-white/70 group-hover:text-white",
                  )}
                >
                  {t.icon}
                </span>
                <span>{t.label}</span>
              </button>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  );
}
