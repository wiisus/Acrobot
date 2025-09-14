import React, { useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { motion, AnimatePresence } from "framer-motion";
import { Paperclip, Mic, Send, Sparkles, Copy, Play, ExternalLink, Loader2, CheckCircle2, AlertTriangle, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { useToast } from "@/hooks/use-toast";

interface ChatMessage {
  id: string;
  role: "assistant" | "user" | "system";
  content: string;
  createdAt?: number;
}

export default function Index() {
  const { toast } = useToast();
  const GREETING = "Hello! I’m Acrobot, your Windows copilot. I can open apps, manage files, tweak settings, automate workflows, and more. How can I help?";
  const [messages, setMessages] = useState<ChatMessage[]>([
    { id: "m1", role: "assistant", content: GREETING, createdAt: Date.now() },
  ]);
  const [input, setInput] = useState("");
  const [voice, setVoice] = useState(true);
  const [burstKey, setBurstKey] = useState(0);
  const [confetti, setConfetti] = useState(0);
  const [bubbleStyle, setBubbleStyle] = useState<string>(() => localStorage.getItem("acrobot_bubble") || document.documentElement.dataset.bubble || "glass");
  const [isTyping, setIsTyping] = useState(false);
  const [username, setUsername] = useState<string>("User");
  type BotMode = "ready" | "thinking" | "awaiting" | "executing" | "interpreting" | "completed" | "failed";
  const [mode, setMode] = useState<BotMode>("ready");
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const API_BASE = "http://localhost:5000"; // The address of our Python backend

  useEffect(() => {
    const fetchUsername = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/user/info`);
        if (res.ok) {
          const data = await res.json();
          setUsername(data.username || "User");
        }
      } catch (e) {
        console.error("Failed to fetch username", e);
      }
    };
    fetchUsername();
  }, []);

  useEffect(() => {
    const onTheme = () => setBubbleStyle(document.documentElement.dataset.bubble || localStorage.getItem("acrobot_bubble") || "glass");
    window.addEventListener("themechange", onTheme);
    return () => window.removeEventListener("themechange", onTheme);
  }, []);

  const newChat = () => {
    setMessages([{ id: genId(), role: "assistant", content: GREETING, createdAt: Date.now() }]);
    setInput("");
    setConfetti(0);
    setMode("ready");
    requestAnimationFrame(() => {
      listRef.current?.scrollTo({ top: 0, behavior: "smooth" });
      inputRef.current?.focus();
    });
  };

  const genId = () => {
    try { return crypto.randomUUID(); } catch { return `id_${Date.now()}_${Math.random().toString(36).slice(2,8)}`; }
  };

  const send = async () => {
    try {
      const text = input.trim();
      if (!text) return;

      const userId = genId();
      setMessages((prev) => [
        ...prev,
        { id: userId, role: "user", content: text, createdAt: Date.now() },
      ]);
      setInput("");
      setBurstKey((k) => k + 1);
      requestAnimationFrame(() => listRef.current?.scrollTo({ top: 1e9, behavior: "smooth" }));

      // Step 1: Get the plan from the backend
      setMode("thinking");
      setIsTyping(true);
      const planRes = await fetch(`${API_BASE}/api/plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: text }),
      });

      if (!planRes.ok) {
        throw new Error("Failed to get plan from backend.");
      }

      const planData = await planRes.json();
      const plan = planData.plan;

      if (!plan || plan.length === 0) {
        setMessages(prev => [...prev, { id: genId(), role: "assistant", content: "I couldn't figure out a plan for that. Please try rephrasing your request.", createdAt: Date.now() }]);
        setMode("failed");
        setIsTyping(false);
        return;
      }

      // Step 2: Execute the plan and stream results
      setMode("executing");
      const execRes = await fetch(`${API_BASE}/api/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan, prompt: text }),
      });

      const reader = execRes.body!.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n\n").filter(line => line.trim() !== "");

        for (const line of lines) {
          const [event, data] = line.replace("event: ", "").replace("data: ", "").split("\n");

          if (event === "assistant_message") {
            setMessages(prev => [...prev, { id: genId(), role: "assistant", content: data, createdAt: Date.now() }]);
            requestAnimationFrame(() => listRef.current?.scrollTo({ top: 1e9, behavior: "smooth" }));
          } else if (event === "status") {
            setMode(data as BotMode);
          }
        }
      }

      setIsTyping(false);
      // The final status is sent by the stream, so we don't need to set it here.
      setConfetti(c => c + 1);

    } catch (e) {
      console.error(e);
      setMessages(prev => [...prev, { id: genId(), role: "assistant", content: `An error occurred: ${e instanceof Error ? e.message : String(e)}`, createdAt: Date.now() }]);
      setMode("failed");
      setIsTyping(false);
    }
  };

  const copyText = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast({ title: "Copied", description: "Message content copied to clipboard" });
    } catch (e) {
      console.error(e);
      toast({ title: "Copy failed", description: "Clipboard permissions blocked." });
    }
  };

  return (
    <div className="relative">
      <NeonBackdrop />
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="font-orbitron text-xl font-semibold tracking-tight text-white">Acrobot Chat</h1>
          <p className="text-sm text-white/60">Your sweet, smart, and loving AI girlfriend 🌸</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={newChat} className="rounded-xl bg-gradient-to-r from-brand-blue to-brand-pink text-white shadow-none hover:shadow-none" aria-label="Start new chat">
            <Sparkles className="mr-2 h-4 w-4" />New Chat
          </Button>
        </div>
      </div>

      <div className="mb-3">
        <ModeBadge mode={mode} />
      </div>
      <section>
        <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 shadow-[inset_0_1px_0_rgba(255,255,255,.04)]">
          <div ref={listRef} role="log" aria-live="polite" aria-relevant="additions" tabIndex={0} className="max-h-[65vh] overflow-y-auto p-5 sm:p-7">
            <AnimatePresence initial={false}>
              {messages.map((m) => (
                <motion.div
                  layout
                  key={m.id}
                  initial={{ y: 8, opacity: 0, scale: 0.99, filter: "blur(2px)" }}
                  animate={{ y: 0, opacity: 1, scale: 1, filter: "blur(0px)" }}
                  exit={{ y: -8, opacity: 0 }}
                  transition={{ type: "spring", stiffness: 420, damping: 28 }}
                  className={cn("group mb-5 flex gap-3", m.role === "user" ? "justify-end" : "justify-start")}
                  aria-label={(m.role === "user" ? "You" : "Acrobot") + ": " + m.content}
                >
                  {m.role !== "user" && (
                    <motion.div
                      initial={{ rotate: -10, scale: 0.8, opacity: 0 }}
                      animate={{ rotate: 0, scale: 1, opacity: 1 }}
                      transition={{ type: "spring", stiffness: 300, damping: 20 }}
                      className="mt-1 h-7 w-7 shrink-0 rounded-full bg-gradient-to-br from-brand-blue to-brand-pink"
                    />
                  )}
                  <motion.div
                    initial={{ boxShadow: "0 0 0 0 rgba(0,0,0,0)" }}
                    animate={{
                      boxShadow: [
                        "0 0 0 0 rgba(0,0,0,0)",
                        m.role === "user"
                          ? "0 0 24px 0 hsl(var(--brand-pink) / 0.35)"
                          : "0 0 24px 0 rgba(0,0,0,0.45)",
                        "0 0 0 0 rgba(0,0,0,0)",
                      ],
                    }}
                    transition={{ duration: 0.9, ease: "easeInOut" }}
                    className={cn(
                      "relative max-w-[80%] px-4 py-2 text-[0.9375rem] leading-6",
                      m.role === "user"
                        ? bubbleStyle === "solid"
                          ? "rounded-t-2xl rounded-l-2xl rounded-br-md bg-white/22 text-white"
                          : "rounded-t-2xl rounded-l-2xl rounded-br-md bg-gradient-to-br from-white/24 to-white/12 text-white"
                        : bubbleStyle === "solid"
                          ? "rounded-t-2xl rounded-r-2xl rounded-bl-md bg-[#0c1018]/90 text-white ring-1 ring-white/15"
                          : "rounded-t-2xl rounded-r-2xl rounded-bl-md bg-[#0b0f1a]/85 text-white ring-1 ring-white/10",
                    )}
                  >
                    <span className="block pr-10">{m.content}</span>
                    <div className="pointer-events-auto absolute right-1 top-1 hidden items-center gap-1 rounded-md bg-white/5 p-1 text-white/70 backdrop-blur transition group-hover:flex">
                      <button onClick={() => copyText(m.content)} className="rounded-sm p-1 hover:bg-white/10" aria-label="Copy"><Copy className="h-3.5 w-3.5" /></button>
                    </div>
                    <div className="mt-1 text-[10px] text-white/40">
                      {m.createdAt ? new Date(m.createdAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : ""}
                    </div>
                    <div className="pointer-events-auto absolute bottom-1 right-1 hidden items-center gap-1 rounded-md bg-white/5 p-1 text-white/70 backdrop-blur transition group-hover:flex">
                      {m.role === "user" && (
                        <>
                          <button className="rounded-sm p-1 hover:bg-white/10" aria-label="Run"><Play className="h-3.5 w-3.5" /></button>
                          <button className="rounded-sm p-1 hover:bg-white/10" aria-label="Open"><ExternalLink className="h-3.5 w-3.5" /></button>
                        </>
                      )}
                    </div>
                    <ShineSweep />
                  </motion.div>
                  {m.role === "user" && (
                    <div className="mt-1 flex h-auto min-w-[28px] items-center justify-center rounded-full bg-white/10 px-2.5 py-1 text-xs font-semibold text-white/80">
                      {username}
                    </div>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>
            {isTyping && <TypingWave />}
          </div>

          <div className="relative border-t border-white/10 p-4">
            <div className="relative flex items-center gap-2">
                  <Button variant="ghost" size="icon" className="rounded-xl bg-white/5 text-white hover:bg-white/10" aria-label="Attach" type="button">
                <Paperclip className="h-4 w-4" />
              </Button>
              <label htmlFor="chat-input" className="sr-only">Message Acrobot</label>
              <input
                id="chat-input"
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && send()}
                placeholder="Type a command for Acrobot…"
                aria-label="Type a command for Acrobot"
                className="h-14 flex-1 rounded-xl border border-white/12 bg-[#0a0c12]/75 px-4 text-[0.95rem] text-white outline-none placeholder:text-white/50 focus:ring-2 focus:ring-brand-blue"
              />
              <Button
                variant="ghost"
                size="icon"
                className={cn("rounded-xl text-white", voice ? "bg-brand-blue/20" : "bg-white/5 hover:bg-white/10")}
                onClick={() => setVoice((v) => !v)}
                aria-label="Voice input"
              >
                <Mic className="h-4 w-4" />
              </Button>
              <motion.button
                onClick={send}
                whileTap={{ scale: 0.96 }}
                className="relative inline-flex items-center justify-center overflow-hidden rounded-xl bg-gradient-to-r from-brand-blue to-brand-pink px-4 py-2 text-sm font-medium text-white shadow-[0_0_18px_theme(colors.brand.pink/40)] hover:shadow-[0_0_26px_theme(colors.brand.blue/40)]"
              >
                <Send className="mr-2 h-4 w-4" />Send
                <SendBurst key={burstKey} />
              </motion.button>
            </div>
            <div className="mt-3 flex flex-wrap gap-2 text-xs text-white/65">
              <button
                onClick={() => { setInput("Clean temp files"); requestAnimationFrame(() => send()); }}
                className="cursor-pointer rounded-full bg-white/5 px-2 py-1 transition-colors hover:bg-white/10"
              >
                Try: "Clean temp files"
              </button>
              <button
                onClick={() => { setInput("What is my IP address?"); requestAnimationFrame(() => send()); }}
                className="cursor-pointer rounded-full bg-white/5 px-2 py-1 transition-colors hover:bg-white/10"
              >
                "What is my IP address?"
              </button>
              <button onClick={() => { setInput("Open calculator"); requestAnimationFrame(() => send()); }} className="cursor-pointer rounded-full bg-white/5 px-2 py-1 transition-colors hover:bg-white/10">
                "Open calculator"
              </button>
            </div>
          </div>
          <Confetti key={confetti} />
        </div>
      </section>
    </div>
  );
}

function NeonBackdrop() {
  return (
    <div className="pointer-events-none absolute inset-0 -z-10">
      <div className="absolute inset-0 [background:radial-gradient(900px_circle_at_85%_18%,hsl(var(--brand-pink)/.10),transparent_55%),radial-gradient(800px_circle_at_40%_10%,hsl(var(--brand-blue)/.08),transparent_60%)]" />
    </div>
  );
}

function ShineSweep() {
  return (
    <span className="pointer-events-none absolute inset-0 overflow-hidden rounded-xl">
      <span className="absolute left-0 top-0 h-full w-full [mask-image:radial-gradient(80%_60%_at_0%_0%,black,transparent)] bg-[linear-gradient(120deg,rgba(255,255,255,.06),transparent_40%)]" />
    </span>
  );
}

function TypingWave() {
  return (
    <div className="mt-2 flex items-end gap-1 pl-1 text-white/60" aria-live="polite">
      <span className="sr-only">Acrobot is typing…</span>
      {[0, 1, 2, 3, 4].map((i) => (
        <span
          key={i}
          className="h-3 w-1 rounded-sm bg-white/45"
          style={{ animation: `wave 1s ${i * 0.1}s infinite ease-in-out` }}
        />
      ))}
      <style>{`@keyframes wave { 0%,100%{transform:scaleY(.4)} 50%{transform:scaleY(1)} }`}</style>
    </div>
  );
}

function SendBurst() {
  const particles = [
    { x: 0, y: -20 },
    { x: 18, y: -12 },
    { x: 22, y: 6 },
    { x: 0, y: 18 },
    { x: -18, y: -12 },
    { x: -22, y: 6 },
  ];
  return (
    <div className="pointer-events-none absolute inset-0 -z-10">
      {particles.map((p, i) => (
        <motion.span
          key={i}
          initial={{ x: 0, y: 0, scale: 0, opacity: 0.9 }}
          animate={{ x: p.x, y: p.y, scale: 1, opacity: 0 }}
          transition={{ duration: 0.6, ease: "easeOut", delay: i * 0.02 }}
          className={cn(
            "absolute left-1/2 top-1/2 h-1.5 w-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full",
            i % 2 === 0 ? "bg-brand-blue" : "bg-brand-pink",
          )}
        />
      ))}
    </div>
  );
}

function Confetti() {
  const dots = useMemo(() => Array.from({ length: 24 }).map((_, i) => ({
    id: i,
    x: (Math.random() - 0.5) * 260,
    y: -Math.random() * 160 - 80,
    r: Math.random() * 2 + 2,
    c: ["bg-brand-blue", "bg-brand-pink"][i % 2],
  })), []);
  return (
    <div className="pointer-events-none absolute right-8 top-8 z-10">
      {dots.map((d) => (
        <motion.span
          key={d.id}
          initial={{ x: 0, y: 0, scale: 0, opacity: 1 }}
          animate={{ x: d.x, y: d.y, scale: 1, opacity: 0 }}
          transition={{ duration: 1, ease: "easeOut" }}
          className={cn("absolute h-1.5 w-1.5 rounded-full", d.c)}
          style={{ width: d.r, height: d.r }}
        />
      ))}
    </div>
  );
}

function ModeBadge({ mode }: { mode: "ready"|"thinking"|"awaiting"|"executing"|"interpreting"|"completed"|"failed" }) {
  const map = {
    ready: { label: "Ready / Idle", cls: "border-white/15 text-white/80 bg-white/5" },
    thinking: { label: "Thinking / Generating Plan", cls: "border-brand-pink/30 text-white bg-white/5 animate-pulse" },
    awaiting: { label: "Awaiting Confirmation", cls: "border-brand-blue/30 text-white bg-white/5" },
    executing: { label: "Executing", cls: "border-brand-blue/50 text-white bg-white/5" },
    interpreting: { label: "Interpreting Output", cls: "border-white/15 text-white bg-white/5" },
    completed: { label: "Task Completed", cls: "border-white/20 text-white bg-white/10" },
    failed: { label: "Recovery Failed", cls: "border-destructive text-destructive-foreground/80 bg-destructive/15" },
  } as const;
  const curr = map[mode];
  return (
    <div className={cn("relative inline-flex items-center gap-2 rounded-lg border px-3 py-1 text-xs", curr.cls)}>
      {mode === "thinking" && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
      {mode === "executing" && <Clock className="h-3.5 w-3.5" />}
      {mode === "completed" && <CheckCircle2 className="h-3.5 w-3.5" />}
      {mode === "failed" && <AlertTriangle className="h-3.5 w-3.5" />}
      <span>{curr.label}</span>
      {mode === "executing" && (
        <span className="pointer-events-none absolute inset-x-0 bottom-0 h-0.5 bg-gradient-to-r from-brand-blue/0 via-brand-blue/60 to-brand-pink/0" />
      )}
    </div>
  );
}
