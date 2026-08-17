import { useState } from 'react';
import { Link, Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom';
import { LayoutDashboard, LogOut, Menu, X, ChevronRight } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { collectionsGroup, buildGroup, machineGroup, getSettingsGroup, type NavGroup } from '../lib/navigation';

const navLinkClasses = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
    isActive
      ? 'bg-brand-50 text-brand-700'
      : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
  }`;

function NavGroupSection({
  group,
  groupActive,
  open,
  onToggle,
}: {
  group: NavGroup;
  groupActive: boolean;
  open: boolean;
  onToggle: () => void;
}) {
  const headerTextClasses = groupActive ? 'text-brand-700' : 'text-foreground';

  return (
    <div>
      <div
        className={`flex items-center rounded-lg text-sm font-medium transition-colors ${
          groupActive ? 'bg-brand-50' : 'hover:bg-accent'
        }`}
      >
        <Link
          to={group.hubPath ?? '#'}
          className={`flex flex-1 min-w-0 items-center gap-3 px-3 py-2.5 ${headerTextClasses}`}
        >
          <group.icon className="h-4 w-4 flex-shrink-0" />
          <span className="truncate">{group.label}</span>
        </Link>
        <button
          onClick={onToggle}
          aria-label={open ? `Collapse ${group.label}` : `Expand ${group.label}`}
          aria-expanded={open}
          className="p-2.5 pl-1.5 text-muted-foreground hover:text-accent-foreground flex-shrink-0"
        >
          <ChevronRight className={`h-3.5 w-3.5 transition-transform ${open ? 'rotate-90' : ''}`} />
        </button>
      </div>
      {open && (
        <div className="mt-1 ml-[1.15rem] pl-3 border-l border-border space-y-1">
          {group.children.map((child) => (
            <NavLink key={child.to} to={child.to} className={navLinkClasses}>
              <child.icon className="h-4 w-4" />
              {child.label}
            </NavLink>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [lastPathname, setLastPathname] = useState(location.pathname);
  const [openOverrides, setOpenOverrides] = useState<Record<string, boolean>>({});

  // Close the mobile drawer whenever navigation happens, so tapping a link
  // doesn't leave the overlay open behind the new page. Adjusted during
  // render (React's documented alternative to an Effect here) rather than
  // in a useEffect, which would cascade an extra render — same pattern
  // used for form-state initialization elsewhere in this app.
  if (location.pathname !== lastPathname) {
    setLastPathname(location.pathname);
    setMobileMenuOpen(false);
  }

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const groups = [collectionsGroup, buildGroup, machineGroup, getSettingsGroup(user)];

  // Collapsed by default; a group auto-expands once its hub or one of its
  // pages is the active route, so navigating straight to a sub-page never
  // hides the highlighted item. A manual toggle overrides that default
  // until the user toggles it again.
  const isGroupActive = (group: NavGroup) => !!group.hubPath && location.pathname.startsWith(group.hubPath);
  const isGroupOpen = (group: NavGroup) => openOverrides[group.id] ?? isGroupActive(group);
  const toggleGroup = (group: NavGroup) => {
    setOpenOverrides((prev) => ({ ...prev, [group.id]: !isGroupOpen(group) }));
  };

  return (
    <div className="flex flex-col lg:flex-row h-screen bg-background">
      {/* Mobile top bar */}
      <div className="lg:hidden flex items-center justify-between p-4 border-b border-border bg-card flex-shrink-0">
        <Link to="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
          <img src="/logo.png" alt="MyACE" className="h-7 w-7" />
          <h1 className="text-lg font-bold text-card-foreground">MyACE</h1>
        </Link>
        <button
          onClick={() => setMobileMenuOpen(true)}
          aria-label="Open menu"
          className="p-2 text-muted-foreground hover:text-accent-foreground hover:bg-accent rounded-lg transition-colors"
        >
          <Menu className="h-6 w-6" />
        </button>
      </div>

      {/* Backdrop */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
          onClick={() => setMobileMenuOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 w-64 bg-card border-r border-border flex flex-col
          transform transition-transform duration-200 ease-in-out
          lg:static lg:z-auto lg:translate-x-0
          ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'}`}
      >
        <div className="p-6 border-b border-border flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <img src="/logo.png" alt="MyACE" className="h-7 w-7" />
            <div>
              <h1 className="text-xl font-bold text-card-foreground">MyACE</h1>
              <p className="text-xs text-muted-foreground mt-1">Portable AI Agent Configs</p>
            </div>
          </Link>
          <button
            onClick={() => setMobileMenuOpen(false)}
            aria-label="Close menu"
            className="lg:hidden p-1 text-muted-foreground hover:text-accent-foreground hover:bg-accent rounded-lg transition-colors flex-shrink-0"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          <NavLink to="/" end className={navLinkClasses}>
            <LayoutDashboard className="h-4 w-4" />
            Dashboard
          </NavLink>

          {groups.map((group) => (
            <NavGroupSection
              key={group.id}
              group={group}
              groupActive={isGroupActive(group)}
              open={isGroupOpen(group)}
              onToggle={() => toggleGroup(group)}
            />
          ))}
        </nav>

        <div className="p-4 border-t border-border space-y-1">
          <div className="flex items-center justify-between px-3 py-2">
            <div className="min-w-0">
              <p className="text-sm font-medium text-card-foreground truncate">
                {user?.display_name ?? '...'}
              </p>
              <p className="text-xs text-muted-foreground">
                {user?.is_admin ? 'Admin' : 'User'}
              </p>
            </div>
            <button
              onClick={handleLogout}
              title="Log out"
              className="p-2 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-lg transition-colors flex-shrink-0"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 min-w-0 overflow-auto">
        <div className="p-4 sm:p-6 lg:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
