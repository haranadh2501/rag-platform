export default function UsersPage() {
  return (
    <main className="p-6">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-slate-900">Users</h1>
        <p className="mt-1 text-sm text-slate-500">
          Manage tenant users and send invitations.
        </p>
      </div>

      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              {['Email', 'Role', 'Active', 'Joined', 'Actions'].map((col) => (
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
              <td colSpan={5} className="px-4 py-10 text-center text-sm text-slate-400">
                User list — wired to GET /admin/users in Phase 5.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </main>
  );
}
