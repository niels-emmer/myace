import { Link, Outlet, NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  FolderGit2,
  SlidersHorizontal,
  Upload,
  Download,
  Settings,
  LogOut,
  Shield,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/collections', icon: FolderGit2, label: 'Collections' },
  { to: '/profiles', icon: SlidersHorizontal, label: 'Profiles' },
  { to: '/import', icon: Upload, label: 'Import' },
  { to: '/compile', icon: Download, label: 'Compile' },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <aside className="w-64 bg-card border-r border-border flex flex-col">
        <div className="p-6 border-b border-border">
          <Link to="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <img src="/logo.png" alt="MyACE" className="h-7 w-7" />
            <h1 className="text-xl font-bold text-card-foreground">MyACE</h1>
          </Link>
          <p className="text-xs text-muted-foreground mt-1">Portable AI Agent Configs</p>
        </div>

        <nav className="flex-1 p-4 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-brand-50 text-brand-700'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                }`
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
          {user?.is_admin && (
            <NavLink
              to="/admin/system"
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-brand-50 text-brand-700'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                }`
              }
            >
              <Shield className="h-4 w-4" />
              System
            </NavLink>
          )}
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
      <main className="flex-1 overflow-auto">
        <div className="p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
