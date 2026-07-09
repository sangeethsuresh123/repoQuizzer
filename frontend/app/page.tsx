"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { TreeNode } from "@/lib/types";
import FileTree from "@/components/FileTree";

export default function HomePage() {
  const router = useRouter();
  const [repoUrl, setRepoUrl] = useState("");
  const [tree, setTree] = useState<TreeNode | null>(null);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleImport(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setTree(null);
    setSelectedPath(null);
    if (!repoUrl.trim()) return;
    setLoading(true);
    try {
      const { tree } = await api.importRepo(repoUrl.trim());
      setTree(tree);
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
        <div className="space-y-4">
          <h2 className="font-mono text-sm uppercase tracking-wide text-dim">
            Select a scope for the quiz
          </h2>
          <div className="rounded-md border border-border bg-elevated p-2 max-h-96 overflow-y-auto">
            <FileTree node={tree} selectedPath={selectedPath} onSelect={setSelectedPath} />
          </div>
          <button
            onClick={handleStartQuiz}
            disabled={selectedPath === null}
            className="rounded-md bg-accent px-5 py-2 font-mono text-sm font-medium text-bg disabled:opacity-40"
          >
            Generate quiz →
          </button>
        </div>
      )}
    </div>
  );
}
