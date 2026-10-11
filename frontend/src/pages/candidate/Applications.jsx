import { useState, useEffect } from 'react';
import { applicationsAPI } from '../../services/api';
import DashboardLayout from '../../components/layout/DashboardLayout';
import { Spinner, PageHeader, EmptyState, StatusBadge } from '../../components/ui';
import { Briefcase, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';

export default function CandidateApplications() {
  const [apps, setApps]     = useState([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    applicationsAPI.list()
      .then(r => setApps(r.data))
      .catch(() => toast.error('Failed to load applications'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const withdraw = async (id) => {
    if (!confirm('Withdraw this application?')) return;
    try {
      await applicationsAPI.withdraw(id);
      toast.success('Application withdrawn.');
      setApps(prev => prev.filter(a => a.application_id !== id));
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
  };

  return (
    <DashboardLayout>
      <PageHeader title="My Applications" subtitle="Track every job you have applied to." />

      {loading ? <div className="flex justify-center py-20"><Spinner size="lg" /></div> : apps.length === 0 ? (
        <EmptyState icon={Briefcase} title="No applications yet"
          description="Browse jobs and apply to get started." />
      ) : (
        <div className="space-y-3">
          {apps.map(a => (
            <div key={a.application_id} className="card flex items-center justify-between gap-4">
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-gray-900">{a.job_title}</p>
                <p className="text-sm text-gray-500">{a.company} {a.location ? `• ${a.location}` : ''}</p>
                <p className="text-xs text-gray-400 mt-1">Applied {new Date(a.applied_at).toLocaleDateString()}</p>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge status={a.app_status} />
                {a.app_status === 'APPLIED' && (
                  <button onClick={() => withdraw(a.application_id)}
                    className="p-2 text-red-400 hover:text-red-600 hover:bg-red-50 rounded-lg">
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </DashboardLayout>
  );
}
