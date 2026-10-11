import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { jobsAPI, applicationsAPI, savedJobsAPI, matchingAPI } from '../../services/api';
import DashboardLayout from '../../components/layout/DashboardLayout';
import { Spinner, EmptyState, ScoreBadge, StatusBadge, PageHeader } from '../../components/ui';
import { Briefcase, MapPin, Search, Bookmark, Zap } from 'lucide-react';
import toast from 'react-hot-toast';

export default function CandidateJobs() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [analyzing, setAnalyzing] = useState({});
  const [applied, setApplied] = useState({});   // tracks which job IDs have been applied to

  const fetchJobs = (q = '') => {
    setLoading(true);
    jobsAPI.list({ search: q, limit: 30 })
      .then(r => setJobs(r.data))
      .catch(() => toast.error('Failed to load jobs'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchJobs(); }, []);

  const handleApply = async (job) => {
    try {
      await applicationsAPI.apply(job.id);
      toast.success(`Applied to ${job.title}!`);
      setApplied(prev => ({ ...prev, [job.id]: true }));
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Apply failed.');
    }
  };

  const handleSave = async (job) => {
    try {
      await savedJobsAPI.save(job.id);
      toast.success('Job saved!');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Save failed.');
    }
  };

  const handleMatch = async (job) => {
    setAnalyzing(prev => ({ ...prev, [job.id]: true }));
    try {
      const r = await matchingAPI.analyze(job.id);
      toast.success(`Match score: ${r.data.overall_score.toFixed(0)}%`);
      setJobs(prev => prev.map(j =>
        j.id === job.id ? { ...j, match_score: r.data.overall_score } : j
      ));
    } catch (err) {
      toast.error('Run matching failed. Make sure the job is Active.');
    } finally {
      setAnalyzing(prev => ({ ...prev, [job.id]: false }));
    }
  };

  return (
    <DashboardLayout>
      <PageHeader title="Browse Jobs" subtitle="Discover opportunities and see how well you match." />

      <div className="flex gap-3 mb-6">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-3 text-gray-400" />
          <input
            type="text"
            className="input pl-9"
            placeholder="Search by title or company..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && fetchJobs(search)}
          />
        </div>
        <button className="btn-primary" onClick={() => fetchJobs(search)}>Search</button>
      </div>

      {loading ? (
        <div className="flex justify-center py-20"><Spinner size="lg" /></div>
      ) : jobs.length === 0 ? (
        <EmptyState icon={Briefcase} title="No jobs found" description="Try a different search." />
      ) : (
        <div className="grid gap-4">
          {jobs.map(job => (
            <div key={job.id} className="card hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-semibold text-gray-900">{job.title}</h3>
                    <StatusBadge status={job.job_status} />
                    {job.match_score && <ScoreBadge score={job.match_score} />}
                  </div>
                  <p className="text-sm text-gray-600 mt-0.5">{job.company}</p>
                  <div className="flex items-center gap-4 mt-2 text-xs text-gray-500 flex-wrap">
                    {job.location && <span className="flex items-center gap-1"><MapPin size={12} />{job.location}</span>}
                    <span className="badge-gray">{job.employment_type?.replace('_',' ')}</span>
                    <span className="badge-blue">{job.experience_level}</span>
                    {job.salary_min && <span>💰 {job.salary_min}{job.salary_max ? ` – ${job.salary_max}` : '+'}</span>}
                  </div>
                  {job.ai_extracted_required_skills?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {job.ai_extracted_required_skills.slice(0, 5).map(s => (
                        <span key={s} className="badge-purple text-xs">{s}</span>
                      ))}
                      {job.ai_extracted_required_skills.length > 5 && (
                        <span className="badge-gray">+{job.ai_extracted_required_skills.length - 5}</span>
                      )}
                    </div>
                  )}
                </div>
                <div className="flex flex-col gap-2 shrink-0">
                  <button
                    onClick={() => handleMatch(job)}
                    disabled={analyzing[job.id]}
                    className="btn-secondary flex items-center gap-1 text-xs py-1.5"
                  >
                    <Zap size={12} />
                    {analyzing[job.id] ? '...' : 'Match'}
                  </button>
                  <button onClick={() => handleApply(job)}
                    disabled={!!applied[job.id]}
                    className={`text-xs py-1.5 ${applied[job.id] ? 'btn-secondary opacity-60 cursor-not-allowed' : 'btn-primary'}`}>
                    {applied[job.id] ? 'Applied ✓' : 'Apply'}
                  </button>
                  <button onClick={() => handleSave(job)} className="btn-secondary text-xs py-1.5 flex items-center gap-1">
                    <Bookmark size={12} /> Save
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </DashboardLayout>
  );
}
