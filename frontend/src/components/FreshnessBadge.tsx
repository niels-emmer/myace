import { ShieldCheck, ShieldQuestion } from 'lucide-react';

// Mirrors the backend's default settings.collection_freshness_threshold_days
// (backend/app/core/config.py, ~6 months). Not read live from the server —
// no endpoint currently exposes it — so an admin-overridden threshold won't
// be reflected here. Good enough for what this badge is: a rough signal,
// not a certified metric (same honesty the backend docs use for it).
const FRESHNESS_THRESHOLD_DAYS = 180;

export function isFreshnessStale(lastVerifiedAt: string | null | undefined): boolean {
  if (!lastVerifiedAt) return true;
  const ageDays = (Date.now() - new Date(lastVerifiedAt).getTime()) / (1000 * 60 * 60 * 24);
  return ageDays > FRESHNESS_THRESHOLD_DAYS;
}

/**
 * "Verified {date}" / "Needs re-check" / "Not yet verified" — honest about
 * what verification means: a human moderator looked at this collection
 * recently and confirmed it's still good. It is NOT an automated check
 * against live tool documentation, and the badge/tooltip copy says so.
 */
export function FreshnessBadge({
  lastVerifiedAt,
  className = '',
}: {
  lastVerifiedAt?: string | null;
  className?: string;
}) {
  if (!lastVerifiedAt) {
    return (
      <span
        title="No moderator has manually confirmed this collection is still good yet."
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-muted text-muted-foreground ${className}`}
      >
        <ShieldQuestion className="h-3 w-3" />
        Not yet verified
      </span>
    );
  }

  if (isFreshnessStale(lastVerifiedAt)) {
    return (
      <span
        title="A moderator last verified this collection more than 6 months ago — it may be out of date."
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-amber-50 text-amber-700 ${className}`}
      >
        <ShieldQuestion className="h-3 w-3" />
        Needs re-check
      </span>
    );
  }

  return (
    <span
      title="A human moderator manually confirmed this collection recently — not an automated check against live tool documentation."
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-green-50 text-green-700 ${className}`}
    >
      <ShieldCheck className="h-3 w-3" />
      Verified {lastVerifiedAt}
    </span>
  );
}
