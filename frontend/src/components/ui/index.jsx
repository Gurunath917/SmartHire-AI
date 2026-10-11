// ── Spinner ───────────────────────────────────────────────────────────────────
export function Spinner({ size = 'md' }) {
  const s = size === 'sm' ? 'w-4 h-4' : size === 'lg' ? 'w-10 h-10' : 'w-6 h-6';
  return (
    <div className={`${s} border-2 border-primary-500 border-t-transparent rounded-full animate-spin`} />
  );
}

// ── Empty State ───────────────────────────────────────────────────────────────
export function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="text-center py-12">
      {Icon && <Icon className="mx-auto h-12 w-12 text-gray-300 mb-4" />}
      <h3 className="text-sm font-medium text-gray-900">{title}</h3>
      {description && <p className="mt-1 text-sm text-gray-500">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

// ── Score Badge ───────────────────────────────────────────────────────────────
export function ScoreBadge({ score }) {
  if (score === null || score === undefined) return null;
  const color =
    score >= 80 ? 'bg-green-100 text-green-800' :
    score >= 60 ? 'bg-yellow-100 text-yellow-800' :
    'bg-red-100 text-red-800';
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${color}`}>
      {score.toFixed(0)}%
    </span>
  );
}

// ── Progress Bar ──────────────────────────────────────────────────────────────
export function ProgressBar({ value, max = 100, color = 'bg-primary-500', className = '' }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div className={`w-full bg-gray-200 rounded-full h-2 ${className}`}>
      <div className={`${color} h-2 rounded-full transition-all duration-500`} style={{ width: `${pct}%` }} />
    </div>
  );
}

// ── Stat Card ─────────────────────────────────────────────────────────────────
export function StatCard({ label, value, icon: Icon, color = 'text-primary-600', bg = 'bg-primary-50' }) {
  return (
    <div className="card flex items-center gap-4">
      {Icon && (
        <div className={`p-3 rounded-lg ${bg}`}>
          <Icon size={20} className={color} />
        </div>
      )}
      <div>
        <p className="text-sm text-gray-500">{label}</p>
        <p className="text-2xl font-bold text-gray-900">{value ?? '—'}</p>
      </div>
    </div>
  );
}

// ── Alert ─────────────────────────────────────────────────────────────────────
export function Alert({ type = 'info', children }) {
  const styles = {
    info:    'bg-blue-50 text-blue-800 border-blue-200',
    success: 'bg-green-50 text-green-800 border-green-200',
    warning: 'bg-yellow-50 text-yellow-800 border-yellow-200',
    error:   'bg-red-50 text-red-800 border-red-200',
  };
  return (
    <div className={`border rounded-lg p-4 text-sm ${styles[type]}`}>
      {children}
    </div>
  );
}

// ── Skill Badge ───────────────────────────────────────────────────────────────
const CATEGORY_COLORS = {
  programming_language: 'bg-blue-100 text-blue-800',
  framework:            'bg-purple-100 text-purple-800',
  database:             'bg-orange-100 text-orange-800',
  cloud:                'bg-sky-100 text-sky-800',
  ml:                   'bg-green-100 text-green-800',
  genai:                'bg-pink-100 text-pink-800',
  tool:                 'bg-gray-100 text-gray-700',
  soft_skill:           'bg-yellow-100 text-yellow-800',
};

export function SkillBadge({ skill_name, category }) {
  const color = CATEGORY_COLORS[category] || 'bg-gray-100 text-gray-700';
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium ${color}`}>
      {skill_name}
    </span>
  );
}

// ── Page Header ───────────────────────────────────────────────────────────────
export function PageHeader({ title, subtitle, action }) {
  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
        {subtitle && <p className="text-sm text-gray-500 mt-1">{subtitle}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}

// ── Status Badge ──────────────────────────────────────────────────────────────
const STATUS_STYLES = {
  APPLIED:             'badge-blue',
  UNDER_REVIEW:        'badge-yellow',
  SHORTLISTED:         'badge-green',
  INTERVIEW_SCHEDULED: 'badge-purple',
  REJECTED:            'badge-red',
  WITHDRAWN:           'badge-gray',
  OFFERED:             'badge-green',
  ACTIVE:              'badge-green',
  DRAFT:               'badge-gray',
  CLOSED:              'badge-red',
  PAUSED:              'badge-yellow',
  GENERATED:           'badge-blue',
  IN_PROGRESS:         'badge-yellow',
  COMPLETED:           'badge-green',
  EVALUATED:           'badge-green',
  PENDING:             'badge-gray',
};

export function StatusBadge({ status }) {
  const cls = STATUS_STYLES[status] || 'badge-gray';
  return <span className={cls}>{status?.replace(/_/g, ' ')}</span>;
}
