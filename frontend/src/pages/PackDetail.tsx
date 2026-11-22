import { useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle,
  ArrowLeft,
  BookOpen,
  ChevronDown,
  ChevronRight,
  Copy,
  Download,
  ExternalLink,
  FileText,
  FolderGit2,
  Loader2,
  MessageSquare,
  Pencil,
  Plus,
  ShieldCheck,
  Star,
  Trash2,
  Wrench,
} from 'lucide-react';
import { collectionsApi, commentsApi, moderationApi, profilesApi, ratingsApi } from '../lib/api';
import { packApi } from '../lib/packApi';
import { FreshnessBadge } from '../components/FreshnessBadge';
import { PublishStatusTracker } from '../components/PublishStatusTracker';
import { useAuth } from '../contexts/AuthContext';
import {
  FRAMEWORK_LABELS,
  formatUses,
  packFrameworks,
  packKindLabel,
  packSource,
  packSourceLabel,
} from '../lib/packs';
import type { Artifact, ArtifactType } from '../types';
import type { Pack, PackTab } from '../types/packs';

const ARTIFACT_TYPES: { value: ArtifactType | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'rule', label: 'Rules' },
  { value: 'skill', label: 'Skills' },
  { value: 'agent', label: 'Agents' },
  { value: 'workflow', label: 'Workflows' },
  { value: 'model_config', label: 'Model configs' },
];

const typeColors: Record<string, string> = {
  rule: 'bg-blue-50 text-blue-700',
  skill: 'bg-green-50 text-green-700',
  agent: 'bg-purple-50 text-purple-700',
  workflow: 'bg-amber-50 text-amber-700',
  model_config: 'bg-rose-50 text-rose-700',
};

const TYPE_ORDER: ArtifactType[] = ['rule', 'workflow', 'agent', 'skill', 'model_config'];
const typeRank = (type: ArtifactType): number => {
  const index = TYPE_ORDER.indexOf(type);
  return index === -1 ? TYPE_ORDER.length : index;
};

const inputClass =
  'w-full px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm ' +
  'focus:ring-2 focus:ring-brand-500 focus:border-brand-500';

const SOURCE_CLASSES = {
  starter: 'bg-brand-50 text-brand-700 border-brand-200',
  mine: 'bg-muted text-foreground border-border',
  community: 'bg-card text-muted-foreground border-border',
} as const;

/**
 * Unified pack detail (design §6.5, decision A): owned packs, starter packs
 * and community packs all render here at `/packs/:id`. The old
 * `/packs/community/:id` path redirects to this route.
 *
 * Reads are anonymous-safe: without a session the page uses the public
 * storefront endpoints (ADR-0014); with one it uses the authenticated
 * collection routes, which additionally let the owner/moderator see a
 * non-public pack. The owner's destructive/editing tools stay on
 * `/packs/:id/manage` so this page's layout is identical for everyone.
 */
export default function PackDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user, isLoading: authLoading } = useAuth();
  const loggedIn = !!user;

  const [tab, setTab] = useState<PackTab>('overview');
  const [typeFilter, setTypeFilter] = useState<ArtifactType | 'all'>('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [commentDraft, setCommentDraft] = useState('');
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pickedBaseId, setPickedBaseId] = useState('');
  const [confirmUnpublish, setConfirmUnpublish] = useState(false);
  const [metaEditOpen, setMetaEditOpen] = useState(false);
  const [metaDraft, setMetaDraft] = useState({ name: '', description: '', category: '' });

  const { data: pack, isLoading: loadingPack } = useQuery<Pack>({
    queryKey: loggedIn ? ['collection', id] : ['public-pack', id],
    queryFn: async () =>
      loggedIn ? collectionsApi.get(id!) : packApi.getPublicPack(id!),
    enabled: !!id && !authLoading,
  });

  const { data: artifacts, isLoading: loadingArtifacts } = useQuery({
    queryKey: loggedIn
      ? ['artifacts', id, { include_disabled: false }]
      : ['public-artifacts', id],
    queryFn: async () =>
      loggedIn
        ? collectionsApi.getArtifacts(id!, { include_disabled: false })
        : packApi.getPublicArtifacts(id!),
    enabled: !!id && !authLoading,
  });

  const isOwner = !!user && !!pack && user.id === pack.owner_id;
  const ratedPack = !!pack && pack.moderation_status === 'approved';

  const { data: ratingSummary } = useQuery({
    queryKey: ['pack-rating', id],
    queryFn: () => ratingsApi.get(id!),
    enabled: !!id && loggedIn && ratedPack,
  });

  const { data: comments, isLoading: loadingComments } = useQuery({
    queryKey: ['pack-comments', id],
    queryFn: () => commentsApi.list(id!),
    enabled: !!id && loggedIn && ratedPack,
  });

  // Starting points for an add-on's "Use this pack" pairing. Public listing,
  // so it works for every signed-in user without a second auth path.
  const { data: basePacks } = useQuery({
    queryKey: ['community-collections', { type: 'base', sort: 'alpha', limit: 100 }],
    queryFn: () => packApi.listCommunity({ type: 'base', sort: 'alpha', limit: 100 }),
    enabled: pickerOpen,
  });

  const rateMutation = useMutation({
    mutationFn: (stars: number) => ratingsApi.rate(id!, stars),
    onSuccess: (data) => {
      queryClient.setQueryData(['pack-rating', id], data);
      // Signed-in reads use ['collection', id]; anonymous reads use
      // ['public-pack', id]. Refresh whichever the header is rendering.
      queryClient.invalidateQueries({ queryKey: ['collection', id] });
      queryClient.invalidateQueries({ queryKey: ['public-pack', id] });
    },
  });

  const removeRatingMutation = useMutation({
    mutationFn: () => ratingsApi.remove(id!),
    onSuccess: (data) => {
      queryClient.setQueryData(['pack-rating', id], data);
      queryClient.invalidateQueries({ queryKey: ['collection', id] });
      queryClient.invalidateQueries({ queryKey: ['public-pack', id] });
    },
  });

  const createCommentMutation = useMutation({
    mutationFn: (body: string) => commentsApi.create(id!, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pack-comments', id] });
      setCommentDraft('');
    },
  });

  const deleteCommentMutation = useMutation({
    mutationFn: (commentId: string) => commentsApi.remove(id!, commentId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['pack-comments', id] }),
  });

  // "Use this pack" records the reference use AND creates the setup that
  // holds the reference (POST /profiles persists base + add-ons and captures
  // the Phase 3 pack snapshots). For an add-on, the chosen starting point is
  // the new setup's base — so the pairing is actually saved, not just shown.
  const useMutationResult = useMutation({
    mutationFn: async () => {
      const baseId = isAddon ? selectedBaseId : pack!.id;
      const additionalIds = isAddon ? [pack!.id] : [];
      await packApi.usePack(pack!.id);
      return profilesApi.create({
        // `Profile.name` is String(255); two user-controlled pack names can
        // exceed that on Postgres, so cap the generated name.
        name: (
          isAddon
            ? `${selectedBaseName ?? 'New setup'} + ${pack!.name}`
            : pack!.name
        ).slice(0, 255),
        description: isAddon
          ? `Adds the ${pack!.name} pack to ${selectedBaseName ?? 'a starting point'}.`
          : pack!.description ?? undefined,
        base_collection_id: baseId,
        additional_collection_ids: additionalIds,
      });
    },
    onSuccess: (profile) => {
      setPickerOpen(false);
      queryClient.invalidateQueries({ queryKey: ['profiles'] });
      queryClient.invalidateQueries({ queryKey: ['public-pack', id] });
      queryClient.invalidateQueries({ queryKey: ['collection', id] });
      queryClient.invalidateQueries({ queryKey: ['community-collections'] });
      navigate(`/setups/${profile.id}`);
    },
  });

  const copyMutation = useMutation({
    mutationFn: () => collectionsApi.importCommunity(id!),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['collections'] });
      navigate(`/packs/${result.collection_id}`);
    },
  });

  const unpublishMutation = useMutation({
    mutationFn: () => collectionsApi.unpublish(id!),
    onSuccess: (updated) => {
      queryClient.setQueryData(['collection', id], updated);
      queryClient.invalidateQueries({ queryKey: ['collections'] });
      queryClient.invalidateQueries({ queryKey: ['public-pack', id] });
      queryClient.invalidateQueries({ queryKey: ['community-collections'] });
      setConfirmUnpublish(false);
    },
  });

  // Moderator capabilities from the old community detail page (rule 37/40
  // reviewed content). Read-only for everyone else.
  const canModerate =
    !!user && user.id !== pack?.owner_id && (user.role === 'moderator' || user.role === 'admin');

  const verifyMutation = useMutation({
    mutationFn: () => collectionsApi.verify(id!),
    onSuccess: (updated) => {
      queryClient.setQueryData(['collection', id], updated);
      queryClient.invalidateQueries({ queryKey: ['community-collections'] });
    },
  });

  const metaMutation = useMutation({
    mutationFn: () =>
      moderationApi.updateMeta(id!, {
        name: metaDraft.name.trim(),
        description: metaDraft.description.trim(),
        category: metaDraft.category.trim(),
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(['collection', id], updated);
      queryClient.invalidateQueries({ queryKey: ['community-collections'] });
      setMetaEditOpen(false);
    },
  });

  // Preselect a sensible starting point once the public base list arrives,
  // without an effect: the pick and the fallback are derived during render.
  // Never ranked by download_count (advisory only, invariant 25).
  const preferredBaseId =
    (basePacks?.items ?? []).find((base) => base.is_starter_pack)?.id ??
    basePacks?.items?.[0]?.id ??
    '';
  const selectedBaseId = pickedBaseId || preferredBaseId;
  const selectedBaseName = (basePacks?.items ?? []).find(
    (base) => base.id === selectedBaseId,
  )?.name;

  const visibleArtifacts = useMemo(() => {
    const filtered =
      typeFilter === 'all'
        ? (artifacts ?? [])
        : (artifacts ?? []).filter((artifact) => artifact.artifact_type === typeFilter);
    return [...filtered].sort(
      (a, b) => typeRank(a.artifact_type) - typeRank(b.artifact_type) || a.name.localeCompare(b.name),
    );
  }, [artifacts, typeFilter]);

  const typeCounts = useMemo(() => {
    const counts: Partial<Record<ArtifactType, number>> = {};
    for (const artifact of artifacts ?? []) {
      counts[artifact.artifact_type] = (counts[artifact.artifact_type] ?? 0) + 1;
    }
    return counts;
  }, [artifacts]);

  if (authLoading || loadingPack) {
    return <div className="py-12 text-center text-muted-foreground">Loading pack…</div>;
  }

  if (!pack) {
    return (
      <div className="py-12 text-center text-muted-foreground">
        Pack not found. It may have been unpublished.{' '}
        <Link to="/packs" className="text-brand-600 hover:underline">
          Browse packs
        </Link>
        .
      </div>
    );
  }

  const source = packSource(pack, user?.id);
  const kind = packKindLabel(pack.collection_type);
  const isAddon = pack.collection_type === 'additional';
  const frameworks = packFrameworks(artifacts ?? []);
  const useCount = pack.download_count;
  const signupHref = '/login?mode=register';

  const beginUse = () => {
    if (isAddon) {
      setPickerOpen(true);
      return;
    }
    useMutationResult.mutate();
  };

  const commentCanDelete = (commentUserId: string) =>
    !!user &&
    (user.id === commentUserId ||
      isOwner ||
      user.role === 'moderator' ||
      user.role === 'admin');

  return (
    <div className="space-y-6">
      <button
        onClick={() => navigate('/packs')}
        className="flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Packs
      </button>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="min-w-0 space-y-5">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                {kind}
              </span>
              <span
                className={`rounded border px-2 py-0.5 text-xs font-medium ${SOURCE_CLASSES[source]}`}
              >
                {packSourceLabel(source)}
              </span>
              {pack.category && (
                <span className="rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                  {pack.category}
                </span>
              )}
              <FreshnessBadge lastVerifiedAt={pack.last_verified_at} />
            </div>
            <h1 className="mt-3 text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
              {pack.name}
            </h1>
            <p className="mt-2 max-w-2xl text-muted-foreground">
              {pack.description || 'No description'}
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
              {pack.rating_count > 0 && (
                <span className="flex items-center gap-1">
                  <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
                  {pack.avg_rating.toFixed(1)} ({pack.rating_count}{' '}
                  {pack.rating_count === 1 ? 'rating' : 'ratings'})
                </span>
              )}
              <span className="flex items-center gap-1">
                <Download className="h-3.5 w-3.5" />
                used {useCount} {useCount === 1 ? 'time' : 'times'}
              </span>
              <span>{pack.artifact_count} items</span>
              {pack.license && <span>{pack.license}</span>}
            </div>
          </div>

          {isOwner && (
            <PublishStatusTracker
              status={pack.moderation_status}
              reason={pack.moderation_reason}
            />
          )}

          <div role="tablist" aria-label="Pack sections" className="flex gap-1 border-b border-border">
            {(
              [
                ['overview', 'Overview'],
                ['contents', 'Contents'],
                ['ratings', 'Ratings & comments'],
              ] as [PackTab, string][]
            ).map(([value, label]) => (
              <button
                key={value}
                role="tab"
                aria-selected={tab === value}
                onClick={() => setTab(value)}
                className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
                  tab === value
                    ? 'border-brand-600 text-brand-700'
                    : 'border-transparent text-muted-foreground hover:text-foreground'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {tab === 'overview' && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {(
                  [
                    ['rule', 'Rules'],
                    ['skill', 'Skills'],
                    ['agent', 'Agents'],
                    ['workflow', 'Workflows'],
                  ] as [ArtifactType, string][]
                ).map(([type, label]) => (
                  <div key={type} className="rounded-lg border border-border bg-card p-3">
                    <p className="text-xl font-bold text-card-foreground">
                      {typeCounts[type] ?? 0}
                    </p>
                    <p className="text-xs text-muted-foreground">{label}</p>
                  </div>
                ))}
              </div>

              <div>
                <h2 className="text-sm font-semibold text-foreground">Works with</h2>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {frameworks.map((framework) => (
                    <span
                      key={framework}
                      className="rounded border border-border px-2 py-0.5 text-xs text-muted-foreground"
                    >
                      {framework}
                    </span>
                  ))}
                </div>
              </div>

              {pack.category && (
                <div className="rounded-lg border border-border bg-card p-4 text-sm text-muted-foreground">
                  <span className="font-medium text-foreground">Category:</span> {pack.category}
                  {pack.license && (
                    <>
                      <span className="mx-2 text-border">·</span>
                      <span className="font-medium text-foreground">License:</span> {pack.license}
                    </>
                  )}
                </div>
              )}
            </div>
          )}

          {tab === 'contents' && (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                {ARTIFACT_TYPES.map((item) => {
                  const count =
                    item.value === 'all'
                      ? artifacts?.length ?? 0
                      : typeCounts[item.value] ?? 0;
                  return (
                    <button
                      key={item.value}
                      onClick={() => setTypeFilter(item.value)}
                      aria-pressed={typeFilter === item.value}
                      className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors ${
                        typeFilter === item.value
                          ? 'border-brand-500 bg-brand-50 text-brand-700'
                          : 'border-border text-muted-foreground hover:border-input'
                      }`}
                    >
                      {item.label} <span className="text-xs opacity-60">({count})</span>
                    </button>
                  );
                })}
              </div>

              {loadingArtifacts ? (
                <p className="py-8 text-center text-sm text-muted-foreground">Loading items…</p>
              ) : visibleArtifacts.length > 0 ? (
                <div className="divide-y divide-border rounded-xl border border-border bg-card">
                  {visibleArtifacts.map((artifact) => (
                    <ArtifactRow
                      key={artifact.id}
                      artifact={artifact}
                      isExpanded={expandedId === artifact.id}
                      onToggleExpand={() =>
                        setExpandedId(expandedId === artifact.id ? null : artifact.id)
                      }
                    />
                  ))}
                </div>
              ) : (
                <div className="rounded-xl border border-border bg-card py-10 text-center">
                  <FolderGit2 className="mx-auto mb-2 h-10 w-10 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">
                    {typeFilter === 'all'
                      ? 'This pack has no items.'
                      : `No ${typeFilter} items in this pack.`}
                  </p>
                </div>
              )}
            </div>
          )}

          {tab === 'ratings' && (
            <div className="space-y-5">
              <div className="flex items-center gap-4 rounded-xl border border-border bg-card p-5">
                <p className="text-3xl font-bold text-card-foreground">
                  {(ratingSummary?.avg_rating ?? pack.avg_rating ?? 0).toFixed(1)}
                </p>
                <div>
                  <div className="flex items-center gap-1">
                    {[1, 2, 3, 4, 5].map((n) => (
                      <Star
                        key={n}
                        className={`h-4 w-4 ${
                          n <= Math.round(ratingSummary?.avg_rating ?? pack.avg_rating ?? 0)
                            ? 'fill-amber-400 text-amber-400'
                            : 'text-muted-foreground'
                        }`}
                      />
                    ))}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {ratingSummary?.rating_count ?? pack.rating_count}{' '}
                    {(ratingSummary?.rating_count ?? pack.rating_count) === 1
                      ? 'rating'
                      : 'ratings'}
                  </p>
                </div>
              </div>

              {!loggedIn ? (
                <div className="rounded-xl border border-border bg-card p-5">
                  <p className="text-sm text-muted-foreground">
                    <Link to={signupHref} className="font-medium text-brand-600 hover:underline">
                      Create an account
                    </Link>{' '}
                    to rate and comment on this pack.
                  </p>
                </div>
              ) : !ratedPack ? (
                <p className="text-sm text-muted-foreground">
                  Ratings and comments open once this pack is approved.
                </p>
              ) : isOwner ? (
                <p className="text-sm text-muted-foreground">
                  You cannot rate your own pack, but you can read and moderate comments.
                </p>
              ) : (
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">Your rating:</span>
                  {[1, 2, 3, 4, 5].map((n) => (
                    <button
                      key={n}
                      onClick={() => rateMutation.mutate(n)}
                      disabled={rateMutation.isPending}
                      title={`Rate ${n} star${n > 1 ? 's' : ''}`}
                      className="p-0.5 disabled:opacity-50"
                    >
                      <Star
                        className={`h-5 w-5 transition-colors ${
                          ratingSummary?.my_rating && n <= ratingSummary.my_rating
                            ? 'fill-amber-400 text-amber-400'
                            : 'text-muted-foreground hover:text-amber-400'
                        }`}
                      />
                    </button>
                  ))}
                  {ratingSummary?.my_rating != null && (
                    <button
                      onClick={() => removeRatingMutation.mutate()}
                      disabled={removeRatingMutation.isPending}
                      className="ml-1 text-xs text-muted-foreground hover:text-destructive"
                    >
                      Clear
                    </button>
                  )}
                </div>
              )}

              {loggedIn && ratedPack && (
                <div className="space-y-4 rounded-xl border border-border bg-card p-5">
                  <h2 className="flex items-center gap-2 text-sm font-semibold text-foreground">
                    <MessageSquare className="h-4 w-4" />
                    Comments {comments && comments.length > 0 && `(${comments.length})`}
                  </h2>
                  <div className="flex gap-2">
                    <textarea
                      value={commentDraft}
                      onChange={(event) => setCommentDraft(event.target.value)}
                      rows={2}
                      maxLength={2000}
                      placeholder="Leave a comment..."
                      className={inputClass}
                    />
                    <button
                      onClick={() => createCommentMutation.mutate(commentDraft.trim())}
                      disabled={!commentDraft.trim() || createCommentMutation.isPending}
                      className="flex-shrink-0 self-end rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:opacity-50"
                    >
                      Post
                    </button>
                  </div>
                  {createCommentMutation.isError && (
                    <p className="text-sm text-destructive">
                      {(createCommentMutation.error as Error).message}
                    </p>
                  )}

                  {loadingComments ? (
                    <p className="text-sm text-muted-foreground">Loading comments...</p>
                  ) : comments && comments.length > 0 ? (
                    <div className="space-y-4 pt-1">
                      {comments.map((comment) => (
                        <div
                          key={comment.id}
                          className="flex items-start justify-between gap-3 border-t border-border pt-3 first:border-0 first:pt-0"
                        >
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-medium text-card-foreground">
                                {comment.author_display_name}
                              </span>
                              <span className="text-xs text-muted-foreground">
                                {new Date(comment.created_at).toLocaleString()}
                              </span>
                            </div>
                            <p className="mt-0.5 whitespace-pre-wrap break-words text-sm text-muted-foreground">
                              {comment.body}
                            </p>
                          </div>
                          {commentCanDelete(comment.user_id) && (
                            <button
                              onClick={() => deleteCommentMutation.mutate(comment.id)}
                              disabled={deleteCommentMutation.isPending}
                              title="Delete comment"
                              className="flex-shrink-0 p-1 text-muted-foreground transition-colors hover:text-destructive"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">No comments yet.</p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        <aside className="space-y-4">
          <div className="space-y-2 rounded-xl border border-border bg-card p-4">
            {isOwner ? (
              <>
                <Link
                  to={`/packs/${pack.id}/publish`}
                  className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700"
                >
                  <BookOpen className="h-4 w-4" />
                  {pack.moderation_status === 'approved' ? 'Manage publication' : 'Publish…'}
                </Link>
                <Link
                  to={`/packs/${pack.id}/manage`}
                  className="flex w-full items-center justify-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
                >
                  <Wrench className="h-4 w-4" />
                  Manage items
                </Link>
                {pack.moderation_status === 'approved' && (
                  <button
                    onClick={() => setConfirmUnpublish(true)}
                    className="flex w-full items-center justify-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium text-destructive transition-colors hover:bg-destructive/10"
                  >
                    <AlertTriangle className="h-4 w-4" />
                    Unpublish
                  </button>
                )}
              </>
            ) : loggedIn ? (
              <>
                <button
                  onClick={beginUse}
                  disabled={useMutationResult.isPending}
                  className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:opacity-50"
                >
                  {useMutationResult.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Plus className="h-4 w-4" />
                  )}
                  Use this pack
                </button>
                <Link
                  to="/setups"
                  className="flex w-full items-center justify-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
                >
                  View my setups
                </Link>
                <button
                  onClick={() => copyMutation.mutate()}
                  disabled={copyMutation.isPending}
                  className="flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
                >
                  {copyMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                  Customize a copy
                </button>
                <p className="text-xs text-muted-foreground">
                  Referenced packs receive publisher updates. Customize a copy if you want to
                  edit.
                </p>
              </>
            ) : (
              <>
                <Link
                  to={signupHref}
                  className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700"
                >
                  Use this pack
                </Link>
                <Link
                  to={signupHref}
                  className="flex w-full items-center justify-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
                >
                  Add to a setup…
                </Link>
                <Link
                  to={signupHref}
                  className="flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
                >
                  Customize a copy
                </Link>
                <p className="text-xs text-muted-foreground">
                  Browsing is free. Sign up to build a setup, install it, or customize a copy.
                </p>
              </>
            )}


            {copyMutation.isError && (
              <p className="text-xs text-destructive">
                {(copyMutation.error as Error).message}
              </p>
            )}
            {useMutationResult.isError && (
              <p className="text-xs text-destructive">
                {(useMutationResult.error as Error).message}
              </p>
            )}
          </div>

          {canModerate && (
            <div className="space-y-2 rounded-xl border border-border bg-card p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Moderator tools
              </p>
              <button
                onClick={() => verifyMutation.mutate()}
                disabled={verifyMutation.isPending}
                title="Confirm you've manually reviewed this pack and it's still good — not an automated check."
                className="flex w-full items-center justify-center gap-2 rounded-lg border border-border px-3 py-2 text-sm text-foreground transition-colors hover:bg-accent disabled:opacity-50"
              >
                {verifyMutation.isPending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <ShieldCheck className="h-3.5 w-3.5" />
                )}
                Mark verified
              </button>
              <button
                onClick={() => {
                  metaMutation.reset();
                  setMetaDraft({
                    name: pack.name,
                    description: pack.description ?? '',
                    category: pack.category ?? '',
                  });
                  setMetaEditOpen(true);
                }}
                className="flex w-full items-center justify-center gap-2 rounded-lg border border-border px-3 py-2 text-sm text-foreground transition-colors hover:bg-accent"
              >
                <Pencil className="h-3.5 w-3.5" />
                Edit metadata
              </button>
              {pack.moderation_status === 'approved' && (
                <button
                  onClick={() => setConfirmUnpublish(true)}
                  className="flex w-full items-center justify-center gap-2 rounded-lg border border-border px-3 py-2 text-sm text-destructive transition-colors hover:bg-destructive/10"
                >
                  <AlertTriangle className="h-3.5 w-3.5" />
                  Unpublish
                </button>
              )}
            </div>
          )}

          <div className="space-y-2 rounded-xl border border-border bg-card p-4 text-sm">
            <div className="flex justify-between gap-3">
              <span className="text-muted-foreground">Kind</span>
              <span className="text-foreground">{kind}</span>
            </div>
            <div className="flex justify-between gap-3">
              <span className="text-muted-foreground">Items</span>
              <span className="text-foreground">{pack.artifact_count}</span>
            </div>
            <div className="flex justify-between gap-3">
              <span className="text-muted-foreground">Frameworks</span>
              <span className="text-foreground">
                {frameworks.length === FRAMEWORK_LABELS.length ? 'All 12' : frameworks.length}
              </span>
            </div>
            <div className="flex justify-between gap-3">
              <span className="text-muted-foreground">License</span>
              <span className="text-foreground">{pack.license || 'Not specified'}</span>
            </div>
            <div className="flex justify-between gap-3">
              <span className="text-muted-foreground">Used</span>
              <span className="text-foreground">{formatUses(useCount)}</span>
            </div>
          </div>
        </aside>
      </div>

      {pickerOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md space-y-4 rounded-xl border border-border bg-card p-6">
            <h2 className="text-lg font-semibold text-card-foreground">
              Pair this add-on with a starting point
            </h2>
            <p className="text-sm text-muted-foreground">
              Add-ons layer onto a starting point. Pick the one this new setup begins from —
              you can change its frameworks and install it next.
            </p>
            <select
              value={selectedBaseId}
              onChange={(event) => setPickedBaseId(event.target.value)}
              className={inputClass}
              aria-label="Starting point"
            >
              <option value="">Select a starting point…</option>
              {(basePacks?.items ?? []).map((base) => (
                <option key={base.id} value={base.id}>
                  {base.name}
                </option>
              ))}
            </select>
            {useMutationResult.isError && (
              <p className="text-sm text-destructive">
                {(useMutationResult.error as Error).message}
              </p>
            )}
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setPickerOpen(false)}
                className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground"
              >
                Cancel
              </button>
              <button
                onClick={() => useMutationResult.mutate()}
                disabled={!selectedBaseId || useMutationResult.isPending}
                className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:opacity-50"
              >
                {useMutationResult.isPending ? 'Creating setup…' : 'Create setup with this add-on'}
              </button>
            </div>
          </div>
        </div>
      )}

      {metaEditOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md space-y-4 rounded-xl border border-border bg-card p-6">
            <h2 className="flex items-center gap-2 text-lg font-semibold text-card-foreground">
              <Pencil className="h-5 w-5" />
              Edit metadata
            </h2>
            <p className="-mt-2 text-sm text-muted-foreground">
              Moderator edit — only name, description and category. Item content is not affected.
            </p>
            <div>
              <label className="mb-1 block text-sm font-medium text-foreground" htmlFor="meta-name">
                Name
              </label>
              <input
                id="meta-name"
                value={metaDraft.name}
                onChange={(event) => setMetaDraft({ ...metaDraft, name: event.target.value })}
                className={inputClass}
              />
            </div>
            <div>
              <label
                className="mb-1 block text-sm font-medium text-foreground"
                htmlFor="meta-description"
              >
                Description
              </label>
              <textarea
                id="meta-description"
                value={metaDraft.description}
                onChange={(event) =>
                  setMetaDraft({ ...metaDraft, description: event.target.value })
                }
                rows={3}
                className={inputClass}
              />
            </div>
            <div>
              <label
                className="mb-1 block text-sm font-medium text-foreground"
                htmlFor="meta-category"
              >
                Category
              </label>
              <input
                id="meta-category"
                value={metaDraft.category}
                onChange={(event) => setMetaDraft({ ...metaDraft, category: event.target.value })}
                className={inputClass}
              />
            </div>
            {metaMutation.isError && (
              <p className="text-sm text-destructive">{(metaMutation.error as Error).message}</p>
            )}
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setMetaEditOpen(false)}
                className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground"
              >
                Cancel
              </button>
              <button
                onClick={() => metaMutation.mutate()}
                disabled={!metaDraft.name.trim() || metaMutation.isPending}
                className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:opacity-50"
              >
                {metaMutation.isPending ? 'Saving…' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}

      {confirmUnpublish && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-sm space-y-4 rounded-xl border border-border bg-card p-6">
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 rounded-lg bg-amber-100 p-2">
                <AlertTriangle className="h-5 w-5 text-amber-700" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-card-foreground">
                  Unpublish &ldquo;{pack.name}&rdquo;?
                </h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  This removes it from the community library and makes it private again. You can
                  resubmit it for review later.
                </p>
              </div>
            </div>
            {unpublishMutation.isError && (
              <p className="text-sm text-destructive">
                {(unpublishMutation.error as Error).message}
              </p>
            )}
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setConfirmUnpublish(false)}
                className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground"
              >
                Cancel
              </button>
              <button
                onClick={() => unpublishMutation.mutate()}
                disabled={unpublishMutation.isPending}
                className="rounded-lg bg-amber-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-amber-700 disabled:opacity-50"
              >
                {unpublishMutation.isPending ? 'Unpublishing…' : 'Unpublish'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ArtifactRow({
  artifact,
  isExpanded,
  onToggleExpand,
}: {
  artifact: Artifact;
  isExpanded: boolean;
  onToggleExpand: () => void;
}) {
  return (
    <div>
      <button
        onClick={onToggleExpand}
        aria-expanded={isExpanded}
        aria-label={isExpanded ? `Collapse ${artifact.name}` : `Expand ${artifact.name}`}
        className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-accent/40"
      >
        {isExpanded ? (
          <ChevronDown className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
        )}
        <span className="min-w-0 flex-1 truncate text-sm font-medium text-card-foreground">
          {artifact.name}
        </span>
        <span
          className={`rounded px-1.5 py-0.5 text-xs font-medium ${
            typeColors[artifact.artifact_type] ?? 'bg-muted text-muted-foreground'
          }`}
        >
          {artifact.artifact_type}
        </span>
        <span className="flex-shrink-0 text-xs text-muted-foreground">p{artifact.priority}</span>
      </button>
      {isExpanded && (
        <div className="space-y-2 px-4 pb-4 pl-11">
          {artifact.description && (
            <p className="text-sm text-muted-foreground">{artifact.description}</p>
          )}
          <div className="max-h-80 overflow-y-auto overflow-x-auto rounded-lg bg-muted p-3">
            <pre className="whitespace-pre-wrap font-mono text-xs text-foreground">
              {artifact.body}
            </pre>
          </div>
          <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <FileText className="h-3 w-3" />
              {artifact.file_path}
            </span>
            {artifact.tags.length > 0 && <span>Tags: {artifact.tags.join(', ')}</span>}
            {artifact.target_compatibility.length > 0 && (
              <span>Targets: {artifact.target_compatibility.join(', ')}</span>
            )}
            {artifact.handoff_to && artifact.handoff_to.length > 0 && (
              <span className="flex items-center gap-1">
                <ExternalLink className="h-3 w-3" />
                Hands off to {artifact.handoff_to.join(', ')}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
