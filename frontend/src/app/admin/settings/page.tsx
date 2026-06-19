export default function SettingsPage() {
  return (
    <main className="p-6">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-slate-900">Settings</h1>
        <p className="mt-1 text-sm text-slate-500">
          Tenant configuration and channel status.
        </p>
      </div>

      {/* Tenant info card */}
      <div className="mb-4 rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-slate-700">Tenant Info</h2>
        <dl className="space-y-2 text-sm">
          <div className="flex gap-4">
            <dt className="w-16 shrink-0 text-slate-500">Name</dt>
            <dd className="text-slate-400">— wired to tenant data in Phase 7</dd>
          </div>
          <div className="flex gap-4">
            <dt className="w-16 shrink-0 text-slate-500">Slug</dt>
            <dd className="text-slate-400">—</dd>
          </div>
          <div className="flex gap-4">
            <dt className="w-16 shrink-0 text-slate-500">Plan</dt>
            <dd className="text-slate-400">—</dd>
          </div>
        </dl>
      </div>

      {/* Channel status */}
      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-slate-700">Channel Status</h2>
        <div className="flex gap-6 text-sm">
          <span className="text-emerald-600">● Web</span>
          <span className="text-slate-400">○ WhatsApp</span>
          <span className="text-slate-400">○ Slack</span>
        </div>
        <p className="mt-2 text-xs text-amber-600">
          Placeholder values — actual channel status is sourced from backend config in Phase 7.
        </p>
        <p className="mt-2 text-xs text-slate-400">
          Rate limit: 20 uploads / hour per tenant
        </p>
      </div>
    </main>
  );
}
