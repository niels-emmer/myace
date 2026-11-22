import { Routes, Route, Navigate, Outlet, useLocation, useParams } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { useAuth } from './contexts/AuthContext';
import Layout from './components/Layout';
import PublicLayout from './components/PublicLayout';
import Landing from './pages/Landing';
import Login from './pages/Login';
import ResetPassword from './pages/ResetPassword';
import Home from './pages/Home';
import PacksLibrary from './pages/PacksLibrary';
import PackDetail from './pages/PackDetail';
import PublishPack from './pages/PublishPack';
import CollectionsManager from './pages/CollectionsManager';
import CollectionDetail from './pages/CollectionDetail';
import NewArtifactRule from './pages/NewArtifactRule';
import ProfileComposer from './pages/ProfileComposer';
import Onboarding from './pages/Onboarding';
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

// Some legacy paths preselected something via the query string
// (`/compile?profile=...`, `/import?source=...`). Keep that intent rather
// than dropping the query on redirect.
function RedirectWithSearch({ to }: { to: string }) {
  const { search } = useLocation();
  return <Navigate to={`${to}${search}`} replace />;
}

function LegacyCompileRedirect() {
  const { search } = useLocation();
  const profile = new URLSearchParams(search).get('profile');
  return <Navigate to={profile ? `/setups/${profile}/install` : '/setups'} replace />;
}

// Browse routes are public (ADR-0014): anonymous visitors get the storefront
// header, signed-in visitors keep the app's normal sidebar Layout. Both
// shells render an <Outlet/>, so this is a route element rather than a
// page-level wrapper.
function PackBrowseShell() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return user ? <Layout /> : <PublicLayout />;
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

      {/* Public browse surface — no session required. */}
      <Route element={<PackBrowseShell />}>
        <Route path="/packs" element={<PacksLibrary />} />
        {/* The community detail merged into the unified pack detail
            (decision A). Keep the old path as a param-preserving redirect. */}
        <Route path="/packs/community/:id" element={<ParamRedirect to={(id) => `/packs/${id}`} />} />
        <Route path="/packs/:id" element={<PackDetail />} />
      </Route>

      <Route element={<RequireAuth />}>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />

          <Route path="/onboarding" element={<Onboarding />} />
          <Route path="/setups" element={<ProfileComposer />} />
          <Route path="/setups/:id" element={<ProfileDetail />} />
          <Route path="/setups/:id/install" element={<TargetExporter />} />

          <Route path="/packs/mine" element={<CollectionsManager />} />
          <Route path="/packs/pipelines" element={<OrchestrationGallery />} />
          <Route path="/packs/pipelines/new" element={<OrchestratorBuilder />} />
          <Route path="/packs/import" element={<ImportPage />} />
          <Route path="/packs/:id/publish" element={<PublishPack />} />
          <Route path="/packs/:id/manage" element={<CollectionDetail />} />
          <Route path="/packs/:id/items/new" element={<NewArtifactRule />} />

          <Route path="/machine" element={<MachinePage />} />

          {/* Legacy paths, kept as redirects for old bookmarks/links */}
          <Route path="/collections" element={<Navigate to="/packs" replace />} />
          <Route path="/collections/community" element={<Navigate to="/packs" replace />} />
          <Route
            path="/collections/community/:id"
            element={<ParamRedirect to={(id) => `/packs/${id}`} />}
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
          <Route path="/build/compile" element={<LegacyCompileRedirect />} />
          <Route path="/build/orchestration" element={<Navigate to="/packs/pipelines" replace />} />
          <Route path="/build/orchestration/build" element={<Navigate to="/packs/pipelines/new" replace />} />

          <Route path="/profiles" element={<Navigate to="/setups" replace />} />
          <Route path="/profiles/:id" element={<ParamRedirect to={(id) => `/setups/${id}`} />} />
          <Route path="/compile" element={<LegacyCompileRedirect />} />
          <Route path="/export" element={<LegacyCompileRedirect />} />
          <Route path="/orchestration" element={<Navigate to="/packs/pipelines" replace />} />
          <Route path="/orchestration/build" element={<Navigate to="/packs/pipelines/new" replace />} />
          <Route path="/import" element={<RedirectWithSearch to="/packs/import" />} />
          <Route path="/setup-audit" element={<Navigate to="/machine?tab=audit" replace />} />
          <Route path="/sync" element={<Navigate to="/machine?tab=sync" replace />} />
          <Route path="/machine/import" element={<RedirectWithSearch to="/packs/import" />} />
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
