import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Download, Copy, Terminal, Check } from 'lucide-react';
import { profilesApi, adaptersApi } from '../lib/api';
import type { CompileResult } from '../types';

export default function TargetExporter() {
  const [selectedProfile, setSelectedProfile] = useState('');
  const [selectedTarget, setSelectedTarget] = useState('opencode');
  const [result, setResult] = useState<CompileResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);

  const { data: profiles } = useQuery({
    queryKey: ['profiles'],
    queryFn: () => profilesApi.list(),
  });

  const { data: adapters } = useQuery({
    queryKey: ['adapters'],
    queryFn: () => adaptersApi.list(),
  });

  const handleCompile = async () => {
    if (!selectedProfile) return;
    setLoading(true);
    try {
      const res = await profilesApi.compile({
        profile_id: selectedProfile,
        target: selectedTarget,
      });
      setResult(res);
    } catch (err) {
      console.error('Compilation failed:', err);
    }
    setLoading(false);
  };

  const copyToClipboard = async (text: string, key: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(null), 2000);
  };

  const cliCommand = result
    ? `myace pull --profile ${result.profile_name} --target ${result.target}`
    : '';

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Compile Profile</h1>
        <p className="text-muted-foreground mt-1">
          Turn a profile into the config files a target framework expects (CLAUDE.md, AGENTS.md, etc.) — copy them out or pull with the CLI.
        </p>
      </div>

      {/* Controls */}
      <div className="bg-card rounded-xl border border-border p-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Profile</label>
            <select
              value={selectedProfile}
              onChange={(e) => setSelectedProfile(e.target.value)}
              className="w-full px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm"
            >
              <option value="">Select a profile...</option>
              {profiles?.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Target Framework</label>
            <select
              value={selectedTarget}
              onChange={(e) => setSelectedTarget(e.target.value)}
              className="w-full px-3 py-2 bg-background text-foreground border border-input rounded-lg text-sm"
            >
              {adapters?.map((a) =>
                a.targets.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))
              )}
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={handleCompile}
              disabled={!selectedProfile || loading}
              className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg hover:bg-brand-700 disabled:opacity-50 text-sm font-medium"
            >
              <Download className="h-4 w-4" />
              {loading ? 'Compiling...' : 'Compile'}
            </button>
          </div>
        </div>

        {/* CLI Command */}
        {cliCommand && (
          <div className="bg-muted rounded-lg p-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Terminal className="h-4 w-4 text-muted-foreground" />
              <code className="text-sm text-foreground">{cliCommand}</code>
            </div>
            <button
              onClick={() => copyToClipboard(cliCommand, 'cli')}
              className="p-1.5 hover:bg-accent rounded transition-colors"
            >
              {copied === 'cli' ? (
                <Check className="h-4 w-4 text-green-600" />
              ) : (
                <Copy className="h-4 w-4 text-muted-foreground" />
              )}
            </button>
          </div>
        )}
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-foreground">
              Output — {result.artifact_count} artifacts, {Object.keys(result.files).length} files
            </h2>
          </div>

          {Object.entries(result.files).map(([filename, content]) => (
            <div key={filename} className="bg-card rounded-xl border border-border overflow-hidden">
              <div className="flex items-center justify-between px-4 py-2 bg-muted border-b border-border">
                <span className="text-sm font-mono text-foreground">{filename}</span>
                <button
                  onClick={() => copyToClipboard(content, filename)}
                  className="p-1.5 hover:bg-accent rounded transition-colors"
                >
                  {copied === filename ? (
                    <Check className="h-4 w-4 text-green-600" />
                  ) : (
                    <Copy className="h-4 w-4 text-muted-foreground" />
                  )}
                </button>
              </div>
              <pre className="p-4 text-xs text-muted-foreground overflow-x-auto max-h-64 overflow-y-auto">
                {content}
              </pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
