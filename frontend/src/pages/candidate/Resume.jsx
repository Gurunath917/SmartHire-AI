import { useState, useEffect, useRef } from 'react';
import { resumeAPI } from '../../services/api';
import DashboardLayout from '../../components/layout/DashboardLayout';
import { Spinner, PageHeader, Alert, SkillBadge, StatusBadge } from '../../components/ui';
import { Upload, FileText, Trash2, RefreshCw, CheckCircle } from 'lucide-react';
import toast from 'react-hot-toast';

export default function CandidateResume() {
  const [resumes, setResumes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [parsing, setParsing] = useState({});
  const fileRef = useRef();

  const load = () => {
    resumeAPI.list()
      .then(r => setResumes(r.data))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.endsWith('.pdf')) { toast.error('Only PDF files are accepted.'); return; }
    setUploading(true);
    try {
      await resumeAPI.upload(file);
      toast.success('Resume uploaded and parsed!');
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Upload failed.');
    } finally {
      setUploading(false);
      fileRef.current.value = '';
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this resume?')) return;
    try {
      await resumeAPI.delete(id);
      toast.success('Resume deleted.');
      setResumes(prev => prev.filter(r => r.id !== id));
    } catch { toast.error('Delete failed.'); }
  };

  const handleReparse = async (id) => {
    setParsing(prev => ({ ...prev, [id]: true }));
    try {
      await resumeAPI.parse(id);
      toast.success('Resume re-parsed!');
      load();
    } catch { toast.error('Parse failed.'); }
    finally { setParsing(prev => ({ ...prev, [id]: false })); }
  };

  const active = resumes.find(r => r.is_active);
  const skills = active?.parsed_data?.skills?.all || [];

  return (
    <DashboardLayout>
      <PageHeader title="Resume" subtitle="Upload your PDF resume to extract skills automatically." />

      {/* Upload area */}
      <div
        className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center mb-6 hover:border-primary-400 hover:bg-primary-50 transition-colors cursor-pointer"
        onClick={() => fileRef.current?.click()}
      >
        <input ref={fileRef} type="file" accept=".pdf" className="hidden" onChange={handleUpload} />
        {uploading ? (
          <div className="flex flex-col items-center gap-2">
            <Spinner size="lg" />
            <p className="text-sm text-gray-600">Uploading and parsing...</p>
          </div>
        ) : (
          <>
            <Upload size={32} className="mx-auto text-gray-400 mb-2" />
            <p className="font-medium text-gray-700">Click to upload PDF resume</p>
            <p className="text-xs text-gray-500 mt-1">Max 10 MB • PDF only</p>
          </>
        )}
      </div>

      {loading ? <div className="flex justify-center py-10"><Spinner size="lg" /></div> : (
        <>
          {/* Active resume details */}
          {active && (
            <div className="card mb-6">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <FileText size={20} className="text-primary-600" />
                  <div>
                    <p className="font-semibold text-gray-900">{active.original_filename}</p>
                    <p className="text-xs text-gray-500">
                      {(active.file_size_bytes / 1024).toFixed(0)} KB •{' '}
                      {active.is_parsed ? (
                        <span className="text-green-600 flex items-center gap-1 inline-flex">
                          <CheckCircle size={12} /> Parsed
                        </span>
                      ) : 'Not parsed'}
                    </p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleReparse(active.id)}
                    disabled={parsing[active.id]}
                    className="btn-secondary text-xs py-1.5 flex items-center gap-1"
                  >
                    <RefreshCw size={12} /> Re-parse
                  </button>
                  <button onClick={() => handleDelete(active.id)} className="btn-danger text-xs py-1.5">
                    <Trash2 size={12} />
                  </button>
                </div>
              </div>

              {active.is_parsed && (
                <>
                  {/* Extracted sections */}
                  {active.extracted_sections && Object.keys(active.extracted_sections).length > 0 && (
                    <div className="mb-4">
                      <p className="text-sm font-medium text-gray-700 mb-2">Detected Sections</p>
                      <div className="flex flex-wrap gap-2">
                        {Object.keys(active.extracted_sections).map(s => (
                          <span key={s} className="badge-blue capitalize">{s}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Extracted contact */}
                  {active.parsed_data?.contact?.email && (
                    <Alert type="success">
                      <strong>Contact detected:</strong> {active.parsed_data.contact.email}
                      {active.parsed_data.contact.phone && ` • ${active.parsed_data.contact.phone}`}
                    </Alert>
                  )}

                  {/* Extracted skills */}
                  {skills.length > 0 && (
                    <div className="mt-4">
                      <p className="text-sm font-medium text-gray-700 mb-2">
                        Extracted Skills ({skills.length})
                        <span className="text-xs text-gray-400 ml-2">— review and edit in Profile</span>
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {skills.map(s => (
                          <span key={s} className="badge-purple">{s}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* All resumes list */}
          {resumes.filter(r => !r.is_active).length > 0 && (
            <div className="card">
              <h3 className="font-medium text-gray-700 mb-3">Previous Resumes</h3>
              <div className="space-y-2">
                {resumes.filter(r => !r.is_active).map(r => (
                  <div key={r.id} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                    <div className="flex items-center gap-2">
                      <FileText size={14} className="text-gray-400" />
                      <span className="text-sm text-gray-600">{r.original_filename}</span>
                    </div>
                    <button onClick={() => handleDelete(r.id)} className="text-red-500 hover:text-red-700 p-1">
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </DashboardLayout>
  );
}
