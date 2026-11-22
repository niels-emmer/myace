import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Download,
  FilePlus2,
  FolderGit2,
  Home,
  Laptop,
  LayoutGrid,
  Search,
  Settings,
  SlidersHorizontal,
  Upload,
  Workflow,
} from 'lucide-react';
import { collectionsApi, profilesApi } from '../lib/api';
import { packHref, packSource } from '../lib/packs';
import { useAuth } from '../contexts/AuthContext';

interface CommandPaletteProps {
  open: boolean;
  onOpen: () => void;
  onClose: () => void;
}

interface PaletteItem {
  id: string;
  group: 'Actions' | 'Pages' | 'Packs' | 'Setups';
  label: string;
  hint?: string;
  to: string;
  icon: typeof Home;
}

const ACTIONS: PaletteItem[] = [
  { id: 'action-new-setup', group: 'Actions', label: 'New setup', hint: 'Guided setup from packs', to: '/onboarding', icon: FilePlus2 },
  { id: 'action-import', group: 'Actions', label: 'Import packs', hint: 'From your machine or a repository', to: '/packs/import', icon: Upload },
  { id: 'action-machine', group: 'Actions', label: 'Check my machine', hint: 'Companion status, audit, and drift', to: '/machine', icon: Laptop },
  { id: 'action-publish', group: 'Actions', label: 'Publish a pack', hint: 'Manage and publish your packs', to: '/packs/mine', icon: FolderGit2 },
];

const PAGES: PaletteItem[] = [
  { id: 'page-home', group: 'Pages', label: 'Home', to: '/', icon: Home },
  { id: 'page-setups', group: 'Pages', label: 'Setups', to: '/setups', icon: SlidersHorizontal },
  { id: 'page-packs', group: 'Pages', label: 'Packs', to: '/packs', icon: LayoutGrid },
  { id: 'page-pipelines', group: 'Pages', label: 'Pipelines', to: '/packs/pipelines', icon: Workflow },
  { id: 'page-machine', group: 'Pages', label: 'My machine', to: '/machine', icon: Laptop },
  { id: 'page-settings', group: 'Pages', label: 'Settings', to: '/settings', icon: Settings },
];

const GROUP_ORDER: PaletteItem['group'][] = ['Actions', 'Pages', 'Packs', 'Setups'];

function matches(value: string, query: string): boolean {
  return value.toLowerCase().includes(query.toLowerCase());
}

export default function CommandPalette({ open, onOpen, onClose }: CommandPaletteProps) {
  const navigate = useNavigate();
  const { user } = useAuth();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const [wasOpen, setWasOpen] = useState(open);

  // Reset the search each time the palette opens. Adjusting state during
  // render is React's documented alternative to an Effect for this case
  // (the repo uses the same pattern in Layout for mobile-menu closing).
  if (open !== wasOpen) {
    setWasOpen(open);
    if (open) {
      setQuery('');
      setActiveIndex(0);
    }
  }

  // Same query keys the rest of the app uses, so opening the palette reuses
  // whatever is already in the React Query cache rather than refetching.
  const { data: collections } = useQuery({
    queryKey: ['collections'],
    queryFn: () => collectionsApi.list(),
    enabled: open,
  });
  const { data: profiles } = useQuery({
    queryKey: ['profiles'],
    queryFn: () => profilesApi.list(),
    enabled: open,
  });

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        if (open) onClose();
        else onOpen();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onOpen, onClose]);

  useEffect(() => {
    if (!open) return;
    // Wait for the dialog to mount before focusing the input.
    const frame = requestAnimationFrame(() => inputRef.current?.focus());
    return () => cancelAnimationFrame(frame);
  }, [open]);

  const items = useMemo<PaletteItem[]>(() => {
    const packItems: PaletteItem[] = (collections ?? [])
      .filter((collection) => matches(`${collection.name} ${collection.description ?? ''}`, query))
      .slice(0, 5)
      .map((collection) => {
        const source = packSource(collection, user?.id);
        return {
          id: `pack-${collection.id}`,
          group: 'Packs',
          label: collection.name,
          hint: source === 'mine' ? 'Your pack' : source === 'starter' ? 'Starter pack' : 'Community pack',
          to: packHref(collection, source),
          icon: FolderGit2,
        };
      });

    const setupItems: PaletteItem[] = (profiles ?? [])
      // `GET /profiles` also returns other users' public profiles; the
      // palette is a personal shortcut surface, so only list your own.
      .filter((profile) => profile.owner_id === user?.id)
      .filter((profile) => matches(`${profile.name} ${profile.description ?? ''}`, query))
      .slice(0, 5)
      .map((profile) => ({
        id: `setup-${profile.id}`,
        group: 'Setups',
        label: profile.name,
        hint: 'Setup',
        to: `/setups/${profile.id}`,
        icon: Download,
      }));

    const actions = ACTIONS.filter((item) => matches(`${item.label} ${item.hint ?? ''}`, query));
    const pages = PAGES.filter((item) => matches(item.label, query));

    return [...actions, ...pages, ...packItems, ...setupItems];
  }, [collections, profiles, query, user?.id]);

  const grouped = useMemo(
    () =>
      GROUP_ORDER.map((group) => ({
        group,
        items: items.filter((item) => item.group === group),
      })).filter((entry) => entry.items.length > 0),
    [items],
  );

  // Keep the highlight in range while the result set shrinks.
  const activePosition = items.length === 0 ? -1 : Math.min(activeIndex, items.length - 1);
  const activeItem = activePosition >= 0 ? items[activePosition] : null;

  const choose = (item: PaletteItem) => {
    onClose();
    navigate(item.to);
  };

  if (!open) return null;

  const handleKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Escape') {
      event.preventDefault();
      onClose();
      return;
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveIndex(items.length === 0 ? 0 : (activePosition + 1) % items.length);
      return;
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveIndex(items.length === 0 ? 0 : (activePosition - 1 + items.length) % items.length);
      return;
    }
    if (event.key === 'Enter') {
      event.preventDefault();
      if (activeItem) choose(activeItem);
      return;
    }
    // Everything else stays in the input — a simple focus trap for a dialog
    // whose only focusable control is the search field.
    if (event.key === 'Tab') event.preventDefault();
  };

  return (
    <div
      className="fixed inset-0 z-[60] bg-black/50 p-4 pt-[12vh]"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        onKeyDown={handleKeyDown}
        className="mx-auto w-full max-w-xl overflow-hidden rounded-xl border border-border bg-card shadow-2xl"
      >
        <div className="flex items-center gap-3 border-b border-border px-4 py-3">
          <Search className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setActiveIndex(0);
            }}
            role="combobox"
            aria-expanded="true"
            aria-controls="command-palette-results"
            aria-autocomplete="list"
            aria-activedescendant={activeItem ? `command-option-${activeItem.id}` : undefined}
            aria-label="Search commands, packs, and setups"
            placeholder="Search commands, packs, and setups…"
            className="w-full bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
          />
          <kbd className="hidden flex-shrink-0 rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground sm:inline">
            Esc
          </kbd>
        </div>

        <div id="command-palette-results" role="listbox" aria-label="Results" className="max-h-[55vh] overflow-y-auto py-2">
          {items.length === 0 ? (
            <p className="px-4 py-8 text-center text-sm text-muted-foreground">No matches for “{query}”.</p>
          ) : (
            grouped.map(({ group, items: groupItems }) => (
              <div key={group} role="presentation">
                <p className="px-4 pb-1 pt-3 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground" role="presentation">
                  {group}
                </p>
                {groupItems.map((item) => {
                  const index = items.indexOf(item);
                  const selected = index === activePosition;
                  const Icon = item.icon;
                  return (
                    <div
                      key={item.id}
                      id={`command-option-${item.id}`}
                      role="option"
                      aria-selected={selected}
                      onMouseDown={(event) => event.preventDefault()}
                      onClick={() => choose(item)}
                      onMouseEnter={() => setActiveIndex(index)}
                      className={`flex cursor-pointer items-center gap-3 px-4 py-2.5 text-sm ${
                        selected ? 'bg-brand-50 text-brand-700' : 'text-foreground'
                      }`}
                    >
                      <Icon className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                      <span className="min-w-0 flex-1 truncate">{item.label}</span>
                      {item.hint && <span className="truncate text-xs text-muted-foreground">{item.hint}</span>}
                    </div>
                  );
                })}
              </div>
            ))
          )}
        </div>

        <div className="flex items-center gap-3 border-t border-border px-4 py-2 text-[11px] text-muted-foreground">
          <span>↑↓ to navigate</span>
          <span>Enter to open</span>
          <span>Esc to close</span>
        </div>
      </div>
    </div>
  );
}
