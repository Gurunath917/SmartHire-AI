import { useState, useEffect } from 'react';
import { analyticsAPI } from '../../services/api';
import DashboardLayout from '../../components/layout/DashboardLayout';
import { Spinner, PageHeader, StatCard } from '../../components/ui';
import { Briefcase, Users, Star, TrendingUp } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';
import toast from 'react-hot-toast';

const COLORS = ['#2563eb','#16a34a','#d97706','#dc2626','#7c3aed','#0891b2'];

export default function RecruiterAnalytics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    analyticsAPI.recruiter()
      .then(r => setData(r.data))
      .catch(() => toast.error('Failed to load analytics'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <DashboardLayout><div className="flex justify-center py-20"><Spinner size="lg" /></div></DashboardLayout>;

  const jobStatusData = [
    { name: 'Active', value: data?.active_jobs || 0 },
    { name: 'Draft',  value: data?.draft_jobs  || 0 },
    { name: 'Closed', value: data?.closed_jobs || 0 },
  ].filter(d => d.value > 0);

  const appStatusData = Object.entries(data?.applications_by_status || {}).map(([k, v]) => ({
    name: k.replace(/_/g,' '), value: v,
  }));

  const skillData = (data?.top_applicant_skills || []).map(s => ({
    name: s.skill_name, count: s.count,
  }));

  return (
    <DashboardLayout>
      <PageHeader title="Recruitment Analytics" subtitle="Insights from your job postings and applicants." />

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard label="Total Jobs"       value={data?.total_jobs       || 0} icon={Briefcase} bg="bg-blue-50"   color="text-blue-600" />
        <StatCard label="Active Jobs"      value={data?.active_jobs      || 0} icon={TrendingUp} bg="bg-green-50"  color="text-green-600" />
        <StatCard label="Total Applicants" value={data?.total_applicants || 0} icon={Users}     bg="bg-purple-50" color="text-purple-600" />
        <StatCard label="Shortlisted"      value={data?.shortlisted      || 0} icon={Star}      bg="bg-yellow-50" color="text-yellow-600" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Job status pie */}
        {jobStatusData.length > 0 && (
          <div className="card">
            <h2 className="font-semibold text-gray-900 mb-4">Jobs by Status</h2>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={jobStatusData} cx="50%" cy="50%" outerRadius={70} dataKey="value" label>
                  {jobStatusData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Legend />
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Application status bar */}
        {appStatusData.length > 0 && (
          <div className="card">
            <h2 className="font-semibold text-gray-900 mb-4">Applications by Status</h2>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={appStatusData}>
                <XAxis dataKey="name" tick={{ fontSize: 9 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="value" fill="#2563eb" radius={[4,4,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Top skills */}
      {skillData.length > 0 && (
        <div className="card">
          <h2 className="font-semibold text-gray-900 mb-4">Top Skills Among Applicants</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={skillData} layout="vertical">
              <XAxis type="number" tick={{ fontSize: 10 }} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={110} />
              <Tooltip />
              <Bar dataKey="count" fill="#7c3aed" radius={[0,4,4,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </DashboardLayout>
  );
}
