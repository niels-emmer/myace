import { Outlet, NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  FolderGit2,
  SlidersHorizontal,
  Upload,
  Download,
  Settings,
  Sparkles,
} from 'lucide-react';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/collections', icon: FolderGit2, label: 'Collections' },
  { to: '/profiles', icon: SlidersHorizontal, label: 'Profiles' },
  { to: '/import', icon: Upload, label: 'Import' },
  { to: '/export', icon: Download, label: 'Export' },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

export default function Layout() {
  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-brand-600" />
            <h1 className="text-xl font-bold text-gray-900">MyACE</h1>
          </div>
          <p className="text-xs text-gray-500 mt-1">Agentic Coding Environment</p>
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
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                }`
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-gray-200">
          <div className="flex items-center gap-3 px-3 py-2 text-xs text-gray-500">
            <div className="h-2 w-2 rounded-full bg-green-400" />
            API Connected
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
