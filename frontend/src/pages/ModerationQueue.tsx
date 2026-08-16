import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ShieldCheck, Check, X, ExternalLink } from 'lucide-react';
import { moderationApi } from '../lib/api';
import type { ModerationQueueItem } from '../types';

const inputClass =
  'w-full px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm ' +
  'focus:ring-2 focus:ring-brand-500 focus:border-brand-500';

type SortOption = 'submitted_at' | 'rating' | 'downloads' | 'alpha';

const SORT_LABELS: Record<SortOption, string> = {
  submitted_at: 'Oldest submitted first',
  rating: 'Highest rated',
  downloads: 'Most downloaded',
  alpha: 'Name (A–Z)',
};

function formatDate(value?: string): string {
  if (!value) return '—';
  return new Date(value).toLocaleString();
}

export default function ModerationQueue() {
  const queryClient = useQueryClient();
  const [denyTarget, setDenyTarget] = useState<ModerationQueueItem | null>(null);
  const [denyReason, setDenyReason] = useState('');
  const [sort, setSort] = useState<SortOption>('submitted_at');

  const { data: queue, isLoading } = useQuery({
    queryKey: ['moderation-queue', { sort }],
    queryFn: () => moderationApi.getQueue(sort),
  });

  const approveMutation = useMutation({
    mutationFn: (collectionId: string) => moderationApi.approve(collectionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['moderation-queue'] });
      queryClient.invalidateQueries({ queryKey: ['community-collections'] });
    },
  });

  const denyMutation = useMutation({
    mutationFn: ({ collectionId, reason }: { collectionId: string; reason: string }) =>
      moderationApi.deny(collectionId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['moderation-queue'] });
      setDenyTarget(null);
      setDenyReason('');
    },
  });

  const openDenyModal = (collection: ModerationQueueItem) => {
    denyMutation.reset();
    setDenyReason('');
    setDenyTarget(collection);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
          <ShieldCheck className="h-6 w-6 text-muted-foreground" />
          Moderation Queue
        </h1>
        <p className="text-muted-foreground mt-1">
          Collections submitted for community publishing. Approving makes a collection public
          immediately; denying requires a reason the submitter will see.
        </p>
      </div>

      <div className="flex justify-end">
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value as SortOption)}
          className="px-3 py-1.5 bg-background text-foreground border border-input rounded-lg text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
        >
          {(Object.keys(SORT_LABELS) as SortOption[]).map((key) => (
            <option key={key} value={key}>
              {SORT_LABELS[key]}
            </option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading queue...</p>
      ) : queue && queue.length > 0 ? (
        <div className="bg-card border border-border rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/50">
                  <th className="text-left py-3 px-4 font-medium text-muted-foreground">Name</th>
                  <th className="text-left py-3 px-4 font-medium text-muted-foreground">Owner</th>
                  <th className="text-left py-3 px-4 font-medium text-muted-foreground">Category</th>
                  <th className="text-left py-3 px-4 font-medium text-muted-foreground">Submitted</th>
                  <th className="text-right py-3 px-4 font-medium text-muted-foreground">Actions</th>
                </tr>
              </thead>
              <tbody>
                {queue.map((c) => (
                  <tr key={c.id} className="border-b border-border/50 last:border-0">
                    <td className="py-3 px-4 text-card-foreground font-medium">
                      <Link
                        to={`/collections/${c.id}`}
                        className="hover:text-brand-600 inline-flex items-center gap-1"
                      >
                        {c.name}
                        <ExternalLink className="h-3 w-3 text-muted-foreground" />
                      </Link>
                    </td>
                    <td className="py-3 px-4 text-muted-foreground">
                      {c.owner_display_name || c.owner_email}
                    </td>
                    <td className="py-3 px-4 text-muted-foreground">{c.category || '—'}</td>
                    <td className="py-3 px-4 text-muted-foreground">
                      {formatDate(c.submitted_at)}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => approveMutation.mutate(c.id)}
                          disabled={approveMutation.isPending}
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-green-50 text-green-700 border border-green-200 rounded-lg hover:bg-green-100 disabled:opacity-50 text-xs font-medium transition-colors"
                        >
                          <Check className="h-3.5 w-3.5" />
                          Approve
                        </button>
                        <button
                          onClick={() => openDenyModal(c)}
                          disabled={denyMutation.isPending}
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-red-50 text-red-700 border border-red-200 rounded-lg hover:bg-red-100 disabled:opacity-50 text-xs font-medium transition-colors"
                        >
                          <X className="h-3.5 w-3.5" />
                          Deny
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          Nothing awaiting review right now.
        </p>
      )}

      {approveMutation.isError && (
        <p className="text-sm text-destructive">
          {(approveMutation.error as Error).message}
        </p>
      )}

      {/* Deny Modal */}
      {denyTarget && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-card border border-border rounded-xl p-6 w-full max-w-md space-y-4">
            <h2 className="text-lg font-semibold text-card-foreground">
              Deny &ldquo;{denyTarget.name}&rdquo;?
            </h2>
            <p className="text-sm text-muted-foreground -mt-2">
              The submitter will see this reason and can edit their collection and resubmit it
              for another review.
            </p>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                Reason <span className="text-destructive">*</span>
              </label>
              <textarea
                value={denyReason}
                onChange={(e) => setDenyReason(e.target.value)}
                rows={3}
                className={inputClass}
                placeholder="What needs to change before this can be approved?"
                autoFocus
              />
            </div>

            {denyMutation.isError && (
              <p className="text-sm text-destructive">
                {(denyMutation.error as Error).message}
              </p>
            )}

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDenyTarget(null)}
                className="px-4 py-2 text-sm text-muted-foreground hover:text-accent-foreground"
              >
                Cancel
              </button>
              <button
                onClick={() =>
                  denyMutation.mutate({ collectionId: denyTarget.id, reason: denyReason })
                }
                disabled={!denyReason.trim() || denyMutation.isPending}
                className="px-4 py-2 bg-destructive text-white rounded-lg hover:bg-destructive/90 disabled:opacity-50 text-sm font-medium transition-colors"
              >
                {denyMutation.isPending ? 'Denying...' : 'Deny'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
