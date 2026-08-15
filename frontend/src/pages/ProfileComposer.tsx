import { useEffect, useRef, useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, SlidersHorizontal, Save, Download } from 'lucide-react';
import { adaptersApi, collectionsApi, profilesApi } from '../lib/api';
import ProfileFormFields from '../components/ProfileForm';
import type { Profile, ProfileCreate } from '../types';

const emptyForm: ProfileCreate = {
  name: '',
  description: '',
  base_collection_id: '',
  additional_collection_ids: [],
  disabled_artifact_ids: [],
  target_framework: undefined,
  is_public: false,
};

export default function ProfileComposer() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<ProfileCreate>(emptyForm);
  const consumedCloneState = useRef(false);

  const { data: profiles } = useQuery({
    queryKey: ['profiles'],
    queryFn: () => profilesApi.list(),
  });

  const { data: collections } = useQuery({
    queryKey: ['collections'],
    queryFn: () => collectionsApi.list(),
  });

  const { data: adapters } = useQuery({
    queryKey: ['adapters'],
    queryFn: () => adaptersApi.list(),
  });

  const targets = (adapters ?? []).map((a) => a.name);

  const baseCollections = collections?.filter((c) => c.collection_type === 'base') ?? [];
  const additionalCollections = collections?.filter((c) => c.collection_type === 'additional') ?? [];

  // A profile detail page can send us here to clone it — prefill and open the form.
  useEffect(() => {
    const cloneFrom = (location.state as { cloneFrom?: Profile } | null)?.cloneFrom;
    if (cloneFrom && !consumedCloneState.current) {
      consumedCloneState.current = true;
      setForm({
        name: `${cloneFrom.name} [copy]`,
        description: cloneFrom.description ?? '',
        base_collection_id: cloneFrom.base_collection_id,
        additional_collection_ids: [...cloneFrom.additional_collection_ids],
        disabled_artifact_ids: [...cloneFrom.disabled_artifact_ids],
        target_framework: cloneFrom.target_framework,
        is_public: false,
      });
      setShowForm(true);
      navigate(location.pathname, { replace: true, state: null });
    }
  }, [location, navigate]);

  const createMutation = useMutation({
    mutationFn: (data: ProfileCreate) => profilesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profiles'] });
      setShowForm(false);
      setForm(emptyForm);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate(form);
  };

  const openNewProfileForm = () => {
    createMutation.reset();
    setForm(emptyForm);
    setShowForm(true);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Profile Composer</h1>
        <p className="text-muted-foreground mt-1">
          A profile is a named recipe: one base collection plus optional additional
          collections, layered by priority. View and edit your profiles here, or{' '}
          <button
            onClick={openNewProfileForm}
            className="text-brand-600 hover:underline font-medium"
          >
            add a new profile
          </button>{' '}
          to your exact liking. Then,{' '}
          <Link to="/compile" className="text-brand-600 hover:underline font-medium">
            compile your profile
          </Link>{' '}
          to produce the actual files for a target framework.
        </p>
      </div>

      <div className="flex justify-end">
        <button
          onClick={openNewProfileForm}
          className="flex items-center gap-1.5 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 text-sm font-medium transition-colors"
        >
          <Plus className="h-4 w-4" />
          Add profile
        </button>
      </div>

      {/* Create Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="bg-card rounded-xl border border-border p-6 space-y-6">
          <ProfileFormFields
            value={form}
            onChange={setForm}
            baseCollections={baseCollections}
            additionalCollections={additionalCollections}
            targets={targets}
          />

          {createMutation.isError && (
            <div className="p-3 bg-destructive/10 border border-destructive/30 rounded-lg text-sm text-destructive">
              {(createMutation.error as Error).message}
            </div>
          )}

          <div className="flex justify-end gap-3">
            <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 text-sm text-muted-foreground">
              Cancel
            </button>
            <button
              type="submit"
              disabled={!form.base_collection_id || createMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 text-sm font-medium"
            >
              <Save className="h-4 w-4" />
              {createMutation.isPending ? 'Saving...' : 'Save Profile'}
            </button>
          </div>
        </form>
      )}

      {/* Profile List */}
      {profiles && profiles.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {profiles.map((profile) => (
            <ProfileCard key={profile.id} profile={profile} />
          ))}
        </div>
      ) : (
        <div className="text-center py-12 bg-card rounded-xl border border-border">
          <SlidersHorizontal className="h-12 w-12 text-muted-foreground mx-auto mb-3" />
          <p className="text-muted-foreground">
            No profiles yet.{' '}
            <button
              onClick={openNewProfileForm}
              className="text-brand-600 hover:underline font-medium"
            >
              Create your first composition!
            </button>
          </p>
        </div>
      )}
    </div>
  );
}

function ProfileCard({ profile }: { profile: Profile }) {
  const navigate = useNavigate();

  return (
    <div
      onClick={() => navigate(`/profiles/${profile.id}`)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') navigate(`/profiles/${profile.id}`);
      }}
      className="text-left bg-card rounded-xl border border-border p-5 hover:shadow-sm hover:border-input transition-shadow cursor-pointer"
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-card-foreground">{profile.name}</h3>
          <p className="text-sm text-muted-foreground mt-0.5">{profile.description || 'No description'}</p>
        </div>
        <span className="text-xs text-muted-foreground">v{profile.version}</span>
      </div>
      <div className="flex items-center gap-4 text-xs text-muted-foreground mb-3">
        <span>{profile.additional_collection_ids.length + 1} collections</span>
        <span>{profile.is_public ? 'Public' : 'Private'}</span>
      </div>
      <button
        onClick={(e) => {
          e.stopPropagation();
          navigate(`/compile?profile=${profile.id}`);
        }}
        className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-muted border border-border rounded-lg text-sm text-muted-foreground hover:bg-accent transition-colors"
      >
        <Download className="h-4 w-4" />
        Compile & Preview
      </button>
    </div>
  );
}
