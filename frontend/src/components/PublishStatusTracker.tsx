import { AlertTriangle, BookOpen, CheckCircle2, Clock, EyeOff } from 'lucide-react';
import type { PublishStatus } from '../types/packs';

const STEPS: { status: PublishStatus; label: string }[] = [
  { status: 'draft', label: 'Draft' },
  { status: 'submitted', label: 'In review' },
  { status: 'approved', label: 'Approved' },
  { status: 'unpublished', label: 'Unpublished' },
];

/**
 * Owner-facing moderation tracker, shared by the pack detail and the publish
 * wizard. `denied` is shown as "Changes requested" (rule 18's wording) and
 * keeps the moderator's reason visible — never a silent submit.
 */
export function PublishStatusTracker({
  status,
  reason,
}: {
  status: PublishStatus;
  reason?: string | null;
}) {
  const denied = status === 'denied';

  return (
    <div className="rounded-xl border border-border bg-card p-4" data-testid="publish-status">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        {STEPS.map((step) => {
          const active =
            step.status === status ||
            (denied && step.status === 'approved');
          return (
            <div key={step.status} className="flex items-center gap-2">
              <span
                className={`rounded-full border px-2.5 py-1 font-medium ${
                  active
                    ? denied
                      ? 'border-amber-300 bg-amber-50 text-amber-800'
                      : 'border-brand-300 bg-brand-50 text-brand-700'
                    : 'border-border text-muted-foreground'
                }`}
              >
                {denied && step.status === 'approved' ? 'Changes requested' : step.label}
              </span>
              {step.status !== 'unpublished' && <span className="text-muted-foreground">→</span>}
            </div>
          );
        })}
        {status === 'unpublished' && (
          <span className="flex items-center gap-1 text-muted-foreground">
            <EyeOff className="h-3.5 w-3.5" /> Removed from the community library
          </span>
        )}
      </div>

      {status === 'submitted' && (
        <p className="mt-3 flex items-start gap-2 text-sm text-muted-foreground">
          <Clock className="mt-0.5 h-4 w-4 shrink-0" />
          A moderator reviews every submission. You will see the decision here.
        </p>
      )}
      {status === 'approved' && (
        <p className="mt-3 flex items-start gap-2 text-sm text-green-700">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          Approved and visible in the community library.
        </p>
      )}
      {denied && (
        <p className="mt-3 flex items-start gap-2 text-sm text-amber-800">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          Changes requested{reason ? `: ${reason}` : '.'} Edit the pack, then resubmit.
        </p>
      )}
      {status === 'draft' && (
        <p className="mt-3 flex items-start gap-2 text-sm text-muted-foreground">
          <BookOpen className="mt-0.5 h-4 w-4 shrink-0" />
          Not submitted yet. Share this pack with a link from the Share control; publishing
          puts it in the community library.
        </p>
      )}
    </div>
  );
}
