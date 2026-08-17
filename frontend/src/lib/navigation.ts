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
  UserCircle,
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
  /** One or more paragraphs introducing the group, rendered on its hub page. */
  description: string[];
  hubPath?: string;
  children: NavChild[];
}

export const collectionsGroup: NavGroup = {
  id: 'collections',
  label: 'Collections',
  icon: FolderGit2,
  description: [
    'Collections are groups of artifacts — rules, skills, agents, and workflows — that serve a role or specific function in agentic coding. Curate your own, or bring in ready-made ones from a GitHub repository, your local machine, or the community.',
    'Base collections set the foundation for your coding profile; additional collections layer in specific roles and skills on top. Combine them into a Profile, then compile that profile to any supported framework.',
  ],
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
  description: [
    "A Profile is a named recipe — a base collection plus any additional ones, with individual rules, skills, and agents toggled on or off — not a duplicated file tree. Build one once, then compile it to as many target frameworks as you need.",
    "Agents can also declare who they hand work off to. Browse existing multi-agent pipelines in the Orchestration Gallery, or compose your own from a profile's agents without writing frontmatter by hand.",
  ],
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
  description: [
    "MyACE only does anything useful once it's connected to the tools actually running on your machine. Import scans a local config directory or a GitHub repo and turns what it finds into a portable Collection; Setup Audit checks your machine's existing configs against what MyACE expects and reports gaps.",
    "Once you've pulled a compiled profile down with the CLI, Sync keeps you honest — it flags whenever a local file has been hand-edited or has drifted out of date against the server, so nothing silently goes stale.",
  ],
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

export function getSettingsGroup(user: User | null): NavGroup {
  const children: NavChild[] = [
    {
      to: '/settings/account',
      label: 'Account',
      icon: UserCircle,
      description: 'Manage your account, API tokens, and CLI setup.',
    },
  ];

  if (user?.role === 'moderator' || user?.role === 'admin') {
    children.push({
      to: '/settings/moderation',
      label: 'Moderation',
      icon: ShieldCheck,
      description: 'Review, approve, or deny community collection submissions.',
    });
  }

  if (user?.is_admin) {
    children.push({
      to: '/settings/system',
      label: 'System',
      icon: Shield,
      description: 'Configure system-wide settings and adapters.',
    });
  }

  return {
    id: 'settings',
    label: 'Settings',
    icon: Settings,
    description: [
      'Manage your own account — profile details, notification preferences, and the API tokens the CLI uses to authenticate.',
      ...(user?.role === 'moderator' || user?.role === 'admin'
        ? [
            "If you hold a moderator or admin role, this is also where you review community submissions and, for admins, configure system-wide behavior like SMTP, OAuth providers, and adapter availability.",
          ]
        : []),
    ],
    hubPath: '/settings',
    children,
  };
}
