import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import CollectionsManager from './pages/CollectionsManager';
import ProfileComposer from './pages/ProfileComposer';
import ImportPage from './pages/ImportPage';
import TargetExporter from './pages/TargetExporter';
import Settings from './pages/Settings';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/collections" element={<CollectionsManager />} />
        <Route path="/profiles" element={<ProfileComposer />} />
        <Route path="/import" element={<ImportPage />} />
        <Route path="/export" element={<TargetExporter />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
