"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { AttemptSummary } from "@/lib/types";

function ScoreBar({ score, max }: { score: number; max: number }) {
  const pct = max === 0 ? 0 : Math.round((score / max) * 100);
  return (
    <div className="flex items-center gap-2 font-mono text-xs">
      <div className="flex h-2 w-24 overflow-hidden rounded-full bg-badBg">
        <div className="h-full bg-good" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-dim">{score}/{max}</span>
    </div>
  );
}

export default function HistoryPage() {
  const [attempts, setAttempts] = useState<AttemptSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<any | null>(null);

  useEffect(() => {
    api
      .history()
      .then((r) => setAttempts(r.attempts))
      .catch((e) => setError(e.message));
  }, []);

  async function toggleExpand(id: number) {
    if (expandedId === id) {
      setExpandedId(null);
      setDetail(null);
      return;
    }
    setExpandedId(id);
    const d = await api.historyDetail(id);
    setDetail(d);
  }

  if (error) return <p className="text-bad">{error}</p>;
  if (!attempts) return <p className="text-dim animate-pulse">Loading history…</p>;
  if (attempts.length === 0) return <p className="text-dim">No quiz attempts yet — go generate one.</p>;

  return (
    <div className="space-y-3">
      <h1 className="font-mono text-lg text-ink mb-4">Quiz history</h1>
      {attempts.map((a) => (
        <div key={a.id} className="rounded-md border border-border">
          <button
            onClick={() => toggleExpand(a.id)}
            className="w-full flex items-center justify-between px-4 py-3 hover:bg-elevated text-left"
          >
            <div>
              <p className="font-mono text-sm text-ink">{a.scope_path || "(whole repo)"}</p>
              <p className="text-xs text-dim">
                {a.repo_url.replace("https://github.com/", "")} · {new Date(a.created_at).toLocaleString()}
              </p>
            </div>
            <ScoreBar score={a.score} max={a.max_score} />
          </button>
          {expandedId === a.id && detail && (
            <div className="border-t border-border px-4 py-3 space-y-3 bg-elevated">
              {detail.quiz.mcqs.map((q: any, i: number) => {
                const selected = detail.answers.mcq_answers[q.id];
                const isCorrect = selected === q.correct_index;
                return (
                  <div key={q.id} className="text-sm">
                    <p className="font-mono text-ink">Q{i + 1}. {q.question}</p>
                    <p className={`text-xs mt-1 ${isCorrect ? "text-good" : "text-bad"}`}>
                      Your answer: {q.options[selected] ?? "—"} {isCorrect ? "(correct)" : `(correct: ${q.options[q.correct_index]})`}
                    </p>
                  </div>
                );
              })}
              <div className="text-sm">
                <p className="font-mono text-ink">{detail.quiz.coding_task.title}</p>
                <pre className="mt-1 whitespace-pre-wrap text-xs text-dim">{detail.answers.coding_answer}</pre>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
