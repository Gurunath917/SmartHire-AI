import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { analyticsAPI } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import DashboardLayout from '../../components/layout/DashboardLayout';
import { Spinner, StatCard, ProgressBar, SkillBadge, ScoreBadge, StatusBadge, EmptyState } from '../../components/ui';
import { Briefcase, FileText, Target, Map, Video, Star, TrendingUp, Award, User } from 'lucide-react';
import toast from 'react-hot-toast';

export default function CandidateDashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    analyticsAPI.candidate()
      .then(r => setData(r.data))
      .catch(() => toast.error('Failed to load dashboard data'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <DashboardLayout><div className="flex justify-center py-20"><Spinner size="lg" /></div></DashboardLayout>;

  return (
    <DashboardLayout>
      {/* Welcome */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Welcome back, {user?.full_name?.split(' ')[0]} 👋</h1>
        <p className="text-gray-500 text-sm mt-1">Here's your career progress at a glance.</p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard label="Profile Complete" value={`${data?.profile_completion_pct || 0}%`} icon={User} bg="bg-blue-50" color="text-blue-600" />
        <StatCard label="Resume Score" value={data?.resume_ats_score ? `${data.resume_ats_score}%` : '—'} icon={FileText} bg="bg-green-50" color="text-green-600" />
        <StatCard label="Job Matches" value={data?.total_matches || 0} icon={Target} bg="bg-purple-50" color="text-purple-600" />
        <StatCard label="Applications" value={data?.total_applications || 0} icon={Briefcase} bg="bg-orange-50" color="text-orange-600" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Profile completion */}
        <div className="card">
          <h2 className="font-semibold text-gray-900 mb-4">Profile Completion</h2>
          <ProgressBar value={data?.profile_completion_pct || 0} color="bg-primary-500" className="mb-2" />
          <p className="text-sm text-gray-500">{data?.profile_completion_pct || 0}% complete</p>
          <Link to="/candidate/profile" className="btn-primary mt-4 text-xs inline-block py-1.5 px-3">
            Complete Profile →
          </Link>
        </div>

        {/* Top Skills */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900">My Skills</h2>
            <span className="text-xs text-gray-500">{data?.total_skills || 0} total</span>
          </div>
          {data?.top_skills?.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {data.top_skills.map(s => (
                <SkillBadge key={s.skill_name} skill_name={s.skill_name} category={s.category} />
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500">
              Upload your resume to extract skills automatically.
              <Link to="/candidate/resume" className="text-primary-600 ml-1">Upload now →</Link>
            </p>
          )}
        </div>

        {/* Top Job Matches */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900">Top Matches</h2>
            <Link to="/candidate/jobs" className="text-xs text-primary-600 hover:underline">View all</Link>
          </div>
          {data?.top_matches?.length > 0 ? (
            <div className="space-y-3">
              {data.top_matches.map(m => (
                <div key={m.job_id} className="flex items-center justify-between">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{m.job_title}</p>
                    <p className="text-xs text-gray-500">{m.company}</p>
                  </div>
                  <ScoreBadge score={m.overall_score} />
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500">
              Browse jobs and run matching to see your scores.
              <Link to="/candidate/jobs" className="text-primary-600 ml-1">Browse →</Link>
            </p>
          )}
        </div>

        {/* Recent Applications */}
        <div className="card lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900">Recent Applications</h2>
            <Link to="/candidate/applications" className="text-xs text-primary-600 hover:underline">View all</Link>
          </div>
          {data?.recent_applications?.length > 0 ? (
            <div className="space-y-3">
              {data.recent_applications.map(a => (
                <div key={a.job_id} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{a.job_title}</p>
                    <p className="text-xs text-gray-500">{a.company}</p>
                  </div>
                  <StatusBadge status={a.app_status} />
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={Briefcase}
              title="No applications yet"
              description="Apply to jobs to track them here."
              action={<Link to="/candidate/jobs" className="btn-primary text-sm py-1.5">Browse Jobs</Link>}
            />
          )}
        </div>

        {/* Interview Scores */}
        <div className="card">
          <h2 className="font-semibold text-gray-900 mb-4">Interview Performance</h2>
          {data?.avg_interview_score ? (
            <div className="text-center py-4">
              <p className="text-4xl font-bold text-primary-600">{data.avg_interview_score}</p>
              <p className="text-sm text-gray-500 mt-1">Average Score</p>
              <ProgressBar value={data.avg_interview_score} className="mt-3" />
            </div>
          ) : (
            <EmptyState
              icon={Video}
              title="No interviews yet"
              description="Practice with AI mock interviews."
              action={<Link to="/candidate/interview" className="btn-primary text-sm py-1.5">Start Interview</Link>}
            />
          )}
        </div>
      </div>

      {/* Roadmaps + quick links */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
        {[
          { label: 'Active Roadmaps', value: data?.active_roadmaps || 0, to: '/candidate/roadmap', icon: Map, color: 'text-teal-600', bg: 'bg-teal-50' },
          { label: 'Completed Roadmaps', value: data?.completed_roadmaps || 0, to: '/candidate/roadmap', icon: Award, color: 'text-green-600', bg: 'bg-green-50' },
          { label: 'Saved Jobs', value: data?.saved_jobs_count || 0, to: '/candidate/jobs', icon: Star, color: 'text-yellow-600', bg: 'bg-yellow-50' },
          { label: 'AI Sessions', value: '—', to: '/candidate/assistant', icon: TrendingUp, color: 'text-purple-600', bg: 'bg-purple-50' },
        ].map(({ label, value, to, icon, color, bg }) => (
          <Link to={to} key={label} className="card hover:shadow-md transition-shadow cursor-pointer">
            <StatCard label={label} value={value} icon={icon} color={color} bg={bg} />
          </Link>
        ))}
      </div>
    </DashboardLayout>
  );
}
