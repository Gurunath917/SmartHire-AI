import { useState, useEffect } from 'react';
import { analyticsAPI } from '../../services/api';
import DashboardLayout from '../../components/layout/DashboardLayout';
import { Spinner, PageHeader, StatCard } from '../../components/ui';
import { Users, Briefcase, FileText, Video, Map, MessageSquare, TrendingUp, Activity } from 'lucide-react';
import toast from 'react-hot-toast';

export default function AdminDashboard() {
  const [data, setData]     = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    analyticsAPI.admin()
      .then(r => setData(r.data))
      .catch(() => toast.error('Failed to load admin data'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <DashboardLayout><div className="flex justify-center py-20"><Spinner size="lg" /></div></DashboardLayout>;

  return (
    <DashboardLayout>
      <PageHeader title="Admin Dashboard" subtitle="Platform-wide overview." />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard label="Total Users"      value={data?.total_users}      icon={Users}     bg="bg-blue-50"   color="text-blue-600" />
        <StatCard label="Candidates"       value={data?.total_candidates} icon={Users}     bg="bg-purple-50" color="text-purple-600" />
        <StatCard label="Recruiters"       value={data?.total_recruiters} icon={Users}     bg="bg-teal-50"   color="text-teal-600" />
        <StatCard label="Active Jobs"      value={data?.active_jobs}      icon={Briefcase} bg="bg-green-50"  color="text-green-600" />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard label="Total Jobs"       value={data?.total_jobs}         icon={Briefcase}    bg="bg-gray-50"   color="text-gray-600" />
        <StatCard label="Applications"     value={data?.total_applications} icon={FileText}     bg="bg-orange-50" color="text-orange-600" />
        <StatCard label="Interviews"       value={data?.total_interviews}   icon={Video}        bg="bg-pink-50"   color="text-pink-600" />
        <StatCard label="Roadmaps"         value={data?.total_roadmaps}     icon={Map}          bg="bg-indigo-50" color="text-indigo-600" />
      </div>

      {/* 7-day activity */}
      <div className="card mb-6">
        <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Activity size={16} /> Last 7 Days
        </h2>
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: 'New Users',        value: data?.new_users_7d },
            { label: 'New Jobs',         value: data?.new_jobs_7d },
            { label: 'New Applications', value: data?.new_applications_7d },
          ].map(item => (
            <div key={item.label} className="text-center p-4 bg-gray-50 rounded-lg">
              <p className="text-3xl font-bold text-primary-600">{item.value ?? 0}</p>
              <p className="text-xs text-gray-500 mt-1">{item.label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* AI usage */}
      <div className="card">
        <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <TrendingUp size={16} /> AI Feature Usage
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <StatCard label="Parsed Resumes"      value={data?.parsed_resumes}       icon={FileText}     bg="bg-blue-50"   color="text-blue-600" />
          <StatCard label="Generated Roadmaps"  value={data?.generated_roadmaps}   icon={Map}          bg="bg-green-50"  color="text-green-600" />
          <StatCard label="Evaluated Interviews" value={data?.evaluated_interviews} icon={Video}        bg="bg-purple-50" color="text-purple-600" />
          <StatCard label="Chat Sessions"        value={data?.total_chat_sessions}  icon={MessageSquare} bg="bg-yellow-50" color="text-yellow-600" />
        </div>
      </div>
    </DashboardLayout>
  );
}
