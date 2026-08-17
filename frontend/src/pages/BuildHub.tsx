import SectionHub from '../components/SectionHub';
import { buildGroup } from '../lib/navigation';

export default function BuildHub() {
  return <SectionHub group={buildGroup} />;
}
