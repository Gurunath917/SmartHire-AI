import { useState, useEffect } from 'react';
import { recruiterAPI, matchingAPI } from '../../services/api';
import DashboardLayout from '../../components/layout/DashboardLayout';
import { Spinner, PageHeader, EmptyState, ScoreBadge } from '../../components/ui';
import { Users, Zap } from 'lucide-react';
import toast from 'react-hot-toast';

export default function RecruiterCandidates() {
  const [jobs, setJobs]       = useState([]);
  const [selectedJob, setSel] = useState('');
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [fetching, setFetch]  = useState(false);

  useEffect(() => {
    recruiterAPI.myJobs({ status: 'ACTIVE' })
      .then(r => setJobs(r.data))
      .finally(() => setLoading(false));
  }, []);

  const loadMatches = async (jobId) => {
    setSel(jobId);
    if (!jobId) { setMatches([]); return; }
    setFetch(true);
    try {
      const r = await matchingAPI.jobMatches(jobId);
      setMatches(r.data);
    } catch { toast.error('Failed to load matches'); }
    finally { setFetch(false); }
  };

  return (
    <DashboardLayout>
      <PageHeader title="Candidates" subtitle="View AI-ranked candidates for each of your active jobs." />

      <div className="mb-6">
        <label className="label">Select a Job</label>
        <select className="input max-w-sm" value={selectedJob} onChange={e => loadMatches(e.target.value)}>
          <option value="">-- Select a job --</option>
          {jobs.map(j => <option key={j.id} value={j.id}>{j.title}</option>)}
        </select>
      </div>

      {loading ? <div className="flex justify-center py-20"><Spinner size="lg" /></div>
        : !selectedJob ? (
          <EmptyState icon={Users} title="Select a job above" description="Choose an active job to see ranked candidates." />
        ) : fetching ? (
          <div className="flex justify-center py-20"><Spinner size="lg" /></div>
        ) : matches.length === 0 ? (
          <EmptyState icon={Zap} title="No match data yet"
            description="Candidates need to run matching against this job first." />
        ) : (
          <div className="space-y-3">
            {matches.map((m, i) => (
              <div key={m.candidate_profile_id} className="card flex items-center gap-4">
                <div className="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center text-primary-700 font-bold shrink-0">
                  #{i + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-gray-900">{m.full_name}</p>
                  <p className="text-sm text-gray-500">{m.email} {m.location ? `• ${m.location}` : ''}</p>
                  <div className="flex gap-3 mt-1 text-xs text-gray-500 flex-wrap">
                    {m.skill_match_score != null && <span>Skills {m.skill_match_score.toFixed(0)}%</span>}
                    {m.experience_match_score != null && <span>Exp {m.experience_match_score.toFixed(0)}%</span>}
                    {m.education_match_score != null && <span>Edu {m.education_match_score.toFixed(0)}%</span>}
                    {m.years_of_experience != null && <span>{m.years_of_experience} yrs</span>}
                  </div>
                  {m.explanation?.shap_positive?.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {m.explanation.shap_positive.slice(0,3).map(f => (
                        <span key={f.feature} className="badge-green text-xs">+{f.feature.replace(/_/g,' ')}</span>
                      ))}
                      {m.explanation?.shap_negative?.slice(0,2).map(f => (
                        <span key={f.feature} className="badge-red text-xs">-{f.feature.replace(/_/g,' ')}</span>
                      ))}
                    </div>
                  )}
                </div>
                <ScoreBadge score={m.overall_score} />
              </div>
            ))}
          </div>
        )
      }
    </DashboardLayout>
  );
}
