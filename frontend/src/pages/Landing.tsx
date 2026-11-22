import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Loader2, Play, Package, Boxes, Layers, ArrowRight, Star } from 'lucide-react';
import GithubIcon from '../components/GithubIcon';
import { demoApi } from '../lib/api';
import { packApi } from '../lib/packApi';
import {
  FRAMEWORK_LABELS,
  formatUses,
  packKindLabel,
  packSource,
  packSourceLabel,
} from '../lib/packs';
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

  // Public storefront data (ADR-0014) — works with no session. Featured shows
  // the four starter packs first, then the best-rated community packs.
  // `download_count` is deliberately not used as a ranking (invariant 25).
  const { data: community } = useQuery({
    queryKey: ['public-featured-packs'],
    queryFn: () => packApi.listCommunity({ limit: 50, sort: 'alpha' }),
  });
  const featured = [
    ...(community?.items ?? []).filter((pack) => pack.is_starter_pack).slice(0, 4),
    ...(community?.items ?? [])
      .filter((pack) => !pack.is_starter_pack)
      .sort((a, b) => b.avg_rating - a.avg_rating || b.rating_count - a.rating_count)
      .slice(0, 2),
  ];

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
            <Link
              to="/packs"
              className="hidden text-sm text-muted-foreground transition-colors hover:text-foreground sm:block"
            >
              Browse packs
            </Link>
            <a
              href="https://github.com/niels-emmer/myace"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <GithubIcon className="h-4 w-4" />
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
      <section className="max-w-5xl mx-auto px-4 py-16 text-center space-y-4">
        {/* Brand mark — decorative image (alt="") since the title text beside it
            carries the name; the page's single <h1> stays the pitch below. */}
        <div className="flex flex-col items-center gap-3 pb-4">
          <img src="/logo.png" alt="" aria-hidden="true" className="h-24 w-24 sm:h-32 sm:w-32" />
          <p className="text-4xl sm:text-5xl font-bold tracking-tight text-foreground">MyACE</p>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-foreground">
          Write your AI agent rules once. Compile them everywhere.
        </h1>
        <p className="text-muted-foreground text-lg">
          Browse best-practice packs, assemble them into one setup, and install that setup into
          Claude Code, Codex, Cursor, OpenCode, and eight more — without maintaining a separate
          copy per tool.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
          <Link
            to="/packs"
            className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-6 py-3 text-base font-semibold text-white transition-colors hover:bg-brand-700"
          >
            Browse packs
            <ArrowRight className="h-4 w-4" />
          </Link>
          {/* Phase 2 owns `/onboarding`; until its parallel branch lands,
              send the visitor to sign-up so this CTA has a real
              destination on a standalone Phase 5 branch. Flip to
              `/onboarding` in integration. */}
          <Link
            to="/login?mode=register"
            className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-6 py-3 text-base font-medium text-foreground transition-colors hover:border-brand-600 hover:text-brand-600"
          >
            Set up mine — 2 minutes
          </Link>
        </div>

        {/* The one four-step story every screen repeats (design §4.2). */}
        <div className="grid grid-cols-1 gap-3 pt-6 text-left sm:grid-cols-2 lg:grid-cols-4">
          {[
            ['Browse packs', 'Best-practice rules, skills and agents.'],
            ['Build a setup', 'Combine packs into one recipe.'],
            ['Install everywhere', 'One setup, many frameworks.'],
            ['Publish', 'Share your own pack.'],
          ].map(([title, caption], index) => (
            <div
              key={title}
              className="flex items-start gap-3 rounded-xl border border-border bg-card p-4"
            >
              <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-brand-600 text-xs font-bold text-white">
                {index + 1}
              </span>
              <div>
                <p className="text-sm font-semibold text-card-foreground">{title}</p>
                <p className="text-xs text-muted-foreground">{caption}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Featured packs — the storefront's front door. */}
      <section className="mx-auto max-w-5xl px-4 pb-16">
        <div className="mb-4 flex items-end justify-between gap-3">
          <h2 className="text-xl font-semibold text-foreground">Start from a proven pack</h2>
          <Link to="/packs" className="text-sm text-brand-600 hover:underline">
            Browse all packs →
          </Link>
        </div>
        {featured.length > 0 ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {featured.map((pack) => {
              const source = packSource(pack);
              return (
                <Link
                  key={pack.id}
                  to={`/packs/${pack.id}`}
                  className="flex flex-col rounded-xl border border-border bg-card p-5 transition-shadow hover:border-input hover:shadow-sm"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="rounded bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                      {packKindLabel(pack.collection_type)}
                    </span>
                    <span className="rounded border border-border px-2 py-0.5 text-xs font-medium text-muted-foreground">
                      {packSourceLabel(source)}
                    </span>
                  </div>
                  <h3 className="mt-3 font-semibold text-card-foreground">{pack.name}</h3>
                  <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
                    {pack.description || 'No description'}
                  </p>
                  <div className="mt-auto flex flex-wrap items-center gap-3 pt-4 text-xs text-muted-foreground">
                    {pack.rating_count > 0 && (
                      <span className="flex items-center gap-1">
                        <Star className="h-3 w-3" />
                        {pack.avg_rating.toFixed(1)}
                      </span>
                    )}
                    <span>{formatUses(pack.download_count)}</span>
                    <span>·</span>
                    <span>All 12 frameworks</span>
                  </div>
                </Link>
              );
            })}
          </div>
        ) : (
          <p className="rounded-xl border border-border bg-card p-6 text-sm text-muted-foreground">
            Packs will appear here as soon as the community library has an approved pack.{' '}
            <Link to="/packs" className="text-brand-600 hover:underline">
              Browse packs
            </Link>
            .
          </p>
        )}
      </section>

      {/* Live demo */}
      <section className="max-w-5xl mx-auto px-4 pb-16">
        <div className="bg-card rounded-xl border border-border overflow-hidden">
          <div className="px-6 py-4 border-b border-border flex items-center gap-2">
            <Play className="h-4 w-4 text-brand-600" />
            <h2 className="text-lg font-semibold text-card-foreground">See the translation</h2>
            <span className="text-xs text-muted-foreground">No account needed</span>
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
      <section className="max-w-5xl mx-auto px-4 pb-12 grid grid-cols-1 sm:grid-cols-3 gap-6">
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
          <h3 className="font-semibold text-foreground">12 target frameworks</h3>
          <p className="text-sm text-muted-foreground">
            Claude Code, OpenCode, Cursor, Codex CLI, Copilot CLI, Cline, Windsurf, Aider,
            Continue, Goose, Amazon Q Developer, and pi.dev.
          </p>
        </div>
      </section>

      {/* Framework strip */}
      <section className="mx-auto max-w-5xl px-4 pb-12 text-center">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Compiles to {FRAMEWORK_LABELS.length} frameworks
        </p>
        <div className="mt-3 flex flex-wrap items-center justify-center gap-2">
          {FRAMEWORK_LABELS.map((framework) => (
            <span
              key={framework}
              className="rounded-full border border-border bg-card px-3 py-1 text-xs text-muted-foreground"
            >
              {framework}
            </span>
          ))}
        </div>
      </section>

      {/* Call to action */}
      <section className="mx-auto max-w-5xl px-4 pb-20 text-center">
        <div className="flex flex-wrap items-center justify-center gap-3">
          <Link
            to="/packs"
            className="inline-block rounded-lg border border-border bg-card px-6 py-3 text-base font-medium text-foreground transition-colors hover:border-brand-600 hover:text-brand-600"
          >
            Browse packs
          </Link>
          <Link
            to="/login?mode=register"
            className="inline-block rounded-lg bg-brand-600 px-6 py-3 text-base font-semibold text-white transition-colors hover:bg-brand-700"
          >
            Sign up free — start building
          </Link>
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
