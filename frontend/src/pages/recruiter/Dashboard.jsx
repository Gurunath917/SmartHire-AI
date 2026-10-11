import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { analyticsAPI } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import DashboardLayout from '../../components/layout/DashboardLayout';
import { Spinner, StatCard, EmptyState, StatusBadge, PageHeader } from '../../components/ui';
import { Briefcase, Users, Star, TrendingUp, PlusCircle } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import toast from 'react-hot-toast';

export default function RecruiterDashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    analyticsAPI.recruiter()
      .then(r => setData(r.data))
      .catch(() => toast.error('Failed to load dashboard'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <DashboardLayout><div className="flex justify-center py-20"><Spinner size="lg" /></div></DashboardLayout>;

  const chartData = data?.jobs_with_stats?.map(j => ({
    name: j.job_title.slice(0, 15) + '...',
    applicants: j.applicant_count,
  })) || [];

  return (
    <DashboardLayout>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Recruiter Dashboard</h1>
          <p className="text-gray-500 text-sm mt-1">{data?.company_name || user?.full_name}</p>
        </div>
        <Link to="/recruiter/jobs/create" className="btn-primary flex items-center gap-2">
          <PlusCircle size={16} /> Post a Job
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard label="Total Jobs" value={data?.total_jobs || 0} icon={Briefcase} bg="bg-blue-50" color="text-blue-600" />
        <StatCard label="Active Jobs" value={data?.active_jobs || 0} icon={TrendingUp} bg="bg-green-50" color="text-green-600" />
        <StatCard label="Total Applicants" value={data?.total_applicants || 0} icon={Users} bg="bg-purple-50" color="text-purple-600" />
        <StatCard label="Shortlisted" value={data?.shortlisted || 0} icon={Star} bg="bg-yellow-50" color="text-yellow-600" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Applications by status */}
        <div className="card">
          <h2 className="font-semibold text-gray-900 mb-4">Applications by Status</h2>
          {Object.keys(data?.applications_by_status || {}).length > 0 ? (
            <div className="space-y-2">
              {Object.entries(data.applications_by_status).map(([status, count]) => (
                <div key={status} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                  <StatusBadge status={status} />
                  <span className="font-semibold text-gray-900">{count}</span>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState icon={Users} title="No applications yet" description="Post and activate jobs to receive applicants." />
          )}
        </div>

        {/* Applicants per job chart */}
        <div className="card">
          <h2 className="font-semibold text-gray-900 mb-4">Applicants per Job</h2>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={chartData}>
                <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="applicants" fill="#2563eb" radius={[4,4,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState icon={Briefcase} title="No data yet" description="Create jobs and get applicants first." />
          )}
        </div>
      </div>

      {/* Top skills among applicants */}
      {data?.top_applicant_skills?.length > 0 && (
        <div className="card mb-6">
          <h2 className="font-semibold text-gray-900 mb-4">Top Skills Among Applicants</h2>
          <div className="flex flex-wrap gap-2">
            {data.top_applicant_skills.map(s => (
              <span key={s.skill_name} className="badge-purple">
                {s.skill_name} ({s.count})
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Jobs table */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-gray-900">My Jobs</h2>
          <Link to="/recruiter/jobs" className="text-xs text-primary-600 hover:underline">View all</Link>
        </div>
        {data?.jobs_with_stats?.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b border-gray-200">
                  <th className="pb-2 font-medium">Job Title</th>
                  <th className="pb-2 font-medium">Status</th>
                  <th className="pb-2 font-medium">Applicants</th>
                  <th className="pb-2 font-medium">Avg Match</th>
                </tr>
              </thead>
              <tbody>
                {data.jobs_with_stats.map(j => (
                  <tr key={j.job_id} className="border-b border-gray-100 last:border-0 hover:bg-gray-50">
                    <td className="py-2.5">
                      <Link to={`/recruiter/jobs/${j.job_id}`} className="font-medium text-gray-900 hover:text-primary-600">
                        {j.job_title}
                      </Link>
                    </td>
                    <td className="py-2.5"><StatusBadge status={j.job_status} /></td>
                    <td className="py-2.5 text-gray-700">{j.applicant_count}</td>
                    <td className="py-2.5 text-gray-700">{j.avg_match_score ? `${j.avg_match_score}%` : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon={Briefcase}
            title="No jobs posted yet"
            action={<Link to="/recruiter/jobs/create" className="btn-primary text-sm">Post your first job</Link>}
          />
        )}
      </div>
    </DashboardLayout>
  );
}
