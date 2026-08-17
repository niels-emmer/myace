import SectionHub from '../components/SectionHub';
import { getSettingsGroup } from '../lib/navigation';
import { useAuth } from '../contexts/AuthContext';

export default function SettingsHub() {
  const { user } = useAuth();
  return <SectionHub group={getSettingsGroup(user)} />;
}
