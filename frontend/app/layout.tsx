import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "repo-quiz — code comprehension checks for any GitHub repo",
  description: "Import a public repo, pick a scope, and take a generated quiz on it.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen font-sans">
        <header className="border-b border-border">
          <div className="mx-auto max-w-4xl flex items-center justify-between px-6 py-4">
            <Link href="/" className="font-mono text-lg font-semibold text-ink">
              <span className="text-accent">$</span> repo-quiz
            </Link>
            <nav className="flex gap-6 text-sm text-dim font-mono">
              <Link href="/" className="hover:text-ink transition-colors">new quiz</Link>
              <Link href="/chat" className="hover:text-ink transition-colors">chat</Link>
              <Link href="/history" className="hover:text-ink transition-colors">history</Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-4xl px-6 py-10">{children}</main>
      </body>
    </html>
  );
}
