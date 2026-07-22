"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { TreeNode } from "@/lib/types";
import FileTree from "@/components/FileTree";

type Tech = { name: string; url: string };

export default function HomePage() {
  const router = useRouter();
  const [repoUrl, setRepoUrl] = useState("");
  const [tree, setTree] = useState<TreeNode | null>(null);
  const [repoId, setRepoId] = useState<string | null>(null);
  const [technologies, setTechnologies] = useState<Tech[]>([]);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleImport(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setTree(null);
    setRepoId(null);
    setTechnologies([]);
    setSelectedPath(null);
    if (!repoUrl.trim()) return;
    setLoading(true);
    try {
      const { tree, repo_id, technologies } = await api.importRepo(repoUrl.trim());
      setTree(tree);
      setRepoId(repo_id);
      setTechnologies(technologies || []);
    } catch (err: any) {
      setError(err.message || "Could not import that repo.");
    } finally {
      setLoading(false);
    }
  }

  function handleStartQuiz() {
    if (!selectedPath && selectedPath !== "") return;
    const params = new URLSearchParams({
      repo: repoUrl.trim(),
      scope: selectedPath || "",
    });
    router.push(`/quiz?${params.toString()}`);
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-mono text-2xl font-semibold text-ink">
          Test your understanding of any public repo
        </h1>
        <p className="mt-2 text-dim">
          Paste a GitHub URL, pick a file or folder, and get a short quiz generated straight from that code.
        </p>
      </div>

      <form onSubmit={handleImport} className="flex gap-3">
        <input
          value={repoUrl}
          onChange={(e) => setRepoUrl(e.target.value)}
          placeholder="https://github.com/owner/repo"
          className="flex-1 rounded-md border border-border bg-elevated px-4 py-2 font-mono text-sm text-ink placeholder:text-dim focus:outline-none focus:ring-2 focus:ring-accent"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-accent px-5 py-2 font-mono text-sm font-medium text-bg disabled:opacity-50"
        >
          {loading ? "cloning…" : "clone"}
        </button>
      </form>

      {error && (
        <div className="diff-line diff-line-bad rounded-md px-4 py-3 text-sm text-ink">
          <span className="text-bad font-mono mr-2">✗</span>{error}
        </div>
      )}

      {tree && (
        <div className="space-y-6">
          {technologies.length > 0 && (
            <div className="space-y-2">
              <h2 className="font-mono text-sm uppercase tracking-wide text-dim">
                Detected technologies
              </h2>
              <div className="flex flex-wrap gap-2">
                {technologies.map((tech) => (
                  <a
                    key={tech.name}
                    href={tech.url || "#"}
                    target={tech.url ? "_blank" : undefined}
                    rel="noopener noreferrer"
                    className={`inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 font-mono text-xs transition-colors ${
                      tech.url
                        ? "border-accent/30 bg-accent/5 text-accent hover:bg-accent/15 hover:border-accent/50"
                        : "border-border bg-elevated text-dim"
                    }`}
                  >
                    {tech.name}
                    {tech.url && (
                      <svg className="h-3 w-3 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    )}
                  </a>
                ))}
              </div>
            </div>
          )}

          <div className="space-y-4">
            <h2 className="font-mono text-sm uppercase tracking-wide text-dim">
              Select a scope for the quiz
            </h2>
            <div className="rounded-md border border-border bg-elevated p-2 max-h-96 overflow-y-auto">
              <FileTree node={tree} selectedPath={selectedPath} onSelect={setSelectedPath} />
            </div>
            <div className="flex gap-3">
              <button
                onClick={handleStartQuiz}
                disabled={selectedPath === null}
                className="rounded-md bg-accent px-5 py-2 font-mono text-sm font-medium text-bg disabled:opacity-40"
              >
                Generate quiz →
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
