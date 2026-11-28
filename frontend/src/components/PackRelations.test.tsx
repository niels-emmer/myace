import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { PackRelationsCard } from './PackRelations';

function renderCard(relations: Parameters<typeof PackRelationsCard>[0]['relations']) {
  return render(
    <MemoryRouter>
      <PackRelationsCard relations={relations} />
    </MemoryRouter>,
  );
}

describe('PackRelationsCard', () => {
  it('links layered-on and paired packs', () => {
    renderCard({
      layers_on: [{ id: 'iac-id', name: 'Infrastructure as Code Expert', slug: 'iac-expert' }],
      pairs_with: [{ id: 'devops-id', name: 'DevOps Engineer', slug: 'devops-engineer' }],
    });

    expect(screen.getByRole('heading', { name: 'Works with other packs' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Infrastructure as Code Expert' })).toHaveAttribute(
      'href',
      '/packs/iac-id',
    );
    expect(screen.getByRole('link', { name: 'DevOps Engineer' })).toHaveAttribute(
      'href',
      '/packs/devops-id',
    );
    expect(screen.getByText(/a suggestion, not a requirement/)).toBeInTheDocument();
  });

  it('renders nothing when there are no relations', () => {
    const { container } = renderCard(null);
    expect(container).toBeEmptyDOMElement();

    const empty = renderCard({ layers_on: [], pairs_with: [] });
    expect(empty.container).toBeEmptyDOMElement();
  });

  it('shows only the section that has packs', () => {
    renderCard({
      layers_on: [],
      pairs_with: [{ id: 'x', name: 'Frontend Specialist', slug: 'frontend' }],
    });

    expect(screen.queryByText(/Layers on/)).not.toBeInTheDocument();
    expect(screen.getByText(/Pairs well with/)).toBeInTheDocument();
  });
});
