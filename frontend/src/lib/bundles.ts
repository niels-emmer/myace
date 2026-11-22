/**
 * Curated "start here" bundles — a display-only shortcut over the starter
 * packs. Not a database entity (see docs/plans/v2.0-onboarding-revamp.md):
 * membership is matched by starter pack *name*, so this file is the single
 * place to change a bundle's display name, description, or membership.
 */
export interface Bundle {
  id: string;
  name: string;
  description: string;
  /** Name of the starter collection (`collection_type === 'base'`) this bundle starts from. */
  basePackName: string;
  /** Names of starter add-ons this bundle suggests pairing with the base. */
  addOnPackNames: string[];
}

export const BUNDLES: Bundle[] = [
  {
    id: 'software-engineer',
    name: 'Software Engineer',
    description: 'TDD, review discipline, and a planner → builder → verifier handoff chain.',
    basePackName: 'Software Engineer',
    addOnPackNames: ['QA / Test Engineer'],
  },
  {
    id: 'devops-engineer',
    name: 'DevOps Engineer',
    description: 'Infrastructure guardrails, deploy checklists, and incident response.',
    basePackName: 'DevOps Engineer',
    addOnPackNames: ['Infrastructure as Code Expert'],
  },
  {
    id: 'data-scientist',
    name: 'Data Scientist',
    description: 'Notebook hygiene, reproducibility, and eval-first experimentation.',
    basePackName: 'Data Scientist',
    addOnPackNames: [],
  },
  {
    id: 'vibecoder',
    name: 'Vibecoder',
    description: 'Ship fast with guardrails on secrets and destructive commands.',
    basePackName: 'Vibecoder',
    addOnPackNames: [],
  },
];
