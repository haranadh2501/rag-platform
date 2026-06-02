// Documents page placeholder.
// Phase 3 will add DocumentUploadPanel, StorageQuotaBar, and DocumentTable.
export default function DocumentsPage() {
  return (
    <main className="p-6">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-slate-900">Documents</h1>
        <p className="mt-1 text-sm text-slate-500">
          Manage your tenant knowledge base documents.
        </p>
      </div>

      {/* Upload placeholder — Phase 3 */}
      <div className="mb-6 rounded-lg border-2 border-dashed border-slate-300 bg-white p-8 text-center">
        <p className="text-sm text-slate-400">Upload panel — coming in Phase 3</p>
      </div>

      {/* Storage quota placeholder — Phase 3 */}
      <div className="mb-6 h-4 rounded-full bg-slate-200">
        <div className="h-4 w-2/5 rounded-full bg-emerald-500" />
      </div>

      {/* Document list placeholder — Phase 3 */}
      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              {['Title', 'Type', 'Status', 'Chunks', 'Uploaded', 'Actions'].map(
                (col) => (
                  <th
                    key={col}
                    className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-slate-500"
                  >
                    {col}
                  </th>
                ),
              )}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td
                colSpan={6}
                className="px-4 py-8 text-center text-sm text-slate-400"
              >
                Document list — coming in Phase 3
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </main>
  );
}
