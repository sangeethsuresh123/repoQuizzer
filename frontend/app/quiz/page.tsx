"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { Quiz, SubmitResponse } from "@/lib/types";

function QuizPageInner() {
  const searchParams = useSearchParams();
  const repoUrl = searchParams.get("repo") || "";
  const scopePath = searchParams.get("scope") || "";

  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mcqAnswers, setMcqAnswers] = useState<Record<string, number>>({});
  const [codingAnswer, setCodingAnswer] = useState("");
  const [result, setResult] = useState<SubmitResponse | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!repoUrl) return;
    api
      .generateQuiz(repoUrl, scopePath)
      .then((q) => {
        setQuiz(q);
        setCodingAnswer(q.coding_task.starter_code);
      })
      .catch((err) => setError(err.message || "Could not generate a quiz for this scope."))
      .finally(() => setLoading(false));
  }, [repoUrl, scopePath]);

  async function handleSubmit() {
    if (!quiz) return;
    setSubmitting(true);
    try {
      const res = await api.submitQuiz({
        repo_url: repoUrl,
        scope_path: scopePath,
        quiz,
        mcq_answers: mcqAnswers,
        coding_answer: codingAnswer,
      });
      setResult(res);
    } catch (err: any) {
      setError(err.message || "Could not submit the quiz.");
    } finally {
      setSubmitting(false);
    }
  }

  if (!repoUrl) {
    return <p className="text-dim">Missing repo — start from the home page.</p>;
  }
  if (loading) {
    return <p className="font-mono text-dim animate-pulse">Reading {scopePath || "the repo"} and writing questions…</p>;
  }
  if (error) {
    return (
      <div className="diff-line diff-line-bad rounded-md px-4 py-3 text-sm">
        <span className="text-bad font-mono mr-2">✗</span>{error}
      </div>
    );
  }
  if (!quiz) return null;

  const allMcqAnswered = quiz.mcqs.every((q) => mcqAnswers[q.id] !== undefined);

  return (
    <div className="space-y-10">
      <div>
        <p className="font-mono text-xs uppercase tracking-wide text-dim">Scope</p>
        <h1 className="font-mono text-lg text-ink">{scopePath || "(whole repo)"}</h1>
        <p className="mt-1 text-xs text-dim">Based on: {quiz.files_used.join(", ")}</p>
      </div>

      {quiz.mcqs.map((q, idx) => {
        const mcqResult = result?.mcq_results.find((r) => r.id === q.id);
        return (
          <div key={q.id} className="space-y-2">
            <p className="font-mono text-sm text-ink">
              <span className="text-dim">Q{idx + 1}.</span> {q.question}
            </p>
            <div className="rounded-md border border-border overflow-hidden">
              {q.options.map((opt, optIdx) => {
                const isSelected = mcqAnswers[q.id] === optIdx;
                let lineClass = "diff-line-neutral hover:bg-elevated";
                let marker = " ";
                if (result && mcqResult) {
                  if (optIdx === mcqResult.correct_index) {
                    lineClass = "diff-line-good";
                    marker = "+";
                  } else if (isSelected && !mcqResult.is_correct) {
                    lineClass = "diff-line-bad";
                    marker = "-";
                  }
                } else if (isSelected) {
                  lineClass = "diff-line-good";
                  marker = "+";
                }
                return (
                  <button
                    key={optIdx}
                    disabled={!!result}
                    onClick={() => setMcqAnswers((a) => ({ ...a, [q.id]: optIdx }))}
                    className={`diff-line w-full text-left px-4 py-2 text-sm font-mono flex gap-2 ${lineClass} disabled:cursor-default`}
                  >
                    <span className="diff-marker">{marker}</span>
                    <span>{opt}</span>
                  </button>
                );
              })}
            </div>
            {result && mcqResult && (
              <p className={`text-xs pl-1 ${mcqResult.is_correct ? "text-good" : "text-bad"}`}>
                {mcqResult.explanation}
              </p>
            )}
          </div>
        );
      })}

      <div className="space-y-2">
        <p className="font-mono text-xs uppercase tracking-wide text-dim">
          {quiz.coding_task.type === "bug_fix" ? "Bug fix" : "Write the code"}
        </p>
        <h2 className="font-mono text-sm text-ink">{quiz.coding_task.title}</h2>
        <p className="text-sm text-dim">{quiz.coding_task.prompt}</p>
        <textarea
          value={codingAnswer}
          onChange={(e) => setCodingAnswer(e.target.value)}
          disabled={!!result}
          rows={10}
          spellCheck={false}
          className="w-full rounded-md border border-border bg-elevated p-4 font-mono text-sm text-ink focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-70"
        />
        {result && (
          <div className={`diff-line rounded-md px-4 py-3 text-sm ${result.coding_result.correct ? "diff-line-good" : "diff-line-bad"}`}>
            <p className="text-ink">{result.coding_result.feedback}</p>
            <p className="mt-2 text-xs text-dim">Reference solution:</p>
            <pre className="mt-1 whitespace-pre-wrap text-xs text-ink">{quiz.coding_task.reference_solution}</pre>
            <p className="mt-2 text-xs text-dim">{quiz.coding_task.explanation}</p>
          </div>
        )}
      </div>

      {!result ? (
        <button
          onClick={handleSubmit}
          disabled={!allMcqAnswered || submitting}
          className="rounded-md bg-accent px-6 py-2 font-mono text-sm font-medium text-bg disabled:opacity-40"
        >
          {submitting ? "grading…" : "Submit quiz"}
        </button>
      ) : (
        <div className="diff-line diff-line-good rounded-md px-4 py-3 font-mono text-sm">
          Score: {result.score} / {result.max_score}
        </div>
      )}
    </div>
  );
}

export default function QuizPage() {
  return (
    <Suspense fallback={<p className="text-dim">Loading…</p>}>
      <QuizPageInner />
    </Suspense>
  );
}
