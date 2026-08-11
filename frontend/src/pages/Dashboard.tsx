import { useQuery } from '@tanstack/react-query';
import {
  FolderGit2,
  SlidersHorizontal,
  Download,
  ArrowRight,
  Sparkles,
} from 'lucide-react';
import { collectionsApi, profilesApi, adaptersApi } from '../lib/api';

export default function Dashboard() {
  const { data: collections } = useQuery({
    queryKey: ['collections'],
    queryFn: () => collectionsApi.list(),
  });

  const { data: profiles } = useQuery({
    queryKey: ['profiles'],
    queryFn: () => profilesApi.list(),
  });

  const { data: adapters } = useQuery({
    queryKey: ['adapters'],
    queryFn: () => adaptersApi.list(),
  });

  const stats = [
    {
      label: 'Collections',
      value: collections?.length ?? 0,
      icon: FolderGit2,
      color: 'text-blue-600 bg-blue-50',
    },
    {
      label: 'Profiles',
      value: profiles?.length ?? 0,
      icon: SlidersHorizontal,
      color: 'text-purple-600 bg-purple-50',
    },
    {
      label: 'Target Adapters',
      value: adapters?.length ?? 0,
      icon: Download,
      color: 'text-green-600 bg-green-50',
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
        <p className="text-muted-foreground mt-1">
          Manage your agentic coding environment configurations
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className="bg-card rounded-xl border border-border p-6 flex items-center gap-4"
          >
            <div className={`p-3 rounded-lg ${stat.color}`}>
              <stat.icon className="h-6 w-6" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">{stat.label}</p>
              <p className="text-2xl font-bold text-card-foreground">{stat.value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Quick Start */}
      <div className="bg-card rounded-xl border border-border p-6">
        <div className="flex items-center gap-2 mb-4">
          <Sparkles className="h-5 w-5 text-brand-600" />
          <h2 className="text-lg font-semibold text-card-foreground">Quick Start</h2>
        </div>
        <div className="space-y-3">
          <Step number={1} text="Browse the starter Collections, or import your own from GitHub or your local machine" />
          <Step number={2} text="Create a Profile combining a base + additional collections" />
          <Step number={3} text="Compile the profile into your target framework's files" />
          <Step number={4} text="Sync with the CLI: myace pull --profile <name> --target <framework>" />
        </div>
      </div>

      {/* Adapters */}
      {adapters && adapters.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-foreground mb-4">Available Adapters</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {adapters.map((adapter) => (
              <div
                key={adapter.name}
                className="bg-card rounded-xl border border-border p-4 hover:shadow-sm transition-shadow"
              >
                <h3 className="font-medium text-card-foreground">{adapter.name}</h3>
                <p className="text-sm text-muted-foreground mt-1">{adapter.description}</p>
                <div className="flex flex-wrap gap-1.5 mt-3">
                  {adapter.targets.map((target) => (
                    <span
                      key={target}
                      className="px-2 py-0.5 bg-muted text-muted-foreground rounded text-xs font-medium"
                    >
                      {target}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Step({ number, text }: { number: number; text: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="flex items-center justify-center h-7 w-7 rounded-full bg-brand-100 text-brand-700 text-sm font-bold">
        {number}
      </span>
      <p className="text-sm text-muted-foreground">{text}</p>
      {number < 4 && <ArrowRight className="h-4 w-4 text-muted-foreground ml-auto" />}
    </div>
  );
}
