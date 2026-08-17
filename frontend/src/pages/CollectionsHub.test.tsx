import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect } from 'vitest';
import CollectionsHub from './CollectionsHub';

describe('CollectionsHub', () => {
  it('links to My Collections and Community', () => {
    render(
      <MemoryRouter>
        <CollectionsHub />
      </MemoryRouter>
    );

    expect(screen.getByRole('link', { name: /My Collections/ })).toHaveAttribute(
      'href',
      '/collections/mine'
    );
    expect(screen.getByRole('link', { name: /Community/ })).toHaveAttribute(
      'href',
      '/collections/community'
    );
  });
});
