import { useState, useEffect } from 'react';
import { candidateAPI } from '../../services/api';
import DashboardLayout from '../../components/layout/DashboardLayout';
import { Spinner, PageHeader, Alert, ProgressBar } from '../../components/ui';
import { Save, User } from 'lucide-react';
import toast from 'react-hot-toast';

export default function CandidateProfile() {
  const [profile, setProfile] = useState(null);
  const [form, setForm]       = useState({});
  const [loading, setLoading] = useState(true);
  const [saving,  setSaving]  = useState(false);

  useEffect(() => {
    candidateAPI.getProfile()
      .then(r => { setProfile(r.data); setForm(r.data); })
      .catch(() => toast.error('Failed to load profile'))
      .finally(() => setLoading(false));
  }, []);

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const handleSubmit = async e => {
    e.preventDefault();
    setSaving(true);
    try {
      const { data } = await candidateAPI.updateProfile({
        phone: form.phone, location: form.location,
        linkedin_url: form.linkedin_url, github_url: form.github_url,
        portfolio_url: form.portfolio_url, bio: form.bio,
        degree: form.degree, branch: form.branch,
        institution: form.institution, cgpa: form.cgpa ? Number(form.cgpa) : null,
        graduation_year: form.graduation_year ? Number(form.graduation_year) : null,
        years_of_experience: form.years_of_experience ? Number(form.years_of_experience) : null,
        current_company: form.current_company, current_job_title: form.current_job_title,
        expected_salary: form.expected_salary,
        target_roles: form.target_roles,
      });
      setProfile(data);
      toast.success('Profile updated!');
    } catch { toast.error('Update failed.'); }
    finally { setSaving(false); }
  };

  if (loading) return <DashboardLayout><div className="flex justify-center py-20"><Spinner size="lg" /></div></DashboardLayout>;

  const Field = ({ label, name, type = 'text', placeholder }) => (
    <div>
      <label className="label">{label}</label>
      <input type={type} className="input" placeholder={placeholder}
        value={form[name] || ''}
        onChange={e => set(name, e.target.value)} />
    </div>
  );

  return (
    <DashboardLayout>
      <PageHeader title="My Profile" subtitle="Keep your profile up to date for better job matches." />

      {/* Completion bar */}
      <div className="card mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">Profile Completion</span>
          <span className="text-sm font-bold text-primary-600">{profile?.profile_completion_pct || 0}%</span>
        </div>
        <ProgressBar value={profile?.profile_completion_pct || 0} />
        {(profile?.profile_completion_pct || 0) < 80 && (
          <Alert type="info" className="mt-3">Fill in all sections to improve your match score.</Alert>
        )}
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Personal */}
        <div className="card">
          <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2"><User size={16} /> Personal Info</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Phone" name="phone" placeholder="+91-9876543210" />
            <Field label="Location" name="location" placeholder="Bangalore, India" />
            <Field label="LinkedIn URL" name="linkedin_url" placeholder="linkedin.com/in/yourname" />
            <Field label="GitHub URL" name="github_url" placeholder="github.com/yourname" />
            <Field label="Portfolio URL" name="portfolio_url" placeholder="yoursite.com" />
          </div>
          <div className="mt-4">
            <label className="label">Bio / Summary</label>
            <textarea className="input h-24 resize-none" placeholder="Brief professional summary..."
              value={form.bio || ''} onChange={e => set('bio', e.target.value)} />
          </div>
        </div>

        {/* Education */}
        <div className="card">
          <h2 className="font-semibold text-gray-900 mb-4">Education</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Degree" name="degree" placeholder="B.Tech" />
            <Field label="Branch" name="branch" placeholder="Computer Science" />
            <Field label="Institution" name="institution" placeholder="IIT Bombay" />
            <Field label="CGPA" name="cgpa" type="number" placeholder="8.5" />
            <Field label="Graduation Year" name="graduation_year" type="number" placeholder="2024" />
          </div>
        </div>

        {/* Experience */}
        <div className="card">
          <h2 className="font-semibold text-gray-900 mb-4">Experience</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Years of Experience" name="years_of_experience" type="number" placeholder="2" />
            <Field label="Current Company" name="current_company" placeholder="TechCorp" />
            <Field label="Current Job Title" name="current_job_title" placeholder="Software Engineer" />
            <Field label="Expected Salary" name="expected_salary" placeholder="12-18 LPA" />
          </div>
        </div>

        {/* Career preferences */}
        <div className="card">
          <h2 className="font-semibold text-gray-900 mb-4">Career Preferences</h2>
          <div>
            <label className="label">Target Roles (comma-separated)</label>
            <input type="text" className="input"
              placeholder="AI/ML Engineer, Data Scientist"
              value={(form.target_roles || []).join(', ')}
              onChange={e => set('target_roles', e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
            />
          </div>
        </div>

        <button type="submit" disabled={saving} className="btn-primary flex items-center gap-2">
          <Save size={16} /> {saving ? 'Saving...' : 'Save Profile'}
        </button>
      </form>
    </DashboardLayout>
  );
}
