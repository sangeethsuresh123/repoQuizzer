"use client";

import { Suspense, useState, useRef, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";

type Message = {
  role: "user" | "assistant";
  content: string;
  sources?: string[];
};

function ChatInner() {
  const searchParams = useSearchParams();
  const initialRepoId = searchParams.get("repo_id") ?? "";

  const [repoId, setRepoId] = useState(initialRepoId);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    const q = input.trim();
    if (!q || !repoId.trim() || loading) return;

    setInput("");
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: q }]);
    setLoading(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const res = await api.ask(repoId.trim(), q, { signal: controller.signal });
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.answer, sources: res.sources },
      ]);
    } catch (err: any) {
      if (err.name === "AbortError") return;
      setError(err.message || "Request failed");
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Something went wrong. Please try again." },
      ]);
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      <h1 className="font-mono text-xl font-semibold mb-4">
        <span className="text-accent">/</span> chat with the repo
      </h1>

      {!initialRepoId && (
        <div className="mb-4">
          <label className="block text-sm text-dim font-mono mb-1">repo id</label>
          <input
            value={repoId}
            onChange={(e) => setRepoId(e.target.value)}
            placeholder="e.g. my-repo-abc123def456"
            className="w-full bg-elevated border border-border rounded px-3 py-2 font-mono text-sm text-ink placeholder:text-dim/50 focus:outline-none focus:border-accent"
          />
          <p className="text-xs text-dim mt-1">
            Find this in the URL after importing a repo, or check the /import response.
          </p>
        </div>
      )}

      {initialRepoId && (
        <p className="text-xs text-dim font-mono mb-3">
          repo: <span className="text-ink">{repoId}</span>
        </p>
      )}

      <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-2">
        {messages.length === 0 && (
          <p className="text-dim text-sm text-center mt-12">
            Ask a question about the codebase.
          </p>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[80%] rounded-lg px-4 py-3 ${
                msg.role === "user"
                  ? "bg-accent/10 border border-accent/30 text-ink"
                  : "bg-elevated border border-border text-ink"
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-2 pt-2 border-t border-border/50">
                  <span className="text-xs text-dim font-mono">sources: </span>
                  {msg.sources.map((s, j) => (
                    <span key={j} className="text-xs text-accent font-mono">
                      {s}
                      {j < msg.sources!.length - 1 ? ", " : ""}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {error && (
        <p className="text-bad text-xs font-mono mb-2">{error}</p>
      )}

      <div className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={repoId.trim() ? "Ask about the code..." : "Enter a repo id first"}
          disabled={loading || !repoId.trim()}
          className="flex-1 bg-elevated border border-border rounded px-3 py-2 font-mono text-sm text-ink placeholder:text-dim/50 focus:outline-none focus:border-accent disabled:opacity-50"
        />
        <button
          onClick={send}
          disabled={loading || !input.trim() || !repoId.trim()}
          className="bg-accent/20 border border-accent/40 text-accent font-mono text-sm px-4 py-2 rounded hover:bg-accent/30 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loading ? (
            <span className="inline-block w-4 h-4 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
          ) : (
            "send"
          )}
        </button>
      </div>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-[calc(100vh-8rem)]">
          <span className="text-dim font-mono text-sm">loading…</span>
        </div>
      }
    >
      <ChatInner />
    </Suspense>
  );
}
