import { Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { useAuth } from './contexts/AuthContext';
import Layout from './components/Layout';
import Login from './pages/Login';
import ResetPassword from './pages/ResetPassword';
import Dashboard from './pages/Dashboard';
import CollectionsManager from './pages/CollectionsManager';
import CollectionDetail from './pages/CollectionDetail';
import CommunityCollections from './pages/CommunityCollections';
import CommunityCollectionDetail from './pages/CommunityCollectionDetail';
import ProfileComposer from './pages/ProfileComposer';
import ProfileDetail from './pages/ProfileDetail';
import ImportPage from './pages/ImportPage';
import TargetExporter from './pages/TargetExporter';
import SyncDashboard from './pages/SyncDashboard';
import UserSettings from './pages/UserSettings';
import SystemSettings from './pages/SystemSettings';
import ModerationQueue from './pages/ModerationQueue';

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

function RequireAdmin() {
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

  if (!user.is_admin) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}

function RequireModerator() {
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

  if (user.role !== 'moderator' && user.role !== 'admin') {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route element={<RequireAuth />}>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/collections" element={<CollectionsManager />} />
          <Route path="/collections/community" element={<CommunityCollections />} />
          <Route path="/collections/community/:id" element={<CommunityCollectionDetail />} />
          <Route path="/collections/:id" element={<CollectionDetail />} />
          <Route path="/profiles" element={<ProfileComposer />} />
          <Route path="/profiles/:id" element={<ProfileDetail />} />
          <Route path="/import" element={<ImportPage />} />
          <Route path="/compile" element={<TargetExporter />} />
          <Route path="/export" element={<Navigate to="/compile" replace />} />
          <Route path="/sync" element={<SyncDashboard />} />
          <Route path="/settings" element={<UserSettings />} />
          <Route element={<RequireModerator />}>
            <Route path="/moderation" element={<ModerationQueue />} />
          </Route>
          <Route element={<RequireAdmin />}>
            <Route path="/admin/system" element={<SystemSettings />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Route>
    </Routes>
  );
}
