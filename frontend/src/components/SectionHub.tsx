import { Link } from 'react-router-dom';
import type { NavGroup } from '../lib/navigation';

export default function SectionHub({ group }: { group: NavGroup }) {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-foreground">{group.label}</h1>
        <div className="space-y-2 mt-1">
          {group.description.map((paragraph, i) => (
            <p key={i} className="text-muted-foreground">
              {paragraph}
            </p>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {group.children.map((child) => (
          <Link
            key={child.to}
            to={child.to}
            className="bg-card rounded-xl border border-border p-6 flex flex-col gap-3 hover:shadow-sm hover:border-input transition-shadow"
          >
            <div className="p-3 rounded-lg bg-brand-50 text-brand-700 w-fit">
              <child.icon className="h-6 w-6" />
            </div>
            <div>
              <h2 className="font-semibold text-card-foreground">{child.label}</h2>
              <p className="text-sm text-muted-foreground mt-1">{child.description}</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
