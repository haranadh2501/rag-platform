// Placeholder — POST /auth/login wiring and authContext.login() call happen in a later phase.
// No form submission logic is implemented here.

export default function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-8 shadow-sm">

        {/* Brand + heading */}
        <div className="mb-6 text-center">
          <span className="text-sm font-semibold tracking-wide text-indigo-600">
            RAG Platform
          </span>
          <h1 className="mt-2 text-xl font-semibold text-slate-900">Sign in</h1>
          <p className="mt-1 text-sm text-slate-500">
            Enter your email and password to continue.
          </p>
        </div>

        {/* Placeholder notice */}
        <div className="mb-5 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-700">
          Placeholder —{' '}
          <code className="rounded bg-amber-100 px-1">POST /auth/login</code>
          {' '}wiring and redirect happen in a later phase. The button is disabled.
        </div>

        <form>
          <div className="space-y-4">
            <div>
              <label
                htmlFor="email"
                className="mb-1 block text-xs font-medium text-slate-700"
              >
                Email
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                placeholder="admin@example.com"
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="mb-1 block text-xs font-medium text-slate-700"
              >
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                placeholder="••••••••"
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled
            className="mt-5 w-full cursor-not-allowed rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white opacity-40"
          >
            Sign in
          </button>
        </form>
      </div>
    </main>
  );
}
