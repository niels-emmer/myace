import { useQuery } from '@tanstack/react-query';
import { adaptersApi } from '../lib/api';

export default function TargetChecklist({
  selected,
  onChange,
}: {
  selected: string[];
  onChange: (next: string[]) => void;
}) {
  const { data: adapters, isLoading } = useQuery({
    queryKey: ['adapters'],
    queryFn: () => adaptersApi.list(),
  });

  const toggle = (name: string) => {
    if (selected.includes(name)) {
      onChange(selected.filter((t) => t !== name));
    } else {
      onChange([...selected, name]);
    }
  };

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading targets...</p>;
  }

  return (
    <div className="space-y-1 max-h-48 overflow-y-auto">
      {(adapters ?? []).map((adapter) => (
        <label
          key={adapter.name}
          className="flex items-center gap-2 text-sm text-foreground cursor-pointer hover:bg-accent rounded px-1.5 py-1"
        >
          <input
            type="checkbox"
            checked={selected.includes(adapter.name)}
            onChange={() => toggle(adapter.name)}
            className="h-4 w-4 rounded border-input text-brand-600 focus:ring-brand-500"
          />
          {adapter.name}
        </label>
      ))}
    </div>
  );
}
