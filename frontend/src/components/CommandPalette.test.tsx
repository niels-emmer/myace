import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import CommandPalette from './CommandPalette';
import { collectionsApi, profilesApi } from '../lib/api';
import type { Collection, Profile } from '../types';

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 'user-1' } }),
}));

vi.mock('../lib/api', () => ({
  collectionsApi: { list: vi.fn() },
  profilesApi: { list: vi.fn() },
}));

const pack: Collection = {
  id: 'pack-1',
  owner_id: 'starter-owner',
  name: 'Software Engineer',
  description: 'A starting point',
  git_url: '',
  git_branch: 'main',
  collection_type: 'base',
  visibility: 'public',
  is_active: true,
  artifact_count: 12,
  download_count: 100,
  published: true,
  is_starter_pack: true,
  avg_rating: 4.8,
  rating_count: 3,
  moderation_status: 'approved',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const publicProfile: Profile = {
  id: 'public-setup',
  owner_id: 'user-2',
  name: 'Public setup',
  base_collection_id: 'pack-1',
  additional_collection_ids: [],
  disabled_artifact_ids: [],
  is_public: true,
  version: 1,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const profile: Profile = {
  id: 'setup-1',
  owner_id: 'user-1',
  name: 'My software setup',
  base_collection_id: 'pack-1',
  additional_collection_ids: [],
  disabled_artifact_ids: [],
  is_public: false,
  version: 1,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

function LocationProbe() {
  const location = useLocation();
  return <div>at:{location.pathname}</div>;
}

function renderPalette(open = true, onOpen = vi.fn(), onClose = vi.fn()) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const result = render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/packs']}>
        <CommandPalette open={open} onOpen={onOpen} onClose={onClose} />
        <Routes>
          <Route path="*" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return { ...result, onOpen, onClose };
}

describe('CommandPalette', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(collectionsApi.list).mockResolvedValue([pack]);
    vi.mocked(profilesApi.list).mockResolvedValue([profile, publicProfile]);
  });

  it('opens on Ctrl+K / Cmd+K when closed', () => {
    const { onOpen } = renderPalette(false);

    fireEvent.keyDown(window, { key: 'k', ctrlKey: true });
    expect(onOpen).toHaveBeenCalledTimes(1);

    fireEvent.keyDown(window, { key: 'K', metaKey: true });
    expect(onOpen).toHaveBeenCalledTimes(2);
  });

  it('renders actions, pages, cached packs, and setups', async () => {
    renderPalette();

    expect(screen.getByRole('dialog', { name: /Command palette/i })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: /New setup/ })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: /Import packs/ })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: /My machine/ })).toBeInTheDocument();

    expect(await screen.findByRole('option', { name: /Software Engineer/ })).toBeInTheDocument();
    expect(await screen.findByRole('option', { name: /My software setup/ })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: /Public setup/ })).not.toBeInTheDocument();
  });

  it('moves with arrow keys and opens the active item with Enter', async () => {
    renderPalette();
    const dialog = screen.getByRole('dialog', { name: /Command palette/i });

    fireEvent.keyDown(dialog, { key: 'ArrowDown' });
    fireEvent.keyDown(dialog, { key: 'Enter' });

    expect(await screen.findByText('at:/packs/import')).toBeInTheDocument();
  });

  it('filters to a page and navigates to it', async () => {
    renderPalette();
    const input = screen.getByRole('combobox', { name: /Search commands/i });

    fireEvent.change(input, { target: { value: 'home' } });
    expect(screen.getByRole('option', { name: /Home/ })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: /Import packs/ })).not.toBeInTheDocument();

    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Enter' });
    expect(await screen.findByText('at:/')).toBeInTheDocument();
  });

  it('closes on Escape', () => {
    const { onClose } = renderPalette();

    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('closes when the backdrop is clicked', () => {
    const { onClose } = renderPalette();
    const dialog = screen.getByRole('dialog');

    fireEvent.mouseDown(dialog.parentElement!);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('opens a pack result on click', async () => {
    renderPalette();
    const packOption = await screen.findByRole('option', { name: /Software Engineer/ });

    fireEvent.click(packOption);

    expect(await screen.findByText('at:/packs/pack-1')).toBeInTheDocument();
  });

  it('traps Tab focus in the search input', () => {
    renderPalette();
    const dialog = screen.getByRole('dialog');
    const event = new KeyboardEvent('keydown', { key: 'Tab', bubbles: true, cancelable: true });

    dialog.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(true);
  });

  it('keeps the active option in range after filtering', async () => {
    renderPalette();
    const dialog = screen.getByRole('dialog');

    fireEvent.keyDown(dialog, { key: 'ArrowDown' });
    fireEvent.keyDown(dialog, { key: 'ArrowDown' });
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'settings' } });

    await waitFor(() => {
      expect(screen.getByRole('option', { name: /Settings/ })).toHaveAttribute(
        'aria-selected',
        'true',
      );
    });
  });

  it('sends New setup to the onboarding wizard', async () => {
    renderPalette();
    const input = screen.getByRole('combobox', { name: /Search commands/i });

    fireEvent.change(input, { target: { value: 'new setup' } });
    fireEvent.keyDown(screen.getByRole('dialog', { name: /Command palette/i }), { key: 'Enter' });

    expect(await screen.findByText('at:/onboarding')).toBeInTheDocument();
  });
});
