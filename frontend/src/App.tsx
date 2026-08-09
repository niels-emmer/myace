import { Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { useAuth } from './contexts/AuthContext';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import CollectionsManager from './pages/CollectionsManager';
import CollectionDetail from './pages/CollectionDetail';
import ProfileComposer from './pages/ProfileComposer';
import ImportPage from './pages/ImportPage';
import TargetExporter from './pages/TargetExporter';
import Settings from './pages/Settings';

function RequireAuth() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<RequireAuth />}>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/collections" element={<CollectionsManager />} />
          <Route path="/collections/:id" element={<CollectionDetail />} />
          <Route path="/profiles" element={<ProfileComposer />} />
          <Route path="/import" element={<ImportPage />} />
          <Route path="/compile" element={<TargetExporter />} />
          <Route path="/export" element={<Navigate to="/compile" replace />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Route>
    </Routes>
  );
}
