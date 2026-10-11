import { useState, useEffect } from 'react';
import { roadmapAPI, matchingAPI } from '../../services/api';
import DashboardLayout from '../../components/layout/DashboardLayout';
import { Spinner, PageHeader, EmptyState, ProgressBar, StatusBadge, Alert } from '../../components/ui';
import { Map, ChevronDown, ChevronUp, CheckCircle, Circle, Zap } from 'lucide-react';
import toast from 'react-hot-toast';

function WeekCard({ week, roadmapId, onToggle }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={`border rounded-xl overflow-hidden transition-all ${week.is_completed ? 'border-green-300 bg-green-50' : 'border-gray-200 bg-white'}`}>
      <button className="w-full flex items-center justify-between p-4 text-left"
        onClick={() => setOpen(o => !o)}>
        <div className="flex items-center gap-3">
          <button onClick={e => { e.stopPropagation(); onToggle(week.week, !week.is_completed); }}
            className="shrink-0">
            {week.is_completed
              ? <CheckCircle size={20} className="text-green-600" />
              : <Circle size={20} className="text-gray-400" />}
          </button>
          <div>
            <span className="text-xs font-medium text-gray-500">Week {week.week}</span>
            <p className="font-semibold text-gray-900">{week.topic}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">{week.time_estimate}</span>
          {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-3 border-t border-gray-100 pt-3">
          {week.objectives?.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-500 mb-1">Objectives</p>
              <ul className="list-disc list-inside space-y-1">
                {week.objectives.map((o, i) => <li key={i} className="text-sm text-gray-700">{o}</li>)}
              </ul>
            </div>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {week.practice_task && (
              <div className="bg-blue-50 rounded-lg p-3">
                <p className="text-xs font-medium text-blue-700 mb-1">Practice Task</p>
                <p className="text-sm text-blue-900">{week.practice_task}</p>
              </div>
            )}
            {week.project_task && (
              <div className="bg-purple-50 rounded-lg p-3">
                <p className="text-xs font-medium text-purple-700 mb-1">Project Task</p>
                <p className="text-sm text-purple-900">{week.project_task}</p>
              </div>
            )}
          </div>
          {week.resources?.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-500 mb-1">Resources</p>
              <div className="flex flex-wrap gap-2">
                {week.resources.map((r, i) => (
                  <span key={i} className="badge-blue text-xs">{r}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function CandidateRoadmap() {
  const [roadmaps, setRoadmaps] = useState([]);
  const [active, setActive]     = useState(null);
  const [loading, setLoading]   = useState(true);
  const [generating, setGen]    = useState(false);
  const [form, setForm]         = useState({ target_role: '', missing_skills: '' });

  const load = () => roadmapAPI.list()
    .then(r => { setRoadmaps(r.data); if (r.data[0]) loadFull(r.data[0].id); })
    .finally(() => setLoading(false));

  const loadFull = id => roadmapAPI.get(id).then(r => setActive(r.data));

  useEffect(() => { load(); }, []);

  const generate = async e => {
    e.preventDefault();
    if (!form.target_role || !form.missing_skills) { toast.error('Fill in both fields'); return; }
    setGen(true);
    try {
      const skills = form.missing_skills.split(',').map(s => s.trim()).filter(Boolean);
      const r = await roadmapAPI.generate({ target_role: form.target_role, missing_skills: skills });
      setActive(r.data);
      setRoadmaps(prev => [{ id: r.data.id, target_role: r.data.target_role, total_weeks: r.data.total_weeks, roadmap_status: r.data.roadmap_status, created_at: r.data.created_at }, ...prev]);
      toast.success(`Roadmap generated — ${r.data.total_weeks} weeks!`);
    } catch (err) { toast.error(err.response?.data?.detail || 'Generation failed'); }
    finally { setGen(false); }
  };

  const toggleWeek = async (weekNum, done) => {
    try {
      const r = await roadmapAPI.updateProgress(active.id, weekNum, done);
      setActive(r.data);
    } catch { toast.error('Update failed'); }
  };

  const completedWeeks = active?.roadmap_data?.filter(w => w.is_completed).length || 0;
  const totalWeeks     = active?.total_weeks || 0;

  return (
    <DashboardLayout>
      <PageHeader title="Learning Roadmap" subtitle="Personalized week-by-week plan to close your skill gaps." />

      {/* Generate form */}
      <div className="card mb-6">
        <h2 className="font-semibold text-gray-900 mb-4">Generate a New Roadmap</h2>
        <form onSubmit={generate} className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="sm:col-span-1">
            <label className="label">Target Role</label>
            <input className="input" placeholder="AI/ML Engineer"
              value={form.target_role} onChange={e => setForm(f => ({ ...f, target_role: e.target.value }))} />
          </div>
          <div className="sm:col-span-1">
            <label className="label">Missing Skills (comma-separated)</label>
            <input className="input" placeholder="PyTorch, Docker, AWS"
              value={form.missing_skills} onChange={e => setForm(f => ({ ...f, missing_skills: e.target.value }))} />
          </div>
          <div className="flex items-end">
            <button type="submit" disabled={generating} className="btn-primary flex items-center gap-2 w-full justify-center">
              <Zap size={14} /> {generating ? 'Generating...' : 'Generate'}
            </button>
          </div>
        </form>
        <Alert type="info" className="mt-3">
          <span className="text-xs">Tip: Run skill gap analysis on a job first to get your missing skills automatically.</span>
        </Alert>
      </div>

      {loading ? <div className="flex justify-center py-20"><Spinner size="lg" /></div> : (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* List of roadmaps */}
          {roadmaps.length > 0 && (
            <div className="lg:col-span-1">
              <h3 className="font-medium text-gray-700 mb-3 text-sm">My Roadmaps</h3>
              <div className="space-y-2">
                {roadmaps.map(rm => (
                  <button key={rm.id} onClick={() => loadFull(rm.id)}
                    className={`w-full text-left p-3 rounded-lg border transition-colors text-sm ${active?.id === rm.id ? 'border-primary-400 bg-primary-50' : 'border-gray-200 bg-white hover:bg-gray-50'}`}>
                    <p className="font-medium text-gray-900 truncate">{rm.target_role}</p>
                    <p className="text-xs text-gray-500">{rm.total_weeks} weeks</p>
                    <StatusBadge status={rm.roadmap_status} />
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Active roadmap */}
          <div className={roadmaps.length > 0 ? 'lg:col-span-3' : 'lg:col-span-4'}>
            {active && active.roadmap_data?.length > 0 ? (
              <>
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="font-bold text-gray-900 text-lg">{active.target_role}</h2>
                    <p className="text-sm text-gray-500">{completedWeeks}/{totalWeeks} weeks completed</p>
                  </div>
                  <StatusBadge status={active.roadmap_status} />
                </div>
                <ProgressBar value={completedWeeks} max={totalWeeks || 1} color="bg-green-500" className="mb-6" />
                <div className="space-y-3">
                  {active.roadmap_data.map(week => (
                    <WeekCard key={week.week} week={week} roadmapId={active.id} onToggle={toggleWeek} />
                  ))}
                </div>
              </>
            ) : (
              <EmptyState icon={Map} title="No roadmap selected"
                description="Generate a roadmap using the form above." />
            )}
          </div>
        </div>
      )}
    </DashboardLayout>
  );
}
