import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft } from 'lucide-react';
import { collectionsApi } from '../lib/api';
import TargetChecklist from '../components/TargetChecklist';
import { PRIORITY_MIN, PRIORITY_MAX, validatePriority, validateVersion } from '../lib/artifactValidation';

const inputClass =
  'w-full px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500';

export default function NewArtifactRule() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [version, setVersion] = useState('1.0.0');
  const [priority, setPriority] = useState('50');
  const [targets, setTargets] = useState<string[]>([]);
  const [tagsInput, setTagsInput] = useState('');
  const [body, setBody] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: () =>
      collectionsApi.createArtifact(id!, {
        artifact_type: 'rule',
        name: name.trim(),
        description: description.trim() || undefined,
        version: version.trim(),
        priority: Number(priority),
        target_compatibility: targets,
        tags: tagsInput
          .split(',')
          .map((t) => t.trim())
          .filter(Boolean),
        body,
        file_path: 'AGENTS.md',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['artifacts', id] });
      queryClient.invalidateQueries({ queryKey: ['collection', id] });
      navigate(`/collections/${id}`);
    },
  });

  const validate = (): string | null => {
    if (!name.trim()) return 'Name is required.';
    const priorityResult = validatePriority(priority);
    if ('error' in priorityResult) return priorityResult.error;
    const versionResult = validateVersion(version);
    if ('error' in versionResult) return versionResult.error;
    if (!body.trim()) return 'Body is required.';
    return null;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const error = validate();
    if (error) {
      setValidationError(error);
      return;
    }
    setValidationError(null);
    createMutation.mutate();
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center gap-4">
        <Link
          to={`/collections/${id}`}
          className="p-2 -ml-2 text-muted-foreground hover:text-accent-foreground hover:bg-accent rounded-lg transition-colors"
          title="Back to collection"
        >
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-foreground">Add rule</h1>
          <p className="text-muted-foreground mt-1">
            Add a new rule directly to this collection.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="bg-card rounded-xl border border-border p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-foreground mb-1">
            Name <span className="text-destructive">*</span>
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className={inputClass}
            autoFocus
            placeholder="e.g. No trailing whitespace"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground mb-1">
            Description <span className="text-muted-foreground font-normal">(optional)</span>
          </label>
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className={inputClass}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Version</label>
            <input
              type="text"
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              className={inputClass}
              placeholder="1.0.0"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Priority</label>
            <input
              type="number"
              min={PRIORITY_MIN}
              max={PRIORITY_MAX}
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className={inputClass}
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground mb-1">
            Tags <span className="text-muted-foreground font-normal">(comma-separated, optional)</span>
          </label>
          <input
            type="text"
            value={tagsInput}
            onChange={(e) => setTagsInput(e.target.value)}
            className={inputClass}
            placeholder="e.g. python, testing"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground mb-1">
            Target frameworks{' '}
            <span className="text-muted-foreground font-normal">
              (optional — none means compatible with all)
            </span>
          </label>
          <div className="border border-border rounded-lg p-2">
            <TargetChecklist selected={targets} onChange={setTargets} />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-foreground mb-1">
            Body <span className="text-destructive">*</span>
          </label>
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={12}
            className={`${inputClass} font-mono text-xs`}
            placeholder="Markdown content for this rule..."
          />
        </div>

        {(validationError || createMutation.isError) && (
          <p className="text-sm text-destructive">
            {validationError ||
              (createMutation.error instanceof Error
                ? createMutation.error.message
                : 'Failed to create rule.')}
          </p>
        )}

        <div className="flex justify-end gap-3 pt-2">
          <Link
            to={`/collections/${id}`}
            className="px-4 py-2 text-sm text-muted-foreground hover:text-accent-foreground"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 text-sm font-medium transition-colors"
          >
            {createMutation.isPending ? 'Saving...' : 'Add rule'}
          </button>
        </div>
      </form>
    </div>
  );
}
