import { Eye, EyeOff } from 'lucide-react';
import type { Collection, ProfileCreate } from '../types';

const inputClass =
  'w-full px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500';

interface ProfileFormFieldsProps {
  value: ProfileCreate;
  onChange: (value: ProfileCreate) => void;
  baseCollections: Collection[];
  additionalCollections: Collection[];
  targets: string[];
}

export default function ProfileFormFields({
  value,
  onChange,
  baseCollections,
  additionalCollections,
  targets,
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
