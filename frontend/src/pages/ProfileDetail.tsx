import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  Copy,
  Download,
  Pencil,
  Check,
  X,
  Trash2,
  AlertTriangle,
  Globe,
  Lock,
  FolderGit2,
} from 'lucide-react';
import { adaptersApi, collectionsApi, profilesApi } from '../lib/api';
import ProfileFormFields from '../components/ProfileForm';
import type { ProfileCreate } from '../types';

export default function ProfileDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState<ProfileCreate | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const { data: profile, isLoading: loadingProfile } = useQuery({
    queryKey: ['profile', id],
    queryFn: () => profilesApi.get(id!),
    enabled: !!id,
  });

  const { data: collections } = useQuery({
    queryKey: ['collections'],
    queryFn: () => collectionsApi.list(),
  });

  const { data: adapters } = useQuery({
    queryKey: ['adapters'],
    queryFn: () => adaptersApi.list(),
  });

  const targets = Array.from(new Set((adapters ?? []).flatMap((a) => a.targets)));
  const baseCollections = collections?.filter((c) => c.collection_type === 'base') ?? [];
  const additionalCollections = collections?.filter((c) => c.collection_type === 'additional') ?? [];
  const collectionName = (cid: string) => collections?.find((c) => c.id === cid)?.name ?? cid;

  const updateMutation = useMutation({
    mutationFn: (data: ProfileCreate) => profilesApi.update(id!, data),
    onSuccess: (updated) => {
      queryClient.setQueryData(['profile', id], updated);
      queryClient.invalidateQueries({ queryKey: ['profiles'] });
      setIsEditing(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => profilesApi.delete(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profiles'] });
      navigate('/profiles');
    },
  });

  if (loadingProfile) {
    return <div className="text-center py-12 text-muted-foreground">Loading profile...</div>;
  }

  if (!profile) {
    return <div className="text-center py-12 text-muted-foreground">Profile not found.</div>;
  }

  const startEdit = () => {
    updateMutation.reset();
    setEditForm({
      name: profile.name,
      description: profile.description ?? '',
      base_collection_id: profile.base_collection_id,
      additional_collection_ids: [...profile.additional_collection_ids],
      disabled_artifact_ids: [...profile.disabled_artifact_ids],
      target_framework: profile.target_framework,
      is_public: profile.is_public,
    });
    setIsEditing(true);
  };

  const handleClone = () => {
    navigate('/profiles', { state: { cloneFrom: profile } });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <button
          onClick={() => navigate('/profiles')}
          className="p-2 -ml-2 text-muted-foreground hover:text-accent-foreground hover:bg-accent rounded-lg transition-colors"
          title="Back to profiles"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>

        <div className="flex-1 min-w-0">
          {isEditing && editForm ? (
            <div className="max-w-2xl">
              <ProfileFormFields
                value={editForm}
                onChange={setEditForm}
                baseCollections={baseCollections}
                additionalCollections={additionalCollections}
                targets={targets}
              />
            </div>
          ) : (
            <>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-foreground truncate">{profile.name}</h1>
                <span
                  className={`px-2 py-0.5 rounded text-xs font-medium flex-shrink-0 ${
                    profile.is_public ? 'bg-green-50 text-green-700' : 'bg-muted text-muted-foreground'
                  }`}
                >
                  {profile.is_public ? 'Public' : 'Private'}
                </span>
                <span className="text-xs text-muted-foreground flex-shrink-0">v{profile.version}</span>
              </div>
              <p className="text-muted-foreground mt-1">{profile.description || 'No description'}</p>
              <div className="flex items-center gap-4 text-xs text-muted-foreground mt-2">
                <span className="flex items-center gap-1">
                  {profile.is_public ? <Globe className="h-3 w-3" /> : <Lock className="h-3 w-3" />}
                  {profile.is_public ? 'public' : 'private'}
                </span>
                {profile.target_framework && <span>Preferred target: {profile.target_framework}</span>}
              </div>
            </>
          )}
        </div>

        {/* Header actions */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {isEditing ? (
            <>
              <button
                onClick={() => setIsEditing(false)}
                className="flex items-center gap-1.5 px-3 py-2 text-sm text-muted-foreground hover:text-accent-foreground transition-colors"
              >
                <X className="h-4 w-4" />
                Cancel
              </button>
              <button
                onClick={() => editForm && updateMutation.mutate(editForm)}
                disabled={!editForm?.name.trim() || !editForm?.base_collection_id || updateMutation.isPending}
                className="flex items-center gap-1.5 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 transition-colors text-sm font-medium"
              >
                <Check className="h-4 w-4" />
                {updateMutation.isPending ? 'Saving...' : 'Save'}
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => navigate(`/compile?profile=${profile.id}`)}
                className="flex items-center gap-1.5 px-4 py-2 bg-muted border border-border rounded-lg text-sm text-foreground hover:bg-accent transition-colors"
              >
                <Download className="h-3.5 w-3.5" />
                Compile & Preview
              </button>
              <button
                onClick={handleClone}
                className="flex items-center gap-1.5 px-4 py-2 bg-muted border border-border rounded-lg text-sm text-foreground hover:bg-accent transition-colors"
              >
                <Copy className="h-3.5 w-3.5" />
                Clone
              </button>
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="flex items-center gap-1.5 px-4 py-2 bg-muted border border-border rounded-lg text-sm text-destructive hover:bg-destructive/10 transition-colors"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Delete
              </button>
              <button
                onClick={startEdit}
                className="flex items-center gap-1.5 px-4 py-2 bg-muted border border-border rounded-lg text-sm text-foreground hover:bg-accent transition-colors"
              >
                <Pencil className="h-3.5 w-3.5" />
                Edit
              </button>
            </>
          )}
        </div>
      </div>

      {updateMutation.isError && (
        <div className="p-3 bg-destructive/10 border border-destructive/30 rounded-lg text-sm text-destructive">
          {(updateMutation.error as Error).message}
        </div>
      )}

      {/* Collections summary */}
      {!isEditing && (
        <div className="bg-card rounded-xl border border-border p-6 space-y-4">
          <div>
            <h2 className="text-sm font-medium text-muted-foreground mb-2">Base Collection</h2>
            <div className="flex items-center gap-2 px-4 py-3 rounded-lg border border-brand-500 bg-brand-50 text-brand-700 text-sm w-fit">
              <FolderGit2 className="h-4 w-4" />
              {collectionName(profile.base_collection_id)}
            </div>
          </div>

          <div>
            <h2 className="text-sm font-medium text-muted-foreground mb-2">Additional Collections</h2>
            {profile.additional_collection_ids.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {profile.additional_collection_ids.map((cid) => (
                  <div
                    key={cid}
                    className="flex items-center gap-2 px-4 py-3 rounded-lg border border-purple-500 bg-purple-50 text-purple-700 text-sm"
                  >
                    <FolderGit2 className="h-4 w-4" />
                    {collectionName(cid)}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">None</p>
            )}
          </div>

          {profile.disabled_artifact_ids.length > 0 && (
            <p className="text-xs text-muted-foreground">
              {profile.disabled_artifact_ids.length} individually-disabled artifact
              {profile.disabled_artifact_ids.length === 1 ? '' : 's'} carried over from collection edits.
            </p>
          )}
        </div>
      )}

      {/* Delete Confirmation */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-card border border-border rounded-xl p-6 w-full max-w-sm space-y-4">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-destructive/10 rounded-lg flex-shrink-0">
                <AlertTriangle className="h-5 w-5 text-destructive" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-card-foreground">
                  Delete &ldquo;{profile.name}&rdquo;?
                </h2>
                <p className="text-sm text-muted-foreground mt-1">
                  This action cannot be undone.
                </p>
              </div>
            </div>

            {deleteMutation.isError && (
              <p className="text-sm text-destructive">{(deleteMutation.error as Error).message}</p>
            )}

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-4 py-2 text-sm text-muted-foreground hover:text-accent-foreground"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteMutation.mutate()}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 bg-destructive text-white rounded-lg hover:bg-destructive/90 disabled:opacity-50 text-sm font-medium transition-colors"
              >
                {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
