import { AlertTriangle, Eye, EyeOff } from 'lucide-react';
import type { Collection, ProfileCreate } from '../types';
import type { NameCollision } from '../lib/collisions';

const inputClass =
  'w-full px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500';

interface ProfileFormFieldsProps {
  value: ProfileCreate;
  onChange: (value: ProfileCreate) => void;
  baseCollections: Collection[];
  additionalCollections: Collection[];
  targets: string[];
  /** Name collisions across the selected collections (empty when none). */
  collisions?: NameCollision[];
  /** Adds a losing artifact's id to `disabled_artifact_ids`. */
  onDisableArtifact?: (artifactId: string) => void;
}

export default function ProfileFormFields({
  value,
  onChange,
  baseCollections,
  additionalCollections,
  targets,
  collisions = [],
  onDisableArtifact,
}: ProfileFormFieldsProps) {
  const toggleAdditional = (id: string) => {
    const current = value.additional_collection_ids ?? [];
    onChange({
      ...value,
      additional_collection_ids: current.includes(id)
        ? current.filter((cid) => cid !== id)
        : [...current, id],
    });
  };

  // Look up a collection's display name by id for the collision messages.
  const collectionName = (id: string): string =>
    [...baseCollections, ...additionalCollections].find((c) => c.id === id)?.name ?? id;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">Profile Name</label>
          <input
            type="text"
            value={value.name}
            onChange={(e) => onChange({ ...value, name: e.target.value })}
            className={inputClass}
            required
            autoFocus
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">Description</label>
          <input
            type="text"
            value={value.description ?? ''}
            onChange={(e) => onChange({ ...value, description: e.target.value })}
            className={inputClass}
          />
        </div>
      </div>

      {/* Base Collection Selection */}
      <div>
        <label className="block text-sm font-medium text-foreground mb-2">Base Collection</label>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {baseCollections.map((col) => (
            <button
              key={col.id}
              type="button"
              onClick={() => onChange({ ...value, base_collection_id: col.id })}
              className={`text-left px-4 py-3 rounded-lg border text-sm transition-colors ${
                value.base_collection_id === col.id
                  ? 'border-brand-500 bg-brand-50 text-brand-700'
                  : 'border-border hover:border-input'
              }`}
            >
              <div className="font-medium">{col.name}</div>
              <div className="text-xs text-muted-foreground mt-0.5">{col.artifact_count} artifacts</div>
            </button>
          ))}
        </div>
      </div>

      {/* Additional Collections */}
      <div>
        <label className="block text-sm font-medium text-foreground mb-2">Additional Collections</label>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {additionalCollections.map((col) => (
            <button
              key={col.id}
              type="button"
              onClick={() => toggleAdditional(col.id)}
              className={`text-left px-4 py-3 rounded-lg border text-sm transition-colors ${
                (value.additional_collection_ids ?? []).includes(col.id)
                  ? 'border-purple-500 bg-purple-50 text-purple-700'
                  : 'border-border hover:border-input'
              }`}
            >
              <div className="font-medium">{col.name}</div>
              <div className="text-xs text-muted-foreground mt-0.5">{col.artifact_count} artifacts</div>
            </button>
          ))}
        </div>
      </div>

      {/* Pre-compile name-collision preview — mirrors the compile-time
          name_collision warning (AGENTS.md rule 29/32) so the user can act
          before saving, instead of discovering it on /build/compile. Advisory
          amber, matching TargetExporter.tsx's warning panel; updates live as
          the user disables artifacts or changes the selection. */}
      {collisions.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-amber-800">
              {collisions.length === 1
                ? '1 name collision across these collections'
                : `${collisions.length} name collisions across these collections`}
            </h3>
            <p className="text-xs text-amber-700 mt-1">
              When compiled, later collections override earlier ones by artifact name. Disable the
              losing artifact to keep the winning one.
            </p>
            <ul className="mt-2 space-y-2">
              {collisions.map((collision) => (
                <li key={collision.losingArtifactId} className="text-sm text-amber-700 flex items-start justify-between gap-3">
                  <span>
                    <span className="font-medium">{collision.name}</span> is defined in both{' '}
                    {collectionName(collision.losingCollectionId)} and{' '}
                    {collectionName(collision.winningCollectionId)};{' '}
                    {collectionName(collision.winningCollectionId)} wins.
                  </span>
                  {onDisableArtifact && (
                    <button
                      type="button"
                      onClick={() => onDisableArtifact(collision.losingArtifactId)}
                      className="flex-shrink-0 text-xs font-medium text-amber-800 border border-amber-300 rounded px-2 py-1 hover:bg-amber-100 transition-colors"
                    >
                      Disable in this profile
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-end">
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">
            Preferred Target <span className="text-muted-foreground font-normal">(optional)</span>
          </label>
          <select
            value={value.target_framework ?? ''}
            onChange={(e) => onChange({ ...value, target_framework: e.target.value || undefined })}
            className={inputClass}
          >
            <option value="">No default</option>
            {targets.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onChange({ ...value, is_public: !value.is_public })}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm ${
              value.is_public ? 'border-green-300 bg-green-50 text-green-700' : 'border-border'
            }`}
          >
            {value.is_public ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
            {value.is_public ? 'Public' : 'Private'}
          </button>
        </div>
      </div>
    </div>
  );
}
