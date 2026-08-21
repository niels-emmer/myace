import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
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

  const { data: communityData } = useQuery({
    queryKey: ['community-collections', 'dashboard'],
    queryFn: () => collectionsApi.listCommunity({ limit: 1 }),
  });

  const { data: categories } = useQuery({
    queryKey: ['community-categories'],
    queryFn: () => collectionsApi.listCommunityCategories(),
  });

  const communityTotal = communityData?.total;
  const categoryList = categories ?? [];

  const stats = [
    {
      label: 'Collections',
      value: collections?.length ?? 0,
      icon: FolderGit2,
      color: 'text-blue-600 bg-blue-50',
      href: '/collections',
      description:
        'Collections are groups of artifacts — rules, skills, agents, and workflows — that serve a role or specific function in agentic coding.',
    },
    {
      label: 'Profiles',
      value: profiles?.length ?? 0,
      icon: SlidersHorizontal,
      color: 'text-purple-600 bg-purple-50',
      href: '/build/profiles',
      description:
        'A Profile is a named recipe — a base collection plus any additional ones, with individual rules, skills, and agents toggled on or off — not a duplicated file tree.',
    },
    {
      label: 'Target Adapters',
      value: adapters?.length ?? 0,
      icon: Download,
      color: 'text-green-600 bg-green-50',
      href: '/build/compile',
      description:
        'Adapters translate your compiled profile into the exact file layout each framework expects — Claude Code, Cursor, OpenCode, and more.',
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
        <p className="text-muted-foreground mt-1 max-w-2xl">
          MyACE lets you write your rules, skills, and agents once, then compile them into whatever
          Claude Code, Cursor, OpenCode, or any other framework actually expects — no more
          hand-maintaining a slightly different copy for every tool.
        </p>
        <p className="text-muted-foreground mt-1 max-w-2xl">
          To start fresh or augment what&rsquo;s already on your machine, browse the{' '}
          {communityTotal !== undefined ? communityTotal : 'many'} community collections
          {categoryList.length > 0
            ? ` across categories like ${categoryList.slice(0, 5).join(', ')}`
            : ''}{' '}
          and import the ones that fit.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {stats.map((stat) => (
          <Link
            key={stat.label}
            to={stat.href}
            className="bg-card rounded-xl border border-border p-6 hover:shadow-sm hover:border-input transition-shadow"
          >
            <div className="flex items-center gap-4">
              <div className={`p-3 rounded-lg ${stat.color}`}>
                <stat.icon className="h-6 w-6" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">{stat.label}</p>
                <p className="text-2xl font-bold text-card-foreground">{stat.value}</p>
              </div>
            </div>
            <p className="text-sm text-muted-foreground mt-3">{stat.description}</p>
          </Link>
        ))}
      </div>

      {/* Quick Start */}
      <div className="bg-card rounded-xl border border-border p-6">
        <div className="flex items-center gap-2 mb-4">
          <Sparkles className="h-5 w-5 text-brand-600" />
          <h2 className="text-lg font-semibold text-card-foreground">Quick Start</h2>
        </div>
        <div className="space-y-1">
          <Step
            number={1}
            href="/machine/import"
            text="Browse the starter Collections, or import your own from GitHub or your local machine"
          />
          <Step
            number={2}
            href="/build/profiles"
            text="Create a Profile combining a base + additional collections"
          />
          <Step
            number={3}
            href="/build/compile"
            text="Compile the profile into your target framework's files"
          />
          <Step
            number={4}
            href="/build/compile"
            text="Download as an archive, or sync with the CLI: myace pull --profile <name> --target <framework>"
          />
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

function Step({ number, text, href }: { number: number; text: string; href: string }) {
  return (
    <Link
      to={href}
      className="flex items-center gap-3 rounded-lg px-2 py-1.5 -mx-2 transition-colors hover:bg-accent group"
    >
      <span className="flex items-center justify-center h-7 w-7 rounded-full bg-brand-100 text-brand-700 text-sm font-bold flex-shrink-0">
        {number}
      </span>
      <p className="text-sm text-muted-foreground group-hover:text-foreground">{text}</p>
      <ArrowRight className="h-4 w-4 text-muted-foreground ml-auto flex-shrink-0 group-hover:text-foreground" />
    </Link>
  );
}
