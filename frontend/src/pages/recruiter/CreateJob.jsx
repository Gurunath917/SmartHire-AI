import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { jobsAPI } from '../../services/api';
import DashboardLayout from '../../components/layout/DashboardLayout';
import { PageHeader, Alert } from '../../components/ui';
import { Zap, Save } from 'lucide-react';
import toast from 'react-hot-toast';

export default function CreateJob() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    title: '', company: '', location: '', is_remote: false,
    employment_type: 'FULL_TIME', experience_level: 'MID',
    salary_min: '', salary_max: '',
    description: '', responsibilities: '', education_requirements: '',
    required_skills: [], preferred_skills: [],
  });
  const [analyzed, setAnalyzed]   = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [saving, setSaving]       = useState(false);

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const analyze = async () => {
    if (form.description.length < 50) { toast.error('Description must be at least 50 characters.'); return; }
    setAnalyzing(true);
    try {
      const r = await jobsAPI.analyze(form.description);
      setAnalyzed(r.data);
      setForm(f => ({
        ...f,
        required_skills: r.data.required_skills || [],
        preferred_skills: r.data.preferred_skills || [],
      }));
      toast.success('AI analysis complete!');
    } catch { toast.error('Analysis failed.'); }
    finally { setAnalyzing(false); }
  };

  const submit = async e => {
    e.preventDefault();
    setSaving(true);
    try {
      const r = await jobsAPI.create(form);
      toast.success('Job created as Draft!');
      navigate(`/recruiter/jobs/${r.data.id}`);
    } catch (err) { toast.error(err.response?.data?.detail || 'Create failed.'); }
    finally { setSaving(false); }
  };

  const Field = ({ label, name, type='text', required=false, placeholder='' }) => (
    <div>
      <label className="label">{label}{required && <span className="text-red-500 ml-1">*</span>}</label>
      <input type={type} required={required} className="input" placeholder={placeholder}
        value={form[name] || ''} onChange={e => set(name, e.target.value)} />
    </div>
  );

  return (
    <DashboardLayout>
      <PageHeader title="Post a New Job" subtitle="Fill in the details and let AI extract the skill requirements." />

      <form onSubmit={submit} className="space-y-6">
        {/* Basic info */}
        <div className="card">
          <h2 className="font-semibold text-gray-900 mb-4">Job Details</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Job Title" name="title" required placeholder="AI/ML Engineer" />
            <Field label="Company" name="company" required placeholder="TechCorp" />
            <Field label="Location" name="location" placeholder="Bangalore, India" />
            <div>
              <label className="label">Employment Type</label>
              <select className="input" value={form.employment_type} onChange={e => set('employment_type', e.target.value)}>
                {['FULL_TIME','PART_TIME','CONTRACT','INTERNSHIP','FREELANCE'].map(v => <option key={v} value={v}>{v.replace('_',' ')}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Experience Level</label>
              <select className="input" value={form.experience_level} onChange={e => set('experience_level', e.target.value)}>
                {['FRESHER','JUNIOR','MID','SENIOR','LEAD','MANAGER'].map(v => <option key={v} value={v}>{v}</option>)}
              </select>
            </div>
            <div className="flex gap-2">
              <div className="flex-1"><Field label="Salary Min" name="salary_min" placeholder="12 LPA" /></div>
              <div className="flex-1"><Field label="Salary Max" name="salary_max" placeholder="20 LPA" /></div>
            </div>
            <div className="flex items-center gap-2 col-span-full">
              <input type="checkbox" id="remote" checked={form.is_remote}
                onChange={e => set('is_remote', e.target.checked)} className="w-4 h-4" />
              <label htmlFor="remote" className="text-sm font-medium text-gray-700">Remote / Work from Home</label>
            </div>
          </div>
        </div>

        {/* Description + AI analyze */}
        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <label className="font-semibold text-gray-900">Job Description <span className="text-red-500">*</span></label>
            <button type="button" onClick={analyze} disabled={analyzing}
              className="btn-secondary text-xs flex items-center gap-1 py-1.5">
              <Zap size={12} /> {analyzing ? 'Analyzing...' : 'AI Analyze'}
            </button>
          </div>
          <textarea required className="input h-40 resize-none"
            placeholder="Describe the role, responsibilities, and requirements..."
            value={form.description} onChange={e => set('description', e.target.value)} />

          {analyzed && (
            <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
              <p className="text-sm font-semibold text-blue-800 mb-2">AI Extracted Requirements</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-xs font-medium text-gray-600 mb-1">Required Skills</p>
                  <div className="flex flex-wrap gap-1">
                    {analyzed.required_skills?.map(s => <span key={s} className="badge-green">{s}</span>)}
                  </div>
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-600 mb-1">Preferred Skills</p>
                  <div className="flex flex-wrap gap-1">
                    {analyzed.preferred_skills?.map(s => <span key={s} className="badge-yellow">{s}</span>)}
                  </div>
                </div>
              </div>
              {analyzed.experience_years && <p className="text-xs text-gray-600 mt-2">Experience: {analyzed.experience_years}</p>}
              <Alert type="info" className="mt-2">
                <span className="text-xs">Review and edit skills above before saving.</span>
              </Alert>
            </div>
          )}
        </div>

        {/* Additional fields */}
        <div className="card">
          <h2 className="font-semibold text-gray-900 mb-4">Additional Requirements</h2>
          <div className="space-y-3">
            <div>
              <label className="label">Responsibilities</label>
              <textarea className="input h-28 resize-none" placeholder="Key responsibilities..."
                value={form.responsibilities} onChange={e => set('responsibilities', e.target.value)} />
            </div>
            <div>
              <label className="label">Education Requirements</label>
              <input className="input" placeholder="B.Tech in CS or equivalent"
                value={form.education_requirements} onChange={e => set('education_requirements', e.target.value)} />
            </div>
          </div>
        </div>

        <button type="submit" disabled={saving} className="btn-primary flex items-center gap-2">
          <Save size={16} /> {saving ? 'Saving...' : 'Create Job (Draft)'}
        </button>
      </form>
    </DashboardLayout>
  );
}
