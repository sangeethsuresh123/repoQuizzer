"use client";

import { Suspense, useEffect, useState, useRef } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { Quiz, SubmitResponse } from "@/lib/types";

const LOADING_STEPS = [
  { at: 0, text: "Cloning repository…" },
  { at: 5, text: "Scanning files in scope…" },
  { at: 10, text: "Building context for the model…" },
  { at: 15, text: "Generating questions with AI…" },
  { at: 30, text: "Still working — the model is thinking…" },
  { at: 50, text: "Almost there…" },
];

type RoundData = {
  quiz: Quiz;
  mcqAnswers: Record<string, number>;
  codingAnswer: string;
  result: SubmitResponse;
};

function LoadingScreen({ scopePath, round }: { scopePath: string; round: number }) {
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef(Date.now());

  useEffect(() => {
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - startRef.current) / 1000)), 1000);
    return () => clearInterval(id);
  }, []);

  const step = [...LOADING_STEPS].reverse().find((s) => elapsed >= s.at) ?? LOADING_STEPS[0];

  return (
    <div className="flex flex-col items-center justify-center py-24 gap-8">
      <div className="relative h-16 w-16">
        <div className="absolute inset-0 rounded-full border-2 border-border" />
        <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-accent animate-spin" />
        <div className="absolute inset-2 rounded-full border-2 border-transparent border-b-accent animate-spin" style={{ animationDirection: "reverse", animationDuration: "1.5s" }} />
      </div>

      <div className="text-center space-y-3">
        <p className="font-mono text-sm text-ink">{step.text}</p>
        {round > 1 && (
          <p className="font-mono text-xs text-accent">Round {round}</p>
        )}
        <p className="font-mono text-xs text-dim">
          Scope: <span className="text-ink">{scopePath || "(whole repo)"}</span>
        </p>
        <p className="font-mono text-xs text-dim">{elapsed}s elapsed</p>
      </div>

      <div className="w-64 h-1 rounded-full bg-border overflow-hidden">
        <div
          className="h-full bg-accent rounded-full transition-all duration-1000 ease-out"
          style={{ width: `${Math.min((elapsed / 60) * 100, 95)}%` }}
        />
      </div>
    </div>
  );
}

function SummaryView({ rounds, scopePath }: { rounds: RoundData[]; scopePath: string }) {
  const totalMcq = rounds.reduce((s, r) => s + r.result.mcq_results.length, 0);
  const totalMcqCorrect = rounds.reduce(
    (s, r) => s + r.result.mcq_results.filter((m) => m.is_correct).length,
    0,
  );
  const totalCoding = rounds.length;
  const codingCorrect = rounds.filter((r) => r.result.coding_result.correct === true).length;
  const totalScore = rounds.reduce((s, r) => s + r.result.score, 0);
  const maxScore = rounds.reduce((s, r) => s + r.result.max_score, 0);
  const pct = maxScore === 0 ? 0 : Math.round((totalScore / maxScore) * 100);

  const missedQuestions: { round: number; qNum: number; question: string; explanation: string; selected: string; correct: string }[] = [];
  const missedCoding: { round: number; title: string; feedback: string }[] = [];

  rounds.forEach((r, ri) => {
    r.result.mcq_results.forEach((mr, mi) => {
      if (!mr.is_correct) {
        const quizMcq = r.quiz.mcqs.find((q) => q.id === mr.id);
        missedQuestions.push({
          round: ri + 1,
          qNum: mi + 1,
          question: quizMcq?.question ?? mr.id,
          explanation: mr.explanation,
          selected: quizMcq?.options[mr.selected_index ?? -1] ?? "—",
          correct: quizMcq?.options[mr.correct_index] ?? "—",
        });
      }
    });
    if (r.result.coding_result.correct !== true) {
      missedCoding.push({
        round: ri + 1,
        title: r.quiz.coding_task.title,
        feedback: r.result.coding_result.feedback,
      });
    }
  });

  return (
    <div className="space-y-10">
      <div>
        <p className="font-mono text-xs uppercase tracking-wide text-dim">Session complete</p>
        <h1 className="font-mono text-xl text-ink mt-1">Quiz Summary</h1>
        <p className="mt-1 text-sm text-dim">
          Scope: <span className="text-ink">{scopePath || "(whole repo)"}</span> · {rounds.length} round{rounds.length !== 1 ? "s" : ""}
        </p>
      </div>

      {/* Overall score */}
      <div className="rounded-md border border-border bg-elevated p-6 space-y-4">
        <div className="flex items-baseline gap-4">
          <span className="font-mono text-3xl font-semibold text-ink">{totalScore}<span className="text-dim text-lg">/{maxScore}</span></span>
          <span className="font-mono text-sm text-dim">({pct}%)</span>
        </div>
        <div className="w-full h-2 rounded-full bg-border overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${pct}%`,
              backgroundColor: pct >= 80 ? "#3FB950" : pct >= 50 ? "#E3B341" : "#F85149",
            }}
          />
        </div>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="font-mono text-lg text-ink">{totalMcqCorrect}/{totalMcq}</p>
            <p className="text-xs text-dim">MCQ correct</p>
          </div>
          <div>
            <p className="font-mono text-lg text-ink">{codingCorrect}/{totalCoding}</p>
            <p className="text-xs text-dim">Coding tasks</p>
          </div>
          <div>
            <p className="font-mono text-lg text-ink">{rounds.length}</p>
            <p className="text-xs text-dim">Rounds</p>
          </div>
        </div>
      </div>

      {/* Per-round breakdown */}
      <div className="space-y-3">
        <h2 className="font-mono text-sm uppercase tracking-wide text-dim">Per-round scores</h2>
        {rounds.map((r, i) => (
          <div key={i} className="flex items-center justify-between rounded-md border border-border px-4 py-3">
            <div>
              <p className="font-mono text-sm text-ink">Round {i + 1}</p>
              <p className="text-xs text-dim">{r.quiz.mcqs.length} MCQs + coding task</p>
            </div>
            <div className="flex items-center gap-2 font-mono text-xs">
              <div className="flex h-2 w-20 overflow-hidden rounded-full bg-badBg">
                <div
                  className="h-full bg-good"
                  style={{ width: `${r.result.max_score === 0 ? 0 : Math.round((r.result.score / r.result.max_score) * 100)}%` }}
                />
              </div>
              <span className="text-dim">{r.result.score}/{r.result.max_score}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Missed MCQs - improvement areas */}
      {missedQuestions.length > 0 && (
        <div className="space-y-3">
          <h2 className="font-mono text-sm uppercase tracking-wide text-dim">Questions to review</h2>
          <p className="text-sm text-dim">These are the questions you got wrong. Review the explanations to strengthen your understanding.</p>
          {missedQuestions.map((mq, i) => (
            <div key={i} className="diff-line diff-line-bad rounded-md px-4 py-3 space-y-2">
              <p className="font-mono text-xs text-dim">Round {mq.round} · Q{mq.qNum}</p>
              <p className="font-mono text-sm text-ink">{mq.question}</p>
              <div className="text-xs space-y-1">
                <p className="text-bad">Your answer: {mq.selected}</p>
                <p className="text-good">Correct answer: {mq.correct}</p>
              </div>
              <p className="text-xs text-dim border-t border-border pt-2">{mq.explanation}</p>
            </div>
          ))}
        </div>
      )}

      {/* Missed coding tasks */}
      {missedCoding.length > 0 && (
        <div className="space-y-3">
          <h2 className="font-mono text-sm uppercase tracking-wide text-dim">Coding tasks to revisit</h2>
          {missedCoding.map((mc, i) => (
            <div key={i} className="diff-line diff-line-bad rounded-md px-4 py-3 space-y-2">
              <p className="font-mono text-xs text-dim">Round {mc.round}</p>
              <p className="font-mono text-sm text-ink">{mc.title}</p>
              <p className="text-xs text-dim">{mc.feedback}</p>
            </div>
          ))}
        </div>
      )}

      {/* Improvement feedback */}
      <div className="rounded-md border border-accent/30 bg-accent/5 p-6 space-y-3">
        <h2 className="font-mono text-sm text-accent uppercase tracking-wide">Feedback</h2>
        {pct >= 80 ? (
          <p className="text-sm text-ink">
            Strong performance! You have a solid understanding of <span className="text-accent">{scopePath || "this codebase"}</span>.
            {missedQuestions.length > 0 && " Review the missed questions above to fill in the remaining gaps."}
            {missedCoding.length > 0 && " Pay closer attention to the coding tasks — try reading the reference solutions and re-implementing them from scratch."}
          </p>
        ) : pct >= 50 ? (
          <p className="text-sm text-ink">
            Good foundation, but there are gaps in your understanding of <span className="text-accent">{scopePath || "this codebase"}</span>.
            Focus on the questions you missed — re-read the relevant source files and try to understand
            the explanations above. Consider taking another quiz on the same scope to reinforce your learning.
          </p>
        ) : (
          <p className="text-sm text-ink">
            This codebase section needs more study. The explanations above highlight what you missed.
            Re-read the source files in <span className="text-accent">{scopePath || "this scope"}</span> carefully,
            paying attention to the areas covered by the missed questions. Then try another round to measure your improvement.
          </p>
        )}
        {totalCoding > 0 && codingCorrect === 0 && (
          <p className="text-sm text-dim border-t border-border/50 pt-3">
            None of the coding tasks were graded as correct. Practice writing code from scratch based on prompts
            rather than just modifying starter code. Study the reference solutions to understand the expected approach.
          </p>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <a
          href="/"
          className="rounded-md bg-accent px-5 py-2 font-mono text-sm font-medium text-bg hover:opacity-90 transition-opacity"
        >
          New quiz
        </a>
        <a
          href="/history"
          className="rounded-md border border-border px-5 py-2 font-mono text-sm text-dim hover:bg-elevated hover:text-ink transition-colors"
        >
          View history
        </a>
      </div>
    </div>
  );
}

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
  const [previousQuestions, setPreviousQuestions] = useState<string[]>([]);
  const [round, setRound] = useState(1);
  const [generatingMore, setGeneratingMore] = useState(false);
  const [rounds, setRounds] = useState<RoundData[]>([]);
  const [finished, setFinished] = useState(false);

  useEffect(() => {
    if (!repoUrl || finished) {
      setLoading(false);
      if (!repoUrl) setError("Missing repo — start from the home page.");
      return;
    }
    const controller = new AbortController();
    api
      .generateQuiz(repoUrl, scopePath, {
        signal: controller.signal,
        previousQuestions,
      })
      .then((q) => {
        setQuiz(q);
        setCodingAnswer(q.coding_task.starter_code);
      })
      .catch((err) => {
        if (err.name !== "AbortError") {
          setError(err.message || "Could not generate a quiz for this scope.");
        }
      })
      .finally(() => {
        setLoading(false);
        setGeneratingMore(false);
      });
    return () => controller.abort();
  }, [repoUrl, scopePath, round, finished]);

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
      setRounds((prev) => [...prev, { quiz, mcqAnswers, codingAnswer, result: res }]);
    } catch (err: any) {
      setError(err.message || "Could not submit the quiz.");
    } finally {
      setSubmitting(false);
    }
  }

  function handleMoreQuestions() {
    if (!quiz) return;
    const newPrev = [
      ...previousQuestions,
      ...quiz.mcqs.map((q) => q.question),
    ];
    setPreviousQuestions(newPrev);
    setQuiz(null);
    setResult(null);
    setMcqAnswers({});
    setCodingAnswer("");
    setError(null);
    setLoading(true);
    setGeneratingMore(true);
    setRound((r) => r + 1);
  }

  function handleFinish() {
    setFinished(true);
    setQuiz(null);
    setLoading(false);
  }

  if (finished) {
    return <SummaryView rounds={rounds} scopePath={scopePath} />;
  }

  if (loading) {
    return <LoadingScreen scopePath={scopePath} round={round} />;
  }
  if (error) {
    return (
      <div className="space-y-4">
        <div className="diff-line diff-line-bad rounded-md px-4 py-3 text-sm">
          <span className="text-bad font-mono mr-2">✗</span>{error}
        </div>
        {previousQuestions.length > 0 && (
          <button
            onClick={handleMoreQuestions}
            className="rounded-md border border-border px-4 py-2 font-mono text-sm text-dim hover:bg-elevated hover:text-ink transition-colors"
          >
            Try again
          </button>
        )}
      </div>
    );
  }
  if (!quiz) return null;

  const allMcqAnswered = quiz.mcqs.every((q) => mcqAnswers[q.id] !== undefined);

  return (
    <div className="space-y-10">
      <div>
        <div className="flex items-center gap-3">
          <p className="font-mono text-xs uppercase tracking-wide text-dim">Scope</p>
          {round > 1 && (
            <span className="font-mono text-xs px-2 py-0.5 rounded-full bg-elevated border border-border text-accent">
              Round {round}
            </span>
          )}
        </div>
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
        <div className="space-y-4">
          <div className="diff-line diff-line-good rounded-md px-4 py-3 font-mono text-sm">
            Score: {result.score} / {result.max_score}
          </div>
          <div className="flex gap-3">
            <button
              onClick={handleMoreQuestions}
              disabled={generatingMore}
              className="rounded-md border border-accent px-5 py-2 font-mono text-sm font-medium text-accent hover:bg-accent/10 transition-colors disabled:opacity-40"
            >
              {generatingMore ? "Generating…" : "More questions →"}
            </button>
            <button
              onClick={handleFinish}
              className="rounded-md border border-border px-5 py-2 font-mono text-sm text-dim hover:bg-elevated hover:text-ink transition-colors"
            >
              Finish
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function QuizPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center py-24"><p className="font-mono text-dim animate-pulse">Loading…</p></div>}>
      <QuizPageInner />
    </Suspense>
  );
}
