import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { recruiterAPI, jobsAPI } from '../../services/api';
import DashboardLayout from '../../components/layout/DashboardLayout';
import { Spinner, PageHeader, EmptyState, StatusBadge } from '../../components/ui';
import { Briefcase, PlusCircle, Edit, Trash2, Eye, ToggleLeft, ToggleRight } from 'lucide-react';
import toast from 'react-hot-toast';

export default function RecruiterJobs() {
  const [jobs, setJobs]     = useState([]);
  const [loading, setLoading] = useState(true);

  const load = () => recruiterAPI.myJobs()
    .then(r => setJobs(r.data))
    .catch(() => toast.error('Failed to load jobs'))
    .finally(() => setLoading(false));

  useEffect(() => { load(); }, []);

  const toggleStatus = async (job) => {
    const newStatus = job.job_status === 'ACTIVE' ? 'PAUSED' : 'ACTIVE';
    try {
      await jobsAPI.setStatus(job.id, newStatus);
      toast.success(`Job ${newStatus === 'ACTIVE' ? 'activated' : 'paused'}.`);
      setJobs(prev => prev.map(j => j.id === job.id ? { ...j, job_status: newStatus } : j));
    } catch { toast.error('Status update failed.'); }
  };

  const deleteJob = async (id, title) => {
    if (!confirm(`Delete "${title}"?`)) return;
    try {
      await jobsAPI.delete(id);
      toast.success('Job deleted.');
      setJobs(prev => prev.filter(j => j.id !== id));
    } catch { toast.error('Delete failed.'); }
  };

  return (
    <DashboardLayout>
      <PageHeader
        title="My Jobs"
        subtitle="Manage all your job postings."
        action={
          <Link to="/recruiter/jobs/create" className="btn-primary flex items-center gap-2">
            <PlusCircle size={16} /> Post a Job
          </Link>
        }
      />

      {loading ? <div className="flex justify-center py-20"><Spinner size="lg" /></div>
        : jobs.length === 0 ? (
          <EmptyState icon={Briefcase} title="No jobs posted yet"
            action={<Link to="/recruiter/jobs/create" className="btn-primary">Post your first job</Link>} />
        ) : (
          <div className="space-y-3">
            {jobs.map(job => (
              <div key={job.id} className="card flex items-center justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-semibold text-gray-900">{job.title}</p>
                    <StatusBadge status={job.job_status} />
                  </div>
                  <p className="text-sm text-gray-500 mt-0.5">{job.company} {job.location ? `• ${job.location}` : ''}</p>
                  <div className="flex gap-2 mt-2 flex-wrap">
                    <span className="badge-gray">{job.employment_type?.replace('_',' ')}</span>
                    <span className="badge-blue">{job.experience_level}</span>
                    {job.ai_extracted_required_skills?.slice(0,3).map(s => (
                      <span key={s} className="badge-purple">{s}</span>
                    ))}
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button onClick={() => toggleStatus(job)} title={job.job_status === 'ACTIVE' ? 'Pause' : 'Activate'}
                    className="p-2 hover:bg-gray-100 rounded-lg text-gray-500">
                    {job.job_status === 'ACTIVE' ? <ToggleRight size={18} className="text-green-600" /> : <ToggleLeft size={18} />}
                  </button>
                  <Link to={`/recruiter/jobs/${job.id}`} className="p-2 hover:bg-gray-100 rounded-lg text-gray-500">
                    <Eye size={16} />
                  </Link>
                  <button onClick={() => deleteJob(job.id, job.title)}
                    className="p-2 hover:bg-red-50 rounded-lg text-red-400">
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
    </DashboardLayout>
  );
}
