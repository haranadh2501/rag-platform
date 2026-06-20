export default function TenantsPage() {
  return (
    <main className="p-6">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-slate-900">Tenants</h1>
        <p className="mt-1 flex items-center gap-2 text-sm text-slate-500">
          Create and manage tenants.
          <span className="inline-flex items-center rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700 ring-1 ring-inset ring-indigo-600/20">
            super_admin only
          </span>
        </p>
      </div>

      <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
        <strong>Placeholder — no role check is enforced yet.</strong> Any authenticated
        user can currently reach this page. Once auth is wired in Phase 6:{' '}
        <code className="rounded bg-amber-100 px-1 text-xs">admin</code> role will see a
        403 state;{' '}
        <code className="rounded bg-amber-100 px-1 text-xs">super_admin</code> will see
        the full tenant table.
      </div>

      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              {['Tenant', 'Slug', 'Plan', 'Active', 'Created', 'Actions'].map((col) => (
                <th
                  key={col}
                  className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-slate-500"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan={6} className="px-4 py-10 text-center text-sm text-slate-400">
                Tenant list — wired to GET /admin/tenants in Phase 6.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </main>
  );
}
