import { Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/ui/ProtectedRoute';

// Public
import Login    from './pages/public/Login';
import Register from './pages/public/Register';

// Candidate
import CandidateDashboard    from './pages/candidate/Dashboard';
import CandidateProfile      from './pages/candidate/Profile';
import CandidateResume       from './pages/candidate/Resume';
import CandidateJobs         from './pages/candidate/Jobs';
import CandidateApplications from './pages/candidate/Applications';
import CandidateRoadmap      from './pages/candidate/Roadmap';
import CandidateInterview    from './pages/candidate/Interview';
import CandidateAssistant    from './pages/candidate/Assistant';

// Recruiter
import RecruiterDashboard  from './pages/recruiter/Dashboard';
import RecruiterJobs       from './pages/recruiter/Jobs';
import CreateJob           from './pages/recruiter/CreateJob';
import RecruiterJobDetail  from './pages/recruiter/JobDetail';
import RecruiterCandidates from './pages/recruiter/Candidates';
import RecruiterAnalytics  from './pages/recruiter/Analytics';

// Admin
import AdminDashboard  from './pages/admin/Dashboard';
import AdminUsers      from './pages/admin/Users';
import AdminAnalytics  from './pages/admin/Analytics';

const C = (role, Component) => (
  <ProtectedRoute role={role}><Component /></ProtectedRoute>
);

export default function App() {
  return (
    <AuthProvider>
        <Toaster position="top-right" toastOptions={{ duration: 4000 }} />
        <Routes>
          {/* Public */}
          <Route path="/"         element={<Navigate to="/login" replace />} />
          <Route path="/login"    element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Candidate */}
          <Route path="/candidate/dashboard"    element={C('CANDIDATE', CandidateDashboard)} />
          <Route path="/candidate/profile"      element={C('CANDIDATE', CandidateProfile)} />
          <Route path="/candidate/resume"       element={C('CANDIDATE', CandidateResume)} />
          <Route path="/candidate/jobs"         element={C('CANDIDATE', CandidateJobs)} />
          <Route path="/candidate/applications" element={C('CANDIDATE', CandidateApplications)} />
          <Route path="/candidate/roadmap"      element={C('CANDIDATE', CandidateRoadmap)} />
          <Route path="/candidate/interview"    element={C('CANDIDATE', CandidateInterview)} />
          <Route path="/candidate/assistant"    element={C('CANDIDATE', CandidateAssistant)} />

          {/* Recruiter */}
          <Route path="/recruiter/dashboard"    element={C('RECRUITER', RecruiterDashboard)} />
          <Route path="/recruiter/jobs"         element={C('RECRUITER', RecruiterJobs)} />
          <Route path="/recruiter/jobs/create"  element={C('RECRUITER', CreateJob)} />
          <Route path="/recruiter/jobs/:id"     element={C('RECRUITER', RecruiterJobDetail)} />
          <Route path="/recruiter/candidates"   element={C('RECRUITER', RecruiterCandidates)} />
          <Route path="/recruiter/analytics"    element={C('RECRUITER', RecruiterAnalytics)} />

          {/* Admin */}
          <Route path="/admin/dashboard"  element={C('ADMIN', AdminDashboard)} />
          <Route path="/admin/users"      element={C('ADMIN', AdminUsers)} />
          <Route path="/admin/jobs"       element={C('ADMIN', RecruiterJobs)} />
          <Route path="/admin/analytics"  element={C('ADMIN', AdminAnalytics)} />

          {/* 404 */}
          <Route path="*" element={
            <div className="min-h-screen flex items-center justify-center">
              <div className="text-center">
                <p className="text-5xl font-bold text-primary-600 mb-2">404</p>
                <p className="text-gray-600 mb-4">Page not found.</p>
                <button onClick={() => window.history.back()} className="btn-primary">Go Back</button>
              </div>
            </div>
          } />
        </Routes>
    </AuthProvider>
  );
}
