import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import TargetChecklist from './TargetChecklist';

vi.mock('../lib/api', () => ({
  adaptersApi: { list: vi.fn() },
}));

import { adaptersApi } from '../lib/api';

function renderChecklist(selected: string[], onChange: (next: string[]) => void) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <TargetChecklist selected={selected} onChange={onChange} />
    </QueryClientProvider>
  );
}

describe('TargetChecklist', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (adaptersApi.list as ReturnType<typeof vi.fn>).mockResolvedValue([
      { name: 'claude-code', description: '', targets: ['claude-code'], enabled: true },
      { name: 'opencode', description: '', targets: ['opencode'], enabled: true },
    ]);
  });

  it('renders one checkbox per adapter, checked according to `selected`', async () => {
    renderChecklist(['opencode'], vi.fn());

    const claudeCheckbox = await screen.findByRole('checkbox', { name: 'claude-code' });
    const opencodeCheckbox = screen.getByRole('checkbox', { name: 'opencode' });
    expect(claudeCheckbox).not.toBeChecked();
    expect(opencodeCheckbox).toBeChecked();
  });

  it('calls onChange with the target added when an unchecked box is clicked', async () => {
    const onChange = vi.fn();
    renderChecklist(['opencode'], onChange);

    const claudeCheckbox = await screen.findByRole('checkbox', { name: 'claude-code' });
    fireEvent.click(claudeCheckbox);

    expect(onChange).toHaveBeenCalledWith(['opencode', 'claude-code']);
  });

  it('calls onChange with the target removed when a checked box is clicked', async () => {
    const onChange = vi.fn();
    renderChecklist(['opencode', 'claude-code'], onChange);

    const opencodeCheckbox = await screen.findByRole('checkbox', { name: 'opencode' });
    fireEvent.click(opencodeCheckbox);

    expect(onChange).toHaveBeenCalledWith(['claude-code']);
  });
});
