const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

const DEFAULT_TIMEOUT_MS = 250_000;

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const { signal, ...rest } = options ?? {};
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);
  // If caller provides their own signal, abort our controller when it fires.
  if (signal) {
    if (signal.aborted) controller.abort();
    else signal.addEventListener("abort", () => controller.abort(), { once: true });
  }
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      ...rest,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Request failed (${res.status})`);
    }
    return res.json();
  } finally {
    clearTimeout(timeout);
  }
}

export const api = {
  importRepo: (repo_url: string) =>
    request<{ tree: any; repo_id: string; technologies: { name: string; url: string }[] }>("/api/repo/import", {
      method: "POST",
      body: JSON.stringify({ repo_url }),
    }),

  generateQuiz: (
    repo_url: string,
    scope_path: string,
    opts?: { signal?: AbortSignal; previousQuestions?: string[] },
  ) =>
    request<import("./types").Quiz>("/api/quiz/generate", {
      method: "POST",
      body: JSON.stringify({
        repo_url,
        scope_path,
        previous_questions: opts?.previousQuestions ?? [],
      }),
      signal: opts?.signal,
    }),

  submitQuiz: (payload: {
    repo_url: string;
    scope_path: string;
    quiz: import("./types").Quiz;
    mcq_answers: Record<string, number>;
    coding_answer: string;
  }) =>
    request<import("./types").SubmitResponse>("/api/quiz/submit", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  history: () => request<{ attempts: import("./types").AttemptSummary[] }>("/api/history"),

  historyDetail: (id: number) => request<any>(`/api/history/${id}`),
};
