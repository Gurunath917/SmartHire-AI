import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Attach token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Redirect to login on 401
api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authAPI = {
  register: (data) => api.post('/api/auth/register', data),
  login:    (data) => api.post('/api/auth/login', data),
  me:       ()     => api.get('/api/auth/me'),
  logout:   ()     => api.post('/api/auth/logout'),
};

// ── Candidate ─────────────────────────────────────────────────────────────────
export const candidateAPI = {
  getProfile:   ()     => api.get('/api/candidates/me'),
  updateProfile:(data) => api.put('/api/candidates/me', data),
  getSkills:    ()     => api.get('/api/candidates/me/skills'),
};

// ── Resume ────────────────────────────────────────────────────────────────────
export const resumeAPI = {
  upload:  (file)  => {
    const form = new FormData();
    form.append('file', file);
    return api.post('/api/resumes/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  list:    ()      => api.get('/api/resumes/'),
  get:     (id)    => api.get(`/api/resumes/${id}`),
  parse:   (id)    => api.post(`/api/resumes/${id}/parse`),
  delete:  (id)    => api.delete(`/api/resumes/${id}`),
};

// ── Jobs ──────────────────────────────────────────────────────────────────────
export const jobsAPI = {
  list:     (params) => api.get('/api/jobs/', { params }),
  get:      (id)     => api.get(`/api/jobs/${id}`),
  create:   (data)   => api.post('/api/jobs/', data),
  update:   (id, d)  => api.put(`/api/jobs/${id}`, d),
  delete:   (id)     => api.delete(`/api/jobs/${id}`),
  setStatus:(id, s)  => api.patch(`/api/jobs/${id}/status`, { job_status: s }),
  analyze:  (desc)   => api.post('/api/jobs/analyze', { description: desc }),
  applicants:(id)    => api.get(`/api/jobs/${id}/applicants`),
};

// ── Applications ──────────────────────────────────────────────────────────────
export const applicationsAPI = {
  apply:    (job_id, cover_letter='') => api.post('/api/applications/', { job_id, cover_letter }),
  list:     ()                        => api.get('/api/applications/'),
  withdraw: (id)                      => api.delete(`/api/applications/${id}`),
  setStatus:(id, status)              => api.patch(`/api/applications/${id}/status`, { app_status: status }),
};

// ── Saved Jobs ────────────────────────────────────────────────────────────────
export const savedJobsAPI = {
  save:   (id) => api.post(`/api/saved-jobs/${id}`),
  unsave: (id) => api.delete(`/api/saved-jobs/${id}`),
  list:   ()   => api.get('/api/saved-jobs/'),
};

// ── Matching ──────────────────────────────────────────────────────────────────
export const matchingAPI = {
  analyze:       (job_id)  => api.post('/api/matching/analyze', { job_id }),
  myMatches:     (limit=10)=> api.get('/api/matching/candidates/matches', { params: { limit } }),
  jobMatches:    (job_id)  => api.get(`/api/matching/jobs/${job_id}/matches`),
  skillGap:      (job_id)  => api.get(`/api/matching/jobs/${job_id}/skill-gap`),
  allSkillGaps:  ()        => api.get('/api/matching/candidates/skill-gap'),
  modelInfo:     ()        => api.get('/api/matching/model-info'),
};

// ── Roadmap ───────────────────────────────────────────────────────────────────
export const roadmapAPI = {
  generate:       (data)          => api.post('/api/roadmap/generate', data),
  list:           ()              => api.get('/api/roadmap/'),
  get:            (id)            => api.get(`/api/roadmap/${id}`),
  updateProgress: (id, week, done)=> api.patch(`/api/roadmap/${id}/progress`, {
    week_number: week, is_completed: done,
  }),
  delete:         (id)            => api.delete(`/api/roadmap/${id}`),
};

// ── Interviews ────────────────────────────────────────────────────────────────
export const interviewAPI = {
  create:     (data)             => api.post('/api/interviews/', data),
  list:       ()                 => api.get('/api/interviews/'),
  get:        (id)               => api.get(`/api/interviews/${id}`),
  answer:     (id, data)         => api.post(`/api/interviews/${id}/answer`, data),
  evaluate:   (id)               => api.post(`/api/interviews/${id}/evaluate`),
  getEval:    (id)               => api.get(`/api/interviews/${id}/evaluation`),
};

// ── Assistant ─────────────────────────────────────────────────────────────────
export const assistantAPI = {
  chat:           (message, session_id=null) => api.post('/api/assistant/chat', { message, session_id }),
  listSessions:   ()                         => api.get('/api/assistant/history'),
  getSession:     (id)                       => api.get(`/api/assistant/history/${id}`),
  deleteSession:  (id)                       => api.delete(`/api/assistant/history/${id}`),
};

// ── Analytics ─────────────────────────────────────────────────────────────────
export const analyticsAPI = {
  candidate: () => api.get('/api/analytics/candidate'),
  recruiter: () => api.get('/api/analytics/recruiter'),
  admin:     () => api.get('/api/analytics/admin'),
};

// ── Recruiters ────────────────────────────────────────────────────────────────
export const recruiterAPI = {
  getProfile:   ()     => api.get('/api/recruiters/me'),
  updateProfile:(data) => api.put('/api/recruiters/me', data),
  myJobs:       (p)    => api.get('/api/recruiters/me/jobs', { params: p }),
  stats:        ()     => api.get('/api/recruiters/me/stats'),
};
