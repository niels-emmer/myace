import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { FolderGit2, Plus, GitBranch, Globe, Lock } from 'lucide-react';
import { collectionsApi } from '../lib/api';
import type { Collection, CollectionCreate } from '../types';

export default function CollectionsManager() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<CollectionCreate>({
    name: '',
    git_url: '',
    git_branch: 'main',
    collection_type: 'base',
    visibility: 'private',
  });

  const { data: collections, isLoading } = useQuery({
    queryKey: ['collections'],
    queryFn: () => collectionsApi.list(),
  });

  const createMutation = useMutation({
    mutationFn: (data: CollectionCreate) =>
      collectionsApi.create(data, '00000000-0000-0000-0000-000000000000'), // placeholder owner
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['collections'] });
      setShowForm(false);
      setForm({ name: '', git_url: '', git_branch: 'main', collection_type: 'base', visibility: 'private' });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate(form);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Collections</h1>
          <p className="text-gray-500 mt-1">
            Import and manage Git repositories of canonical configurations
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors text-sm font-medium"
        >
          <Plus className="h-4 w-4" />
          Import Collection
        </button>
      </div>

      {/* Import Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Git URL</label>
              <input
                type="url"
                value={form.git_url}
                onChange={(e) => setForm({ ...form, git_url: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
                placeholder="https://github.com/user/repo.git"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Branch</label>
              <input
                type="text"
                value={form.git_branch}
                onChange={(e) => setForm({ ...form, git_branch: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
              <select
                value={form.collection_type}
                onChange={(e) => setForm({ ...form, collection_type: e.target.value as 'base' | 'additional' })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
              >
                <option value="base">Base Collection</option>
                <option value="additional">Additional Collection</option>
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 text-sm font-medium"
            >
              Import
            </button>
          </div>
        </form>
      )}

      {/* Collection List */}
      {isLoading ? (
        <div className="text-center py-12 text-gray-500">Loading collections...</div>
      ) : collections && collections.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {collections.map((collection) => (
            <CollectionCard key={collection.id} collection={collection} />
          ))}
        </div>
      ) : (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
          <FolderGit2 className="h-12 w-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No collections yet. Import your first one!</p>
        </div>
      )}
    </div>
  );
}

function CollectionCard({ collection }: { collection: Collection }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-sm transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-gray-900">{collection.name}</h3>
          <p className="text-sm text-gray-500 mt-0.5">{collection.description || 'No description'}</p>
        </div>
        <span className={`px-2 py-0.5 rounded text-xs font-medium ${
          collection.collection_type === 'base'
            ? 'bg-blue-50 text-blue-700'
            : 'bg-purple-50 text-purple-700'
        }`}>
          {collection.collection_type}
        </span>
      </div>
      <div className="flex items-center gap-4 text-xs text-gray-500">
        <span className="flex items-center gap-1">
          <GitBranch className="h-3 w-3" />
          {collection.git_branch}
        </span>
        <span className="flex items-center gap-1">
          {collection.visibility === 'public' ? (
            <Globe className="h-3 w-3" />
          ) : (
            <Lock className="h-3 w-3" />
          )}
          {collection.visibility}
        </span>
        <span>{collection.artifact_count} artifacts</span>
      </div>
    </div>
  );
}
