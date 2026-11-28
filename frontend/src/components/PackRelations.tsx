import { Link } from 'react-router-dom';
import { Layers, Link2 } from 'lucide-react';
import type { PackRef, PackRelations as PackRelationsData } from '../types/packs';

/**
 * "Works with other packs" card for the pack page.
 *
 * `layers_on` is what the pack assumes is in the same setup; `pairs_with` is a
 * suggestion. Both are advisory (rule 34), so this only informs. Renders
 * nothing when the pack declares no relations that resolve.
 */
function RefList({ refs }: { refs: PackRef[] }) {
  return (
    <ul className="mt-1 flex flex-wrap gap-1.5">
      {refs.map((ref) => (
        <li key={ref.id}>
          <Link
            to={`/packs/${ref.id}`}
            className="inline-block rounded border border-border bg-card px-2 py-0.5 text-xs font-medium text-foreground transition-colors hover:border-brand-300 hover:text-brand-700"
          >
            {ref.name}
          </Link>
        </li>
      ))}
    </ul>
  );
}

export function PackRelationsCard({ relations }: { relations?: PackRelationsData | null }) {
  const layersOn = relations?.layers_on ?? [];
  const pairsWith = relations?.pairs_with ?? [];
  if (layersOn.length === 0 && pairsWith.length === 0) return null;

  return (
    <section
      aria-labelledby="pack-relations-heading"
      className="space-y-3 rounded-lg border border-border bg-card p-4"
    >
      <h2 id="pack-relations-heading" className="text-sm font-semibold text-foreground">
        Works with other packs
      </h2>
      {layersOn.length > 0 && (
        <div>
          <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Layers className="h-3.5 w-3.5" aria-hidden="true" />
            <span>
              <span className="font-medium text-foreground">Layers on</span> — assumes{' '}
              {layersOn.length === 1 ? 'this pack is' : 'these packs are'} in the same setup
            </span>
          </p>
          <RefList refs={layersOn} />
        </div>
      )}
      {pairsWith.length > 0 && (
        <div>
          <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Link2 className="h-3.5 w-3.5" aria-hidden="true" />
            <span>
              <span className="font-medium text-foreground">Pairs well with</span> — a suggestion,
              not a requirement
            </span>
          </p>
          <RefList refs={pairsWith} />
        </div>
      )}
    </section>
  );
}
