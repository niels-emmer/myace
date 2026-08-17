import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect } from 'vitest';
import BuildHub from './BuildHub';

describe('BuildHub', () => {
  it('links to Profiles, Orchestration, and Compile & Export', () => {
    render(
      <MemoryRouter>
        <BuildHub />
      </MemoryRouter>
    );

    expect(screen.getByRole('link', { name: /Profiles/ })).toHaveAttribute(
      'href',
      '/build/profiles'
    );
    expect(screen.getByRole('link', { name: /Orchestration/ })).toHaveAttribute(
      'href',
      '/build/orchestration'
    );
    expect(screen.getByRole('link', { name: /Compile & Export/ })).toHaveAttribute(
      'href',
      '/build/compile'
    );
  });
});
