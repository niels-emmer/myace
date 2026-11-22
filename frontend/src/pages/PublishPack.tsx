import { useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Check,
  CheckCircle2,
  Loader2,
} from 'lucide-react';
import { collectionsApi } from '../lib/api';
import { packApi } from '../lib/packApi';
import { PublishStatusTracker } from '../components/PublishStatusTracker';
import { useAuth } from '../contexts/AuthContext';
import { packKindLabel, packSource, packSourceLabel } from '../lib/packs';
import type { Pack, PublishDraft } from '../types/packs';

const inputClass =
  'w-full px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm ' +
  'focus:ring-2 focus:ring-brand-500 focus:border-brand-500';

const LICENSE_SUGGESTIONS = [
  'MIT',
  'Apache-2.0',
  'BSD-3-Clause',
  'MPL-2.0',
  'GPL-3.0-only',
  'AGPL-3.0-only',
  'Unlicense',
];

const STEPS = ['Select', 'Describe', 'Preview', 'Submit'] as const;

const STATUS_LABEL: Record<string, string> = {
  draft: 'never published',
  submitted: 'in review',
  approved: 'approved',
  denied: 'changes requested',
  unpublished: 'was published, now unpublished',
};

/**
 * Four-step publish wizard (design §6.8, `/packs/:id/publish`).
 *
 * Step 2 writes metadata (including `license`) with `PATCH /collections/{id}`
 * and step 4 submits with `POST /collections/{id}/publish` — the existing
 * moderation-queue entry point. Publishing never touches `visibility`; that
 * stays the separate owner-controlled Share flag (AGENTS.md rule 18).
 *
 * Note: packs have no `tags` column (tags live on items), so this wizard
 * does not offer a pack-tag field — there is nothing in this phase's
 * no-migrations scope to persist it to.
 */
export default function PublishPack() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [step, setStep] = useState(1);
  type DraftState = PublishDraft & { packId: string };
  const [draft, setDraft] = useState<DraftState | null>(null);
  const [isNewCategory, setIsNewCategory] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const { data: pack, isLoading } = useQuery<Pack>({
    queryKey: ['collection', id],
    queryFn: async () => collectionsApi.get(id!),
    enabled: !!id,
  });

  // Seed the form from the loaded pack during render (the same guarded
  // "adjust state during render" pattern Layout.tsx uses) instead of an
  // effect, which the repo's react-hooks lint forbids for this case.
  if (pack && draft?.packId !== pack.id) {
    setDraft({
      packId: pack.id,
      name: pack.name,
      description: pack.description ?? '',
      category: pack.category ?? '',
      license: pack.license ?? '',
    });
  }
  const form: DraftState = draft ?? {
    packId: pack?.id ?? id ?? '',
    name: '',
    description: '',
    category: '',
    license: '',
  };

  const { data: myPacks } = useQuery({
    queryKey: ['collections', { owner_id: user?.id }],
    queryFn: () => collectionsApi.list({ owner_id: user?.id }),
    enabled: !!user,
  });

  const { data: categories } = useQuery({
    queryKey: ['community-categories'],
    queryFn: () => collectionsApi.listCommunityCategories(),
  });

  const publishMutation = useMutation({
    mutationFn: async () => {
      await packApi.updateMetadata(id!, {
        name: form.name.trim(),
        description: form.description.trim(),
        category: form.category.trim(),
        license: form.license.trim() || null,
      });
      return collectionsApi.publish(id!, {
        category: form.category.trim(),
        publish_name: form.name.trim(),
        publish_description: form.description.trim(),
      });
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(['collection', id], updated);
      queryClient.invalidateQueries({ queryKey: ['collections'] });
      queryClient.invalidateQueries({ queryKey: ['public-pack', id] });
      queryClient.invalidateQueries({ queryKey: ['community-collections'] });
      setSubmitted(true);
    },
  });

  const unpublishMutation = useMutation({
    mutationFn: () => collectionsApi.unpublish(id!),
    onSuccess: (updated) => {
      queryClient.setQueryData(['collection', id], updated);
      queryClient.invalidateQueries({ queryKey: ['collections'] });
      queryClient.invalidateQueries({ queryKey: ['community-collections'] });
    },
  });

  const ownerPacks = useMemo(
    () => (myPacks ?? []).filter((candidate) => candidate.id === id || candidate.is_active),
    [myPacks, id],
  );

  if (isLoading) {
    return <div className="py-12 text-center text-muted-foreground">Loading pack…</div>;
  }

  if (!pack) {
    return <div className="py-12 text-center text-muted-foreground">Pack not found.</div>;
  }

  if (!user || user.id !== pack.owner_id) {
    return (
      <div className="py-12 text-center">
        <p className="text-muted-foreground">
          Only the pack&apos;s owner can publish it.{' '}
          <Link to={`/packs/${pack.id}`} className="text-brand-600 hover:underline">
            Back to the pack
          </Link>
          .
        </p>
      </div>
    );
  }

  const status = submitted ? 'submitted' : pack.moderation_status;
  const canSubmit =
    form.name.trim().length > 0 &&
    form.category.trim().length > 0 &&
    (status === 'draft' || status === 'denied' || status === 'unpublished');
  const source = packSource(pack, user.id);

  const goNext = () => {
    if (step === 4) {
      publishMutation.mutate();
      return;
    }
    setStep((current) => Math.min(4, current + 1));
  };

  return (
    <div className="space-y-6">
      <Link
        to={`/packs/${pack.id}`}
        className="flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to the pack
      </Link>

      <div>
        <h1 className="text-2xl font-bold text-foreground">Publish a pack</h1>
        <p className="mt-1 text-muted-foreground">
          Share a pack you own with the community. A moderator reviews every submission.
        </p>
      </div>

      <PublishStatusTracker status={status} reason={pack.moderation_reason} />

      <div className="flex flex-wrap items-center gap-2">
        {STEPS.map((label, index) => {
          const value = index + 1;
          return (
            <button
              key={label}
              onClick={() => setStep(value)}
              aria-current={step === value ? 'step' : undefined}
              className={`rounded-full border px-3 py-1 text-sm font-medium transition-colors ${
                step === value
                  ? 'border-brand-600 bg-brand-50 text-brand-700'
                  : 'border-border text-muted-foreground hover:text-foreground'
              }`}
            >
              {value} · {label}
            </button>
          );
        })}
      </div>

      <div className="space-y-5 rounded-xl border border-border bg-card p-5">
        {step === 1 && (
          <div className="space-y-3">
            <h2 className="text-base font-semibold text-foreground">Which pack?</h2>
            <div className="space-y-2">
              {ownerPacks.map((candidate) => (
                <button
                  key={candidate.id}
                  onClick={() => {
                    if (candidate.id !== id) navigate(`/packs/${candidate.id}/publish`);
                  }}
                  className={`flex w-full items-start gap-3 rounded-lg border p-3 text-left transition-colors ${
                    candidate.id === id
                      ? 'border-brand-500 bg-brand-50'
                      : 'border-border hover:border-input'
                  }`}
                >
                  <span
                    className={`mt-1 h-3.5 w-3.5 shrink-0 rounded-full border ${
                      candidate.id === id ? 'border-brand-600 bg-brand-600' : 'border-input'
                    }`}
                  />
                  <span className="min-w-0">
                    <span className="block text-sm font-medium text-card-foreground">
                      {candidate.name}
                    </span>
                    <span className="block text-xs text-muted-foreground">
                      {candidate.artifact_count} items · {candidate.visibility} ·{' '}
                      {STATUS_LABEL[candidate.moderation_status] ?? candidate.moderation_status}
                    </span>
                  </span>
                </button>
              ))}
              {ownerPacks.length === 0 && (
                <p className="text-sm text-muted-foreground">
                  You do not own any packs yet.{' '}
                  <Link to="/packs/import" className="text-brand-600 hover:underline">
                    Import one
                  </Link>
                  .
                </p>
              )}
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <h2 className="text-base font-semibold text-foreground">Describe it</h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium text-foreground" htmlFor="publish-name">
                  Name
                </label>
                <input
                  id="publish-name"
                  value={form.name}
                  onChange={(event) => setDraft({ ...form, name: event.target.value })}
                  className={inputClass}
                />
              </div>
              <div>
                <label
                  className="mb-1 block text-sm font-medium text-foreground"
                  htmlFor="publish-category"
                >
                  Category
                </label>
                <select
                  id="publish-category"
                  value={isNewCategory ? '__new__' : form.category}
                  onChange={(event) => {
                    if (event.target.value === '__new__') {
                      setIsNewCategory(true);
                      setDraft({ ...form, category: '' });
                    } else {
                      setIsNewCategory(false);
                      setDraft({ ...form, category: event.target.value });
                    }
                  }}
                  className={inputClass}
                >
                  <option value="" disabled>
                    Select a category…
                  </option>
                  {(categories ?? []).map((category) => (
                    <option key={category} value={category}>
                      {category}
                    </option>
                  ))}
                  {form.category &&
                    !isNewCategory &&
                    !(categories ?? []).includes(form.category) && (
                      <option value={form.category}>{form.category}</option>
                    )}
                  <option value="__new__">+ New category…</option>
                </select>
                {isNewCategory && (
                  <input
                    value={form.category}
                    onChange={(event) => setDraft({ ...form, category: event.target.value })}
                    placeholder="e.g. backend, iac, frontend"
                    aria-label="New category"
                    className={`${inputClass} mt-2`}
                  />
                )}
              </div>
            </div>

            <div>
              <label
                className="mb-1 block text-sm font-medium text-foreground"
                htmlFor="publish-description"
              >
                Description
              </label>
              <textarea
                id="publish-description"
                value={form.description}
                onChange={(event) => setDraft({ ...form, description: event.target.value })}
                rows={3}
                className={inputClass}
              />
            </div>

            <div>
              <label
                className="mb-1 block text-sm font-medium text-foreground"
                htmlFor="publish-license"
              >
                License <span className="font-normal text-muted-foreground">(recommended)</span>
              </label>
              <input
                id="publish-license"
                list="license-options"
                value={form.license}
                onChange={(event) => setDraft({ ...form, license: event.target.value })}
                placeholder="MIT"
                className={inputClass}
              />
              <datalist id="license-options">
                {LICENSE_SUGGESTIONS.map((license) => (
                  <option key={license} value={license} />
                ))}
              </datalist>
              <p className="mt-1 text-xs text-muted-foreground">
                An SPDX identifier. Leave empty for no license.
              </p>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-3">
            <h2 className="text-base font-semibold text-foreground">Preview</h2>
            <p className="text-sm text-muted-foreground">
              This is what people will see before using the pack.
            </p>
            <div className="max-w-md space-y-2 rounded-xl border border-border bg-background p-5">
              <div className="flex items-center justify-between gap-2">
                <span className="rounded bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                  {packKindLabel(pack.collection_type)}
                </span>
                <span className="rounded border border-border px-2 py-0.5 text-xs font-medium text-muted-foreground">
                  {packSourceLabel(source)}
                </span>
              </div>
              <h3 className="font-semibold text-foreground">{form.name || 'Untitled pack'}</h3>
              <p className="text-sm text-muted-foreground">
                {form.description || 'No description'}
              </p>
              <div className="flex flex-wrap gap-2 pt-1 text-xs text-muted-foreground">
                <span>{pack.artifact_count} items</span>
                {form.license && <span>{form.license}</span>}
                {form.category && <span>{form.category}</span>}
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              Contents are visible read-only to anyone who opens an approved pack, so check for
              secrets before submitting.
            </p>
          </div>
        )}

        {step === 4 && (
          <div className="space-y-4">
            <h2 className="text-base font-semibold text-foreground">Submit for review</h2>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li className="flex items-center gap-2">
                <CheckCircle2
                  className={`h-4 w-4 ${form.name.trim() && form.description.trim() ? 'text-green-600' : 'text-muted-foreground'}`}
                />
                Name and description are filled in.
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2
                  className={`h-4 w-4 ${form.category.trim() ? 'text-green-600' : 'text-muted-foreground'}`}
                />
                A category is selected.
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2
                  className={`h-4 w-4 ${form.license.trim() ? 'text-green-600' : 'text-muted-foreground'}`}
                />
                {form.license.trim()
                  ? `License: ${form.license.trim()}.`
                  : 'No license selected (optional).'}
              </li>
            </ul>

            <div className="rounded-lg border border-border bg-muted/40 p-3 text-sm text-muted-foreground">
              After submitting, the pack shows <strong className="text-foreground">In review</strong>{' '}
              on its page. A moderator can approve it, request changes, or deny it with a reason.
            </div>

            {submitted && (
              <p className="flex items-center gap-2 text-sm text-green-700">
                <Check className="h-4 w-4" />
                Submitted. You are in the moderation queue.
              </p>
            )}
            {publishMutation.isError && (
              <p className="text-sm text-destructive">
                {(publishMutation.error as Error).message}
              </p>
            )}
            {status === 'approved' && (
              <div className="space-y-2 rounded-lg border border-green-200 bg-green-50 p-3">
                <p className="text-sm text-green-800">
                  This pack is already approved. Use the pack page or the Share control to
                  manage it.
                </p>
                <button
                  onClick={() => unpublishMutation.mutate()}
                  disabled={unpublishMutation.isPending}
                  className="rounded-lg border border-green-300 bg-card px-3 py-1.5 text-sm font-medium text-green-900 transition-colors hover:bg-green-100 disabled:opacity-50"
                >
                  {unpublishMutation.isPending ? 'Unpublishing…' : 'Unpublish'}
                </button>
              </div>
            )}
            {status === 'submitted' && (
              <p className="flex items-center gap-2 text-sm text-amber-800">
                <AlertTriangle className="h-4 w-4" />
                Already in review. A moderator decision is pending.
              </p>
            )}
          </div>
        )}

        <div className="flex items-center justify-between border-t border-border pt-4">
          <button
            onClick={() => setStep((current) => Math.max(1, current - 1))}
            disabled={step === 1}
            className="rounded-lg px-4 py-2 text-sm text-muted-foreground transition-colors hover:text-foreground disabled:opacity-40"
          >
            Back
          </button>
          {step < 4 ? (
            <button
              onClick={goNext}
              disabled={step === 2 && (!form.name.trim() || !form.category.trim())}
              className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:opacity-50"
            >
              Continue
              <ArrowRight className="h-4 w-4" />
            </button>
          ) : (
            <button
              onClick={() => publishMutation.mutate()}
              disabled={!canSubmit || publishMutation.isPending}
              className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:opacity-50"
            >
              {publishMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <BookOpen className="h-4 w-4" />
              )}
              Submit for review
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
