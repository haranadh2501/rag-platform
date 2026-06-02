// Shell layout for /admin/* routes.
// Phase 2 will replace this with AdminLayout (AuthGuard + 240 px sidebar + header).
export default function AdminShellLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <div className="min-h-screen bg-slate-50">{children}</div>;
}
