import { Routes, Route, Navigate, Outlet, useParams } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { useAuth } from './contexts/AuthContext';
import Layout from './components/Layout';
import Landing from './pages/Landing';
import Login from './pages/Login';
import ResetPassword from './pages/ResetPassword';
import Home from './pages/Home';
import PacksLibrary from './pages/PacksLibrary';
import CollectionsManager from './pages/CollectionsManager';
import CollectionDetail from './pages/CollectionDetail';
import NewArtifactRule from './pages/NewArtifactRule';
import CommunityCollectionDetail from './pages/CommunityCollectionDetail';
import ProfileComposer from './pages/ProfileComposer';
import ProfileDetail from './pages/ProfileDetail';
import TargetExporter from './pages/TargetExporter';
import OrchestrationGallery from './pages/OrchestrationGallery';
import OrchestratorBuilder from './pages/OrchestratorBuilder';
import MachinePage from './pages/MachinePage';
import ImportPage from './pages/ImportPage';
import SettingsHub from './pages/SettingsHub';
import UserSettings from './pages/UserSettings';
import SystemSettings from './pages/SystemSettings';
import ModerationQueue from './pages/ModerationQueue';

// Legacy param-bearing paths. `Navigate`'s `to` can't contain a route param
// placeholder, so the :id is read here and interpolated before redirecting
// (AGENTS.md rule 38).
function ParamRedirect({ to }: { to: (id: string) => string }) {
  const { id } = useParams<{ id: string }>();
  return <Navigate to={id ? to(id) : '/'} replace />;
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
          <Route path="/" element={<Home />} />

          <Route path="/setups" element={<ProfileComposer />} />
          <Route path="/setups/:id" element={<ProfileDetail />} />
          <Route path="/setups/:id/install" element={<TargetExporter />} />

          <Route path="/packs" element={<PacksLibrary />} />
          <Route path="/packs/mine" element={<CollectionsManager />} />
          <Route path="/packs/pipelines" element={<OrchestrationGallery />} />
          <Route path="/packs/pipelines/new" element={<OrchestratorBuilder />} />
          <Route path="/packs/import" element={<ImportPage />} />
          <Route path="/packs/community/:id" element={<CommunityCollectionDetail />} />
          <Route path="/packs/:id/items/new" element={<NewArtifactRule />} />
          <Route path="/packs/:id" element={<CollectionDetail />} />

          <Route path="/machine" element={<MachinePage />} />

          {/* Legacy paths, kept as redirects for old bookmarks/links */}
          <Route path="/collections" element={<Navigate to="/packs" replace />} />
          <Route path="/collections/community" element={<Navigate to="/packs" replace />} />
          <Route
            path="/collections/community/:id"
            element={<ParamRedirect to={(id) => `/packs/community/${id}`} />}
          />
          <Route path="/collections/mine" element={<Navigate to="/packs/mine" replace />} />
          <Route
            path="/collections/:id/artifacts/new"
            element={<ParamRedirect to={(id) => `/packs/${id}/items/new`} />}
          />
          <Route path="/collections/:id" element={<ParamRedirect to={(id) => `/packs/${id}`} />} />

          <Route path="/build" element={<Navigate to="/setups" replace />} />
          <Route path="/build/profiles" element={<Navigate to="/setups" replace />} />
          <Route path="/build/profiles/:id" element={<ParamRedirect to={(id) => `/setups/${id}`} />} />
          <Route path="/build/compile" element={<Navigate to="/setups" replace />} />
          <Route path="/build/orchestration" element={<Navigate to="/packs/pipelines" replace />} />
          <Route path="/build/orchestration/build" element={<Navigate to="/packs/pipelines/new" replace />} />

          <Route path="/profiles" element={<Navigate to="/setups" replace />} />
          <Route path="/profiles/:id" element={<ParamRedirect to={(id) => `/setups/${id}`} />} />
          <Route path="/compile" element={<Navigate to="/setups" replace />} />
          <Route path="/export" element={<Navigate to="/setups" replace />} />
          <Route path="/orchestration" element={<Navigate to="/packs/pipelines" replace />} />
          <Route path="/orchestration/build" element={<Navigate to="/packs/pipelines/new" replace />} />
          <Route path="/import" element={<Navigate to="/packs/import" replace />} />
          <Route path="/setup-audit" element={<Navigate to="/machine?tab=audit" replace />} />
          <Route path="/sync" element={<Navigate to="/machine?tab=sync" replace />} />
          <Route path="/machine/audit" element={<Navigate to="/machine?tab=audit" replace />} />
          <Route path="/machine/sync" element={<Navigate to="/machine?tab=sync" replace />} />
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
