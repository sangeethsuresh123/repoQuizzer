const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export const api = {
  importRepo: (repo_url: string) =>
    request<{ tree: any }>("/api/repo/import", {
      method: "POST",
      body: JSON.stringify({ repo_url }),
    }),

  generateQuiz: (repo_url: string, scope_path: string) =>
    request<import("./types").Quiz>("/api/quiz/generate", {
      method: "POST",
      body: JSON.stringify({ repo_url, scope_path }),
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
