import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { Github, Loader2, Play, Package, Boxes, Layers } from 'lucide-react';
import { demoApi } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';

const SAMPLE_MARKDOWN = `## Formatting

Use 2-space indentation. No trailing whitespace.

## Testing

Write a test alongside every bug fix, not just new features.

## Commit Messages

Use conventional commits: feat:, fix:, docs:, chore:.
`;

const DEMO_TARGET_LABELS: Record<string, string> = {
  'claude-code': 'Claude Code',
  cursor: 'Cursor',
  opencode: 'OpenCode',
};

export default function Landing() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [markdown, setMarkdown] = useState(SAMPLE_MARKDOWN);
  const [activeTarget, setActiveTarget] = useState('claude-code');

  // Already signed in — /welcome is for unauthenticated visitors, send an
  // existing session straight to the dashboard instead (same pattern as
  // Login.tsx).
  useEffect(() => {
    if (user) navigate('/', { replace: true });
  }, [user, navigate]);

  const demoMutation = useMutation({
    mutationFn: () => demoApi.compile(markdown),
  });

  const result = demoMutation.data;
  const activeFiles = result?.targets[activeTarget] ?? {};

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <img src="/logo.png" alt="MyACE" className="h-8 w-8" />
            <span className="text-lg font-bold text-foreground">MyACE</span>
          </div>
          <div className="flex items-center gap-3">
            <a
              href="https://github.com/niels-emmer/myace"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <Github className="h-4 w-4" />
              GitHub
            </a>
            <Link
              to="/login"
              className="px-3 py-1.5 text-sm font-medium text-foreground hover:text-brand-600 transition-colors"
            >
              Log in
            </Link>
            <Link
              to="/login?mode=register"
              className="px-4 py-1.5 bg-brand-600 text-white rounded-lg hover:bg-brand-700 text-sm font-medium transition-colors"
            >
              Sign up
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="max-w-3xl mx-auto px-4 py-16 text-center space-y-4">
        <h1 className="text-3xl sm:text-4xl font-bold text-foreground">
          Write your AI agent rules once. Compile them everywhere.
        </h1>
        <p className="text-muted-foreground text-lg">
          MyACE stores your rules, skills, agents, and workflows as a portable Canonical
          Intermediate Representation, then translates them into the exact config files 11
          different coding-agent frameworks expect — Claude Code, Cursor, OpenCode, Codex CLI,
          and more.
        </p>
        <p className="text-sm text-muted-foreground">
          Think packages vs. a lockfile: a <strong className="text-foreground">Collection</strong>{' '}
          is where your rules live; a <strong className="text-foreground">Profile</strong> is a
          named recipe assembled from them, compiled for one target framework at a time.
        </p>
      </section>

      {/* Live demo */}
      <section className="max-w-5xl mx-auto px-4 pb-16">
        <div className="bg-card rounded-xl border border-border overflow-hidden">
          <div className="px-6 py-4 border-b border-border flex items-center gap-2">
            <Play className="h-4 w-4 text-brand-600" />
            <h2 className="text-lg font-semibold text-card-foreground">Try it — no account needed</h2>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-0 lg:divide-x divide-border">
            {/* Input */}
            <div className="p-6 space-y-3">
              <label className="block text-sm font-medium text-foreground">
                Paste or edit an AGENTS.md-style rules file
              </label>
              <textarea
                value={markdown}
                onChange={(e) => setMarkdown(e.target.value)}
                rows={12}
                maxLength={20000}
                className="w-full px-3 py-2 bg-background text-foreground border border-input rounded-lg text-xs font-mono focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
              />
              <button
                onClick={() => demoMutation.mutate()}
                disabled={demoMutation.isPending || !markdown.trim()}
                className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 text-sm font-medium transition-colors"
              >
                {demoMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
                Compile
              </button>
              {demoMutation.isError && (
                <p className="text-sm text-destructive">{demoMutation.error.message}</p>
              )}
              <p className="text-xs text-muted-foreground">
                Only <code className="bg-muted px-1 rounded">## Section</code>-style rules are
                parsed for this demo — sign up to also compile skills, agents, and workflows.
              </p>
            </div>

            {/* Output */}
            <div className="p-6 space-y-3 bg-muted/30">
              {!result ? (
                <div className="h-full flex items-center justify-center text-sm text-muted-foreground py-12">
                  Compiled output for Claude Code, Cursor, and OpenCode will appear here.
                </div>
              ) : (
                <>
                  <div className="flex gap-2">
                    {Object.keys(result.targets).map((target) => (
                      <button
                        key={target}
                        onClick={() => setActiveTarget(target)}
                        className={`px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors ${
                          activeTarget === target
                            ? 'border-brand-500 bg-brand-50 text-brand-700'
                            : 'border-border text-muted-foreground hover:border-input'
                        }`}
                      >
                        {DEMO_TARGET_LABELS[target] ?? target}
                      </button>
                    ))}
                  </div>
                  {Object.keys(activeFiles).length === 0 ? (
                    <p className="text-sm text-muted-foreground py-4">
                      No <code className="bg-background px-1 rounded">## Section</code> rules
                      found — add one and recompile.
                    </p>
                  ) : (
                    Object.entries(activeFiles).map(([filename, content]) => (
                      <div key={filename} className="bg-card rounded-lg border border-border overflow-hidden">
                        <div className="px-3 py-1.5 bg-muted border-b border-border">
                          <span className="text-xs font-mono text-foreground">{filename}</span>
                        </div>
                        <pre className="p-3 text-xs text-muted-foreground overflow-x-auto max-h-64 overflow-y-auto">
                          {content}
                        </pre>
                      </div>
                    ))
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-5xl mx-auto px-4 pb-20 grid grid-cols-1 sm:grid-cols-3 gap-6">
        <div className="space-y-2">
          <Package className="h-6 w-6 text-brand-600" />
          <h3 className="font-semibold text-foreground">Import from anywhere</h3>
          <p className="text-sm text-muted-foreground">
            Scan a local config directory or a GitHub repo and turn what you already have into a
            portable Collection.
          </p>
        </div>
        <div className="space-y-2">
          <Layers className="h-6 w-6 text-brand-600" />
          <h3 className="font-semibold text-foreground">Compose, don't copy</h3>
          <p className="text-sm text-muted-foreground">
            A Profile combines a base collection with additional ones, layered by priority — a
            named recipe, not a duplicated file tree.
          </p>
        </div>
        <div className="space-y-2">
          <Boxes className="h-6 w-6 text-brand-600" />
          <h3 className="font-semibold text-foreground">11 target frameworks</h3>
          <p className="text-sm text-muted-foreground">
            Claude Code, OpenCode, Cursor, Codex CLI, Copilot CLI, Cline, Windsurf, Aider,
            Continue, Goose, and Amazon Q Developer.
          </p>
        </div>
      </section>

      <footer className="border-t border-border py-8 text-center">
        <p className="text-sm text-muted-foreground">
          MyACE is free and self-hostable.{' '}
          <a
            href="https://github.com/niels-emmer/myace"
            target="_blank"
            rel="noopener noreferrer"
            className="text-brand-600 hover:underline"
          >
            View the source on GitHub
          </a>
          .
        </p>
      </footer>
    </div>
  );
}
