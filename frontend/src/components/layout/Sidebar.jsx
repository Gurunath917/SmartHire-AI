import { NavLink } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import {
  LayoutDashboard, User, FileText, Briefcase, Target,
  Map, MessageSquare, Video, BarChart3, Users,
  PlusCircle, Settings,
} from 'lucide-react';

const CANDIDATE_LINKS = [
  { to: '/candidate/dashboard',  label: 'Dashboard',   icon: LayoutDashboard },
  { to: '/candidate/profile',    label: 'Profile',     icon: User },
  { to: '/candidate/resume',     label: 'Resume',      icon: FileText },
  { to: '/candidate/jobs',       label: 'Browse Jobs', icon: Briefcase },
  { to: '/candidate/applications',label:'Applications', icon: Target },
  { to: '/candidate/roadmap',    label: 'Roadmap',     icon: Map },
  { to: '/candidate/interview',  label: 'Interview',   icon: Video },
  { to: '/candidate/assistant',  label: 'AI Assistant',icon: MessageSquare },
];

const RECRUITER_LINKS = [
  { to: '/recruiter/dashboard',  label: 'Dashboard',   icon: LayoutDashboard },
  { to: '/recruiter/jobs',       label: 'My Jobs',     icon: Briefcase },
  { to: '/recruiter/jobs/create',label: 'Post a Job',  icon: PlusCircle },
  { to: '/recruiter/candidates', label: 'Candidates',  icon: Users },
  { to: '/recruiter/analytics',  label: 'Analytics',   icon: BarChart3 },
];

const ADMIN_LINKS = [
  { to: '/admin/dashboard',      label: 'Dashboard',   icon: LayoutDashboard },
  { to: '/admin/users',          label: 'Users',       icon: Users },
  { to: '/admin/jobs',           label: 'Jobs',        icon: Briefcase },
  { to: '/admin/analytics',      label: 'Analytics',   icon: BarChart3 },
];

export default function Sidebar() {
  const { isCandidate, isRecruiter, isAdmin } = useAuth();
  const links = isCandidate ? CANDIDATE_LINKS : isRecruiter ? RECRUITER_LINKS : ADMIN_LINKS;

  return (
    <aside className="w-56 bg-white border-r border-gray-200 min-h-screen flex flex-col py-4 shrink-0">
      <nav className="flex-1 px-3 space-y-0.5">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-primary-50 text-primary-700'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              }`
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
