import { useState, useEffect } from 'react';
import { interviewAPI } from '../../services/api';
import DashboardLayout from '../../components/layout/DashboardLayout';
import { Spinner, PageHeader, EmptyState, StatusBadge, Alert, ProgressBar } from '../../components/ui';
import { Video, Send, Star, ChevronRight } from 'lucide-react';
import toast from 'react-hot-toast';

// ── Setup screen ──────────────────────────────────────────────────────────────
function SetupForm({ onCreate }) {
  const [form, setForm] = useState({ target_role: '', experience_level: 'FRESHER', difficulty: 'MEDIUM', total_questions: 10 });
  const [loading, setLoading] = useState(false);

  const submit = async e => {
    e.preventDefault();
    setLoading(true);
    try {
      const r = await interviewAPI.create({ ...form, total_questions: Number(form.total_questions) });
      onCreate(r.data);
    } catch { toast.error('Failed to create interview'); }
    finally { setLoading(false); }
  };

  return (
    <div className="max-w-lg mx-auto">
      <div className="card">
        <h2 className="font-bold text-gray-900 text-lg mb-6">Start Mock Interview</h2>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="label">Target Role</label>
            <input required className="input" placeholder="AI/ML Engineer"
              value={form.target_role} onChange={e => setForm(f => ({ ...f, target_role: e.target.value }))} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Experience Level</label>
              <select className="input" value={form.experience_level} onChange={e => setForm(f => ({ ...f, experience_level: e.target.value }))}>
                {['FRESHER','JUNIOR','MID','SENIOR'].map(v => <option key={v} value={v}>{v}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Difficulty</label>
              <select className="input" value={form.difficulty} onChange={e => setForm(f => ({ ...f, difficulty: e.target.value }))}>
                {['EASY','MEDIUM','HARD'].map(v => <option key={v} value={v}>{v}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="label">Number of Questions ({form.total_questions})</label>
            <input type="range" min={3} max={20} className="w-full" value={form.total_questions}
              onChange={e => setForm(f => ({ ...f, total_questions: e.target.value }))} />
          </div>
          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? 'Generating questions...' : 'Start Interview →'}
          </button>
        </form>
      </div>
    </div>
  );
}

// ── Interview screen ──────────────────────────────────────────────────────────
function InterviewScreen({ interview, onComplete }) {
  const [current, setCurrent]   = useState(0);
  const [answers, setAnswers]   = useState({});
  const [submitting, setSub]    = useState(false);
  const [evaluated, setEvaluated] = useState(null);
  const [evaluating, setEval]   = useState(false);

  const q = interview.questions?.[current];

  const submitAnswer = async () => {
    if (!answers[q.id]?.trim()) { toast.error('Please write an answer'); return; }
    setSub(true);
    try {
      await interviewAPI.answer(interview.id, { question_id: q.id, answer_text: answers[q.id] });
      toast.success('Answer submitted!');
      if (current < interview.questions.length - 1) {
        setCurrent(c => c + 1);
      } else {
        // All answered — evaluate
        setEval(true);
        const r = await interviewAPI.evaluate(interview.id);
        setEvaluated(r.data);
        setEval(false);
        onComplete(r.data);
      }
    } catch { toast.error('Submit failed'); }
    finally { setSub(false); }
  };

  const TYPE_COLORS = { TECHNICAL: 'badge-blue', CODING: 'badge-purple', BEHAVIORAL: 'badge-green', PROJECT: 'badge-yellow' };

  if (evaluating) return (
    <div className="flex flex-col items-center justify-center py-20 gap-4">
      <Spinner size="lg" />
      <p className="text-gray-600 font-medium">Evaluating your answers...</p>
    </div>
  );

  return (
    <div className="max-w-2xl mx-auto">
      {/* Progress */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-gray-500">Question {current + 1} of {interview.questions.length}</span>
        <span className="text-sm font-medium text-primary-600">{interview.target_role}</span>
      </div>
      <ProgressBar value={current + 1} max={interview.questions.length} className="mb-6" />

      <div className="card">
        <div className="flex items-center gap-2 mb-4 flex-wrap">
          <span className={TYPE_COLORS[q?.question_type] || 'badge-gray'}>{q?.question_type}</span>
          <span className="badge-gray">{q?.difficulty}</span>
        </div>
        <p className="text-lg font-medium text-gray-900 mb-6">{q?.question_text}</p>
        <textarea
          className="input h-40 resize-none"
          placeholder="Write your answer here..."
          value={answers[q?.id] || ''}
          onChange={e => setAnswers(prev => ({ ...prev, [q.id]: e.target.value }))}
        />
        {q?.expected_topics?.length > 0 && (
          <p className="text-xs text-gray-400 mt-2">Hint: cover topics like {q.expected_topics.join(', ')}</p>
        )}
        <div className="flex items-center justify-between mt-4">
          <button disabled={current === 0} onClick={() => setCurrent(c => c - 1)} className="btn-secondary text-sm">← Previous</button>
          <button onClick={submitAnswer} disabled={submitting} className="btn-primary flex items-center gap-2 text-sm">
            <Send size={14} />
            {submitting ? 'Submitting...' : current === interview.questions.length - 1 ? 'Submit & Evaluate' : 'Submit & Next'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Results screen ────────────────────────────────────────────────────────────
function ResultsScreen({ evaluation, onNew }) {
  const score = evaluation.overall_score;
  const color = score >= 75 ? 'text-green-600' : score >= 55 ? 'text-yellow-600' : 'text-red-600';

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="card text-center">
        <p className={`text-6xl font-bold ${color}`}>{score.toFixed(0)}</p>
        <p className="text-gray-500 mt-1">Overall Score</p>
        <div className="grid grid-cols-2 gap-4 mt-4">
          <div className="bg-blue-50 rounded-lg p-3">
            <p className="text-2xl font-bold text-blue-700">{evaluation.technical_score.toFixed(0)}</p>
            <p className="text-xs text-blue-600">Technical</p>
          </div>
          <div className="bg-purple-50 rounded-lg p-3">
            <p className="text-2xl font-bold text-purple-700">{evaluation.communication_score.toFixed(0)}</p>
            <p className="text-xs text-purple-600">Communication</p>
          </div>
        </div>
      </div>

      {evaluation.summary && <Alert type={score >= 65 ? 'success' : 'warning'}>{evaluation.summary}</Alert>}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="card">
          <h3 className="font-semibold text-green-700 mb-3">✅ Strengths</h3>
          <ul className="space-y-2">
            {evaluation.strengths?.map((s, i) => <li key={i} className="text-sm text-gray-700 flex gap-2"><Star size={14} className="text-yellow-500 shrink-0 mt-0.5" />{s}</li>)}
          </ul>
        </div>
        <div className="card">
          <h3 className="font-semibold text-red-600 mb-3">⚠️ Areas to Improve</h3>
          <ul className="space-y-2">
            {evaluation.weaknesses?.map((w, i) => <li key={i} className="text-sm text-gray-700">• {w}</li>)}
          </ul>
        </div>
      </div>

      {evaluation.recommended_topics?.length > 0 && (
        <div className="card">
          <h3 className="font-semibold text-gray-900 mb-3">📚 Study These Topics</h3>
          <div className="flex flex-wrap gap-2">
            {evaluation.recommended_topics.map(t => <span key={t} className="badge-purple">{t}</span>)}
          </div>
        </div>
      )}

      <button onClick={onNew} className="btn-primary w-full">Start Another Interview</button>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function CandidateInterview() {
  const [interviews, setInterviews] = useState([]);
  const [active, setActive]         = useState(null);  // current interview
  const [evaluation, setEvaluation] = useState(null);
  const [screen, setScreen]         = useState('setup'); // setup | interview | results | history
  const [loading, setLoading]       = useState(true);

  useEffect(() => {
    interviewAPI.list()
      .then(r => setInterviews(r.data))
      .finally(() => setLoading(false));
  }, []);

  const handleCreate = interview => { setActive(interview); setScreen('interview'); };
  const handleComplete = ev => { setEvaluation(ev); setScreen('results'); };
  const handleNew = () => { setActive(null); setEvaluation(null); setScreen('setup'); };

  return (
    <DashboardLayout>
      <div className="flex items-center justify-between mb-6">
        <PageHeader title="Mock Interview" subtitle="Practice with AI-generated role-specific questions." />
        <div className="flex gap-2">
          {['setup','history'].map(s => (
            <button key={s} onClick={() => setScreen(s)}
              className={`text-sm px-3 py-1.5 rounded-lg font-medium transition-colors ${screen === s ? 'bg-primary-600 text-white' : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'}`}>
              {s === 'setup' ? 'New Interview' : 'History'}
            </button>
          ))}
        </div>
      </div>

      {screen === 'setup'     && <SetupForm onCreate={handleCreate} />}
      {screen === 'interview' && active && <InterviewScreen interview={active} onComplete={handleComplete} />}
      {screen === 'results'   && evaluation && <ResultsScreen evaluation={evaluation} onNew={handleNew} />}

      {screen === 'history' && (
        loading ? <div className="flex justify-center py-20"><Spinner size="lg" /></div> :
        interviews.length === 0 ? (
          <EmptyState icon={Video} title="No interviews yet" description="Start your first mock interview." />
        ) : (
          <div className="space-y-3">
            {interviews.map(iv => (
              <button key={iv.id} onClick={async () => {
                const r = await interviewAPI.get(iv.id);
                setActive(r.data);
                setScreen('interview');
              }} className="card w-full text-left hover:shadow-md transition-shadow flex items-center justify-between">
                <div>
                  <p className="font-semibold text-gray-900">{iv.target_role}</p>
                  <p className="text-xs text-gray-500">{iv.experience_level} • {iv.difficulty} • {iv.total_questions} questions</p>
                  {iv.overall_score && <p className="text-sm font-medium text-primary-600 mt-1">Score: {iv.overall_score.toFixed(0)}</p>}
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge status={iv.interview_status} />
                  <ChevronRight size={16} className="text-gray-400" />
                </div>
              </button>
            ))}
          </div>
        )
      )}
    </DashboardLayout>
  );
}
