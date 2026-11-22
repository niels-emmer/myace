import {
  Compass,
  FolderGit2,
  Home,
  Laptop,
  Settings,
  Shield,
  ShieldCheck,
  SlidersHorizontal,
  UserCircle,
  Workflow,
  type LucideIcon,
} from 'lucide-react';
import type { User } from '../types';

export interface NavChild {
  to: string;
  label: string;
  icon: LucideIcon;
  description: string;
  /** Match exactly — used for a group's own hub link so it isn't highlighted
   *  for every child route beneath it. */
  end?: boolean;
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

/** Single-link areas (not collapsible groups). */
export const homeNav = { to: '/', label: 'Home', icon: Home } as const;
export const setupsNav = { to: '/setups', label: 'Setups', icon: SlidersHorizontal } as const;
export const machineNav = { to: '/machine', label: 'My machine', icon: Laptop } as const;

export const packsGroup: NavGroup = {
  id: 'packs',
  label: 'Packs',
  icon: FolderGit2,
  description: [
    'A pack is a bundle of rules, skills, agents, and workflows around a role or capability. Starting points give you a complete baseline; add-ons layer a specialty on top.',
    'Compose packs into a setup, then install that setup into every framework you use. Pipelines show how a pack’s agents hand work to one another (running tasks, coding, planning) and let you compose your own handoff chain.',
  ],
  hubPath: '/packs',
  children: [
    {
      to: '/packs',
      label: 'Browse packs',
      icon: Compass,
      description: 'Search starter, community, and your own packs by kind, source, and category.',
      end: true,
    },
    {
      to: '/packs/mine',
      label: 'My packs',
      icon: FolderGit2,
      description: 'Create, edit, and organize the packs and items you own.',
    },
    {
      to: '/packs/pipelines',
      label: 'Pipelines',
      icon: Workflow,
      description: 'Browse and build multi-agent pipelines with handoffs between agents.',
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
      description: 'Review, approve, or deny community pack submissions.',
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
            'If you hold a moderator or admin role, this is also where you review community pack submissions and, for admins, configure system-wide behavior like SMTP, OAuth providers, and adapter availability.',
          ]
        : []),
    ],
    hubPath: '/settings',
    children,
  };
}

export interface Crumb {
  label: string;
  to?: string;
}

const SETTINGS_CRUMBS: Record<string, string> = {
  '/settings': 'Settings',
  '/settings/account': 'Account',
  '/settings/moderation': 'Moderation',
  '/settings/system': 'System',
};

/**
 * Breadcrumb trail for the slim top bar. Only the first crumb is a link —
 * intermediate dynamic segments ("Setup", "Pack") have no stable label until
 * the page loads its own data.
 */
export function getBreadcrumb(pathname: string): Crumb[] {
  const path = pathname.replace(/\/+$/, '') || '/';

  if (path === '/') return [{ label: 'Home' }];
  if (path === '/setups') return [{ label: 'Setups' }];
  if (path.startsWith('/setups/')) {
    const [id, child] = path.slice('/setups/'.length).split('/');
    const crumbs: Crumb[] = [{ label: 'Setups', to: '/setups' }];
    crumbs.push({ label: 'Setup', to: child ? `/setups/${id}` : undefined });
    if (child === 'install') crumbs.push({ label: 'Install' });
    return crumbs;
  }
  if (path === '/packs') return [{ label: 'Packs' }];
  if (path === '/packs/mine') {
    return [{ label: 'Packs', to: '/packs' }, { label: 'My packs' }];
  }
  if (path === '/packs/pipelines') {
    return [{ label: 'Packs', to: '/packs' }, { label: 'Pipelines' }];
  }
  if (path === '/packs/pipelines/new') {
    return [
      { label: 'Packs', to: '/packs' },
      { label: 'Pipelines', to: '/packs/pipelines' },
      { label: 'New pipeline' },
    ];
  }
  if (path === '/packs/import') {
    return [{ label: 'Packs', to: '/packs' }, { label: 'Import packs' }];
  }
  if (path.startsWith('/packs/')) {
    // `/packs/community/:id` is only a redirect now (decision A), so there is
    // no separate "Community pack" crumb; the destination is a plain pack.
    const rest = path.slice('/packs/'.length).split('/');
    const crumbs: Crumb[] = [{ label: 'Packs', to: '/packs' }, { label: 'Pack' }];
    if (rest[1] === 'items') crumbs.push({ label: 'New item' });
    if (rest[1] === 'publish') crumbs.push({ label: 'Publish' });
    if (rest[1] === 'manage') crumbs.push({ label: 'Manage items' });
    return crumbs;
  }
  if (path === '/machine') return [{ label: 'My machine' }];
  if (path === '/settings') return [{ label: 'Settings' }];
  if (path.startsWith('/settings/')) {
    return [{ label: 'Settings', to: '/settings' }, { label: SETTINGS_CRUMBS[path] ?? 'Settings' }];
  }
  return [{ label: 'Home', to: '/' }];
}
