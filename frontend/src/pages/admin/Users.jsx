import { useState, useEffect } from 'react';
import api from '../../services/api';
import DashboardLayout from '../../components/layout/DashboardLayout';
import { Spinner, PageHeader, StatusBadge } from '../../components/ui';
import { Users } from 'lucide-react';

export default function AdminUsers() {
  const [users, setUsers]   = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Admin endpoint — simple users list via auth/me-style (using existing admin analytics for now)
    api.get('/api/analytics/admin')
      .then(() => {
        // Users list endpoint not yet built — show placeholder with stats
        setUsers([]);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <DashboardLayout>
      <PageHeader title="Users" subtitle="All registered users on the platform." />
      {loading ? <div className="flex justify-center py-20"><Spinner size="lg" /></div> : (
        <div className="card text-center py-12">
          <Users size={40} className="mx-auto text-gray-300 mb-3" />
          <p className="font-medium text-gray-700">User management coming soon</p>
          <p className="text-sm text-gray-500 mt-1">Use the Admin Dashboard for platform statistics.</p>
        </div>
      )}
    </DashboardLayout>
  );
}
