import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect } from 'vitest';
import MachineHub from './MachineHub';

describe('MachineHub', () => {
  it('links to Import, Setup Audit, and Sync', () => {
    render(
      <MemoryRouter>
        <MachineHub />
      </MemoryRouter>
    );

    expect(screen.getByRole('link', { name: /Import/ })).toHaveAttribute(
      'href',
      '/machine/import'
    );
    expect(screen.getByRole('link', { name: /Setup Audit/ })).toHaveAttribute(
      'href',
      '/machine/audit'
    );
    expect(screen.getByRole('link', { name: /Sync/ })).toHaveAttribute('href', '/machine/sync');
  });
});
