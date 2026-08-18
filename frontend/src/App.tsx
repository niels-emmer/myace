import { Routes, Route, Navigate, Outlet, useParams } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { useAuth } from './contexts/AuthContext';
import Layout from './components/Layout';
import Landing from './pages/Landing';
import Login from './pages/Login';
import ResetPassword from './pages/ResetPassword';
import Dashboard from './pages/Dashboard';
import CollectionsHub from './pages/CollectionsHub';
import CollectionsManager from './pages/CollectionsManager';
import CollectionDetail from './pages/CollectionDetail';
import NewArtifactRule from './pages/NewArtifactRule';
import CommunityCollections from './pages/CommunityCollections';
import CommunityCollectionDetail from './pages/CommunityCollectionDetail';
import BuildHub from './pages/BuildHub';
import ProfileComposer from './pages/ProfileComposer';
import ProfileDetail from './pages/ProfileDetail';
import TargetExporter from './pages/TargetExporter';
import OrchestrationGallery from './pages/OrchestrationGallery';
import OrchestratorBuilder from './pages/OrchestratorBuilder';
import MachineHub from './pages/MachineHub';
import ImportPage from './pages/ImportPage';
import SetupAudit from './pages/SetupAudit';
import SyncDashboard from './pages/SyncDashboard';
import SettingsHub from './pages/SettingsHub';
import UserSettings from './pages/UserSettings';
import SystemSettings from './pages/SystemSettings';
import ModerationQueue from './pages/ModerationQueue';

// Legacy top-level path -> new grouped path. `Navigate`'s `to` can't itself
// contain a route param placeholder, so the :id param is read here and
// interpolated before redirecting.
function ProfileDetailRedirect() {
  const { id } = useParams();
  return <Navigate to={`/build/profiles/${id}`} replace />;
}

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
    return <Navigate to="/welcome" replace />;
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
      <Route path="/welcome" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route element={<RequireAuth />}>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />

          <Route path="/collections" element={<CollectionsHub />} />
          <Route path="/collections/mine" element={<CollectionsManager />} />
          <Route path="/collections/community" element={<CommunityCollections />} />
          <Route path="/collections/community/:id" element={<CommunityCollectionDetail />} />
          <Route path="/collections/:id" element={<CollectionDetail />} />
          <Route path="/collections/:id/artifacts/new" element={<NewArtifactRule />} />

          <Route path="/build" element={<BuildHub />} />
          <Route path="/build/profiles" element={<ProfileComposer />} />
          <Route path="/build/profiles/:id" element={<ProfileDetail />} />
          <Route path="/build/orchestration" element={<OrchestrationGallery />} />
          <Route path="/build/orchestration/build" element={<OrchestratorBuilder />} />
          <Route path="/build/compile" element={<TargetExporter />} />

          <Route path="/machine" element={<MachineHub />} />
          <Route path="/machine/import" element={<ImportPage />} />
          <Route path="/machine/audit" element={<SetupAudit />} />
          <Route path="/machine/sync" element={<SyncDashboard />} />

          {/* Legacy top-level paths, kept as redirects for old bookmarks/links */}
          <Route path="/profiles" element={<Navigate to="/build/profiles" replace />} />
          <Route path="/profiles/:id" element={<ProfileDetailRedirect />} />
          <Route path="/orchestration" element={<Navigate to="/build/orchestration" replace />} />
          <Route path="/orchestration/build" element={<Navigate to="/build/orchestration/build" replace />} />
          <Route path="/compile" element={<Navigate to="/build/compile" replace />} />
          <Route path="/export" element={<Navigate to="/build/compile" replace />} />
          <Route path="/import" element={<Navigate to="/machine/import" replace />} />
          <Route path="/setup-audit" element={<Navigate to="/machine/audit" replace />} />
          <Route path="/sync" element={<Navigate to="/machine/sync" replace />} />
          <Route path="/moderation" element={<Navigate to="/settings/moderation" replace />} />
          <Route path="/admin/system" element={<Navigate to="/settings/system" replace />} />

          <Route path="/settings" element={<SettingsHub />} />
          <Route path="/settings/account" element={<UserSettings />} />
          <Route element={<RequireModerator />}>
            <Route path="/settings/moderation" element={<ModerationQueue />} />
          </Route>
          <Route element={<RequireAdmin />}>
            <Route path="/settings/system" element={<SystemSettings />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Route>
    </Routes>
  );
}
