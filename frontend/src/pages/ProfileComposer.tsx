import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { SlidersHorizontal, Plus, Save, Eye, EyeOff } from 'lucide-react';
import { collectionsApi, profilesApi } from '../lib/api';
import type { Profile, ProfileCreate } from '../types';

export default function ProfileComposer() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<ProfileCreate>({
    name: '',
    description: '',
    base_collection_id: '',
    additional_collection_ids: [],
    disabled_artifact_ids: [],
    is_public: false,
  });

  const { data: profiles } = useQuery({
    queryKey: ['profiles'],
    queryFn: () => profilesApi.list(),
  });

  const { data: collections } = useQuery({
    queryKey: ['collections'],
    queryFn: () => collectionsApi.list(),
  });

  const baseCollections = collections?.filter((c) => c.collection_type === 'base') ?? [];
  const additionalCollections = collections?.filter((c) => c.collection_type === 'additional') ?? [];

  const createMutation = useMutation({
    mutationFn: (data: ProfileCreate) =>
      profilesApi.create(data, '00000000-0000-0000-0000-000000000000'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profiles'] });
      setShowForm(false);
      setForm({
        name: '',
        description: '',
        base_collection_id: '',
        additional_collection_ids: [],
        disabled_artifact_ids: [],
        is_public: false,
      });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate(form);
  };

  const toggleAdditional = (id: string) => {
    setForm((prev) => ({
      ...prev,
      additional_collection_ids: prev.additional_collection_ids!.includes(id)
        ? prev.additional_collection_ids!.filter((cid) => cid !== id)
        : [...prev.additional_collection_ids!, id],
    }));
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Profile Composer</h1>
          <p className="text-gray-500 mt-1">
            Mix base collections with additional collections to create custom profiles
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors text-sm font-medium"
        >
          <Plus className="h-4 w-4" />
          New Profile
        </button>
      </div>

      {/* Create Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Profile Name</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <input
                type="text"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              />
            </div>
          </div>

          {/* Base Collection Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Base Collection</label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {baseCollections.map((col) => (
                <button
                  key={col.id}
                  type="button"
                  onClick={() => setForm({ ...form, base_collection_id: col.id })}
                  className={`text-left px-4 py-3 rounded-lg border text-sm transition-colors ${
                    form.base_collection_id === col.id
                      ? 'border-brand-500 bg-brand-50 text-brand-700'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="font-medium">{col.name}</div>
                  <div className="text-xs text-gray-500 mt-0.5">{col.artifact_count} artifacts</div>
                </button>
              ))}
            </div>
          </div>

          {/* Additional Collections */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Additional Collections</label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {additionalCollections.map((col) => (
                <button
                  key={col.id}
                  type="button"
                  onClick={() => toggleAdditional(col.id)}
                  className={`text-left px-4 py-3 rounded-lg border text-sm transition-colors ${
                    form.additional_collection_ids!.includes(col.id)
                      ? 'border-purple-500 bg-purple-50 text-purple-700'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="font-medium">{col.name}</div>
                  <div className="text-xs text-gray-500 mt-0.5">{col.artifact_count} artifacts</div>
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setForm({ ...form, is_public: !form.is_public })}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm ${
                form.is_public ? 'border-green-300 bg-green-50 text-green-700' : 'border-gray-200'
              }`}
            >
              {form.is_public ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
              {form.is_public ? 'Public' : 'Private'}
            </button>
          </div>

          <div className="flex justify-end gap-3">
            <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 text-sm text-gray-600">
              Cancel
            </button>
            <button
              type="submit"
              className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 text-sm font-medium"
            >
              <Save className="h-4 w-4" />
              Save Profile
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
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
          <SlidersHorizontal className="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No profiles yet. Create your first composition!</p>
        </div>
      )}
    </div>
  );
}

function ProfileCard({ profile }: { profile: Profile }) {
  const [compiling, setCompiling] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const handleCompile = async () => {
    setCompiling(true);
    try {
      const res = await profilesApi.compile({
        profile_id: profile.id,
        target: 'opencode',
      });
      setResult(`Compiled ${res.artifact_count} artifacts into ${Object.keys(res.files).length} files`);
    } catch (err) {
      setResult('Compilation failed');
    }
    setCompiling(false);
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-sm transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-gray-900">{profile.name}</h3>
          <p className="text-sm text-gray-500 mt-0.5">{profile.description || 'No description'}</p>
        </div>
        <span className="text-xs text-gray-400">v{profile.version}</span>
      </div>
      <div className="flex items-center gap-4 text-xs text-gray-500 mb-3">
        <span>{profile.additional_collection_ids.length + 1} collections</span>
        <span>{profile.is_public ? 'Public' : 'Private'}</span>
      </div>
      <button
        onClick={handleCompile}
        disabled={compiling}
        className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-100 transition-colors disabled:opacity-50"
      >
        {compiling ? 'Compiling...' : 'Compile & Preview'}
      </button>
      {result && (
        <p className="text-xs text-gray-500 mt-2">{result}</p>
      )}
    </div>
  );
}
