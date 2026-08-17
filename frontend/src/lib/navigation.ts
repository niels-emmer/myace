import {
  FolderGit2,
  Globe,
  SlidersHorizontal,
  Workflow,
  Download,
  Upload,
  Search,
  RefreshCw,
  Settings,
  ShieldCheck,
  Shield,
  type LucideIcon,
} from 'lucide-react';
import type { User } from '../types';

export interface NavChild {
  to: string;
  label: string;
  icon: LucideIcon;
  description: string;
}

export interface NavGroup {
  id: string;
  label: string;
  icon: LucideIcon;
  summary: string;
  hubPath?: string;
  children: NavChild[];
}

export const collectionsGroup: NavGroup = {
  id: 'collections',
  label: 'Collections',
  icon: FolderGit2,
  summary: 'Curate the rules, skills, and agents that make up your library.',
  hubPath: '/collections',
  children: [
    {
      to: '/collections/mine',
      label: 'My Collections',
      icon: FolderGit2,
      description: 'Create, edit, and organize the rules, skills, and agents you own.',
    },
    {
      to: '/collections/community',
      label: 'Community',
      icon: Globe,
      description: 'Browse and import collections published by other users.',
    },
  ],
};

export const buildGroup: NavGroup = {
  id: 'build',
  label: 'Build',
  icon: SlidersHorizontal,
  summary: "Turn your collections into a working profile for your coding agent.",
  hubPath: '/build',
  children: [
    {
      to: '/build/profiles',
      label: 'Profiles',
      icon: SlidersHorizontal,
      description: 'Combine a base + additional collections into a profile.',
    },
    {
      to: '/build/orchestration',
      label: 'Orchestration',
      icon: Workflow,
      description: 'Browse and build multi-agent pipelines with handoffs between agents.',
    },
    {
      to: '/build/compile',
      label: 'Compile & Export',
      icon: Download,
      description: 'Turn a profile into files for your target framework.',
    },
  ],
};

export const machineGroup: NavGroup = {
  id: 'machine',
  label: 'My Machine',
  icon: Upload,
  summary: 'Manage the connection between MyACE and your local tool configs.',
  hubPath: '/machine',
  children: [
    {
      to: '/machine/import',
      label: 'Import',
      icon: Upload,
      description: 'Scan your local machine or a GitHub repo to bring in existing configs.',
    },
    {
      to: '/machine/audit',
      label: 'Setup Audit',
      icon: Search,
      description: "Check your local machine's tool configs against what MyACE expects.",
    },
    {
      to: '/machine/sync',
      label: 'Sync',
      icon: RefreshCw,
      description: 'See which pulled targets have drifted from their compiled profile.',
    },
  ],
};

export function getAccountGroup(user: User | null): NavGroup {
  const children: NavChild[] = [
    {
      to: '/settings',
      label: 'Settings',
      icon: Settings,
      description: 'Manage your account, API tokens, and CLI setup.',
    },
  ];

  if (user?.role === 'moderator' || user?.role === 'admin') {
    children.push({
      to: '/moderation',
      label: 'Moderation',
      icon: ShieldCheck,
      description: 'Review, approve, or deny community collection submissions.',
    });
  }

  if (user?.is_admin) {
    children.push({
      to: '/admin/system',
      label: 'System',
      icon: Shield,
      description: 'Configure system-wide settings and adapters.',
    });
  }

  return {
    id: 'account',
    label: 'Account',
    icon: Settings,
    summary: 'Your account, tokens, and admin tools.',
    children,
  };
}
