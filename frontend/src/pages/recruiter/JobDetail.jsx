import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { jobsAPI, matchingAPI, applicationsAPI } from '../../services/api';
import DashboardLayout from '../../components/layout/DashboardLayout';
import { Spinner, PageHeader, EmptyState, StatusBadge, ScoreBadge, Alert } from '../../components/ui';
import { Users, Zap, CheckCircle, XCircle } from 'lucide-react';
import toast from 'react-hot-toast';

export default function RecruiterJobDetail() {
  const { id }               = useParams();
  const [job, setJob]        = useState(null);
  const [applicants, setApp] = useState([]);
  const [matches, setMatches]= useState([]);
  const [loading, setLoading]= useState(true);
  const [tab, setTab]        = useState('applicants');

  useEffect(() => {
    Promise.all([
      jobsAPI.get(id),
      jobsAPI.applicants(id).catch(() => ({ data: [] })),
      matchingAPI.jobMatches(id).catch(() => ({ data: [] })),
    ]).then(([j, a, m]) => {
      setJob(j.data); setApp(a.data); setMatches(m.data);
    }).finally(() => setLoading(false));
  }, [id]);

  const setStatus = async status => {
    try {
      await jobsAPI.setStatus(id, status);
      setJob(prev => ({ ...prev, job_status: status }));
      toast.success(`Job ${status.toLowerCase()}.`);
    } catch { toast.error('Status update failed.'); }
  };

  const updateAppStatus = async (appId, status) => {
    try {
      await applicationsAPI.setStatus(appId, status);
      setApp(prev => prev.map(a => a.application_id === appId ? { ...a, app_status: status } : a));
      toast.success('Status updated.');
    } catch { toast.error('Update failed.'); }
  };

  if (loading) return <DashboardLayout><div className="flex justify-center py-20"><Spinner size="lg" /></div></DashboardLayout>;
  if (!job) return <DashboardLayout><Alert type="error">Job not found.</Alert></DashboardLayout>;

  return (
    <DashboardLayout>
      <div className="flex items-start justify-between mb-6 flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-2xl font-bold text-gray-900">{job.title}</h1>
            <StatusBadge status={job.job_status} />
          </div>
          <p className="text-gray-500 text-sm mt-1">{job.company} {job.location ? `• ${job.location}` : ''}</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          {job.job_status !== 'ACTIVE'  && <button onClick={() => setStatus('ACTIVE')}  className="btn-primary text-sm">Activate</button>}
          {job.job_status === 'ACTIVE'  && <button onClick={() => setStatus('PAUSED')}  className="btn-secondary text-sm">Pause</button>}
          {job.job_status !== 'CLOSED'  && <button onClick={() => setStatus('CLOSED')}  className="btn-danger text-sm">Close</button>}
        </div>
      </div>

      {/* Required skills */}
      {job.ai_extracted_required_skills?.length > 0 && (
        <div className="card mb-6">
          <h3 className="font-medium text-gray-700 mb-3">Required Skills</h3>
          <div className="flex flex-wrap gap-2">
            {job.ai_extracted_required_skills.map(s => <span key={s} className="badge-green">{s}</span>)}
          </div>
          {job.ai_extracted_preferred_skills?.length > 0 && (
            <>
              <h3 className="font-medium text-gray-700 mt-3 mb-2">Preferred Skills</h3>
              <div className="flex flex-wrap gap-2">
                {job.ai_extracted_preferred_skills.map(s => <span key={s} className="badge-yellow">{s}</span>)}
              </div>
            </>
          )}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 mb-4">
        {['applicants','matches'].map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${tab === t ? 'bg-primary-600 text-white' : 'bg-white border border-gray-300 text-gray-700'}`}>
            {t === 'applicants' ? `Applicants (${applicants.length})` : `AI Ranked (${matches.length})`}
          </button>
        ))}
      </div>

      {tab === 'applicants' && (
        applicants.length === 0 ? <EmptyState icon={Users} title="No applicants yet" description="Share the job to attract candidates." /> : (
          <div className="space-y-3">
            {applicants.map(a => (
              <div key={a.application_id} className="card flex items-center justify-between gap-4">
                <div>
                  <p className="font-semibold text-gray-900">{a.full_name}</p>
                  <p className="text-sm text-gray-500">{a.email} {a.location ? `• ${a.location}` : ''}</p>
                  {a.years_of_experience != null && <p className="text-xs text-gray-400">{a.years_of_experience} yrs exp</p>}
                </div>
                <div className="flex items-center gap-2 flex-wrap justify-end">
                  <StatusBadge status={a.app_status} />
                  <select className="text-xs border border-gray-300 rounded-lg px-2 py-1"
                    value={a.app_status}
                    onChange={e => updateAppStatus(a.application_id, e.target.value)}>
                    {['UNDER_REVIEW','SHORTLISTED','INTERVIEW_SCHEDULED','REJECTED','OFFERED'].map(s =>
                      <option key={s} value={s}>{s.replace(/_/g,' ')}</option>
                    )}
                  </select>
                </div>
              </div>
            ))}
          </div>
        )
      )}

      {tab === 'matches' && (
        matches.length === 0 ? (
          <EmptyState icon={Zap} title="No match scores yet"
            description="Candidates need to run matching against this job first." />
        ) : (
          <div className="space-y-3">
            {matches.map((m, i) => (
              <div key={m.candidate_profile_id} className="card flex items-center gap-4">
                <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center text-primary-700 font-bold text-sm shrink-0">
                  {i + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-gray-900">{m.full_name}</p>
                  <p className="text-sm text-gray-500">{m.email}</p>
                  <div className="flex gap-3 mt-1 text-xs text-gray-500 flex-wrap">
                    {m.skill_match_score != null && <span>Skills: {m.skill_match_score.toFixed(0)}%</span>}
                    {m.experience_match_score != null && <span>Exp: {m.experience_match_score.toFixed(0)}%</span>}
                  </div>
                </div>
                <ScoreBadge score={m.overall_score} />
              </div>
            ))}
          </div>
        )
      )}
    </DashboardLayout>
  );
}
