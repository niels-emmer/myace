import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect } from 'vitest';
import { FolderGit2, Globe } from 'lucide-react';
import SectionHub from './SectionHub';
import type { NavGroup } from '../lib/navigation';

const testGroup: NavGroup = {
  id: 'test',
  label: 'Test Group',
  icon: FolderGit2,
  description: ['A group for testing.', 'A second paragraph for testing.'],
  hubPath: '/test',
  children: [
    { to: '/test/one', label: 'One', icon: FolderGit2, description: 'First item.' },
    { to: '/test/two', label: 'Two', icon: Globe, description: 'Second item.' },
  ],
};

describe('SectionHub', () => {
  it('renders the group title, every description paragraph, and one card per child', () => {
    render(
      <MemoryRouter>
        <SectionHub group={testGroup} />
      </MemoryRouter>
    );

    expect(screen.getByText('Test Group')).toBeInTheDocument();
    expect(screen.getByText('A group for testing.')).toBeInTheDocument();
    expect(screen.getByText('A second paragraph for testing.')).toBeInTheDocument();

    expect(screen.getByText('One')).toBeInTheDocument();
    expect(screen.getByText('First item.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /One/ })).toHaveAttribute('href', '/test/one');

    expect(screen.getByText('Two')).toBeInTheDocument();
    expect(screen.getByText('Second item.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Two/ })).toHaveAttribute('href', '/test/two');
  });
});
