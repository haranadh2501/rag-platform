import Image from 'next/image';
import Link from 'next/link';

export default function LandingPage() {
  return (
    <main className="flex min-h-screen flex-col bg-white">
      {/* Nav */}
      <nav className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
        <span className="text-sm font-semibold tracking-wide text-indigo-600">RAG Platform</span>
      </nav>

      {/* Hero */}
      <section className="flex flex-1 flex-col items-center justify-center px-6 py-24 text-center">
        <span className="mb-4 inline-block rounded-full bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">
          Powered by OpenAI + n8n
        </span>
        <h1 className="max-w-2xl text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl">
          Build your AI knowledge base{' '}
          <span className="text-indigo-600">in minutes</span>
        </h1>
        <p className="mt-5 max-w-xl text-lg text-slate-500">
          Upload any documents, then query them via chat, WhatsApp, or Slack.
          No ML expertise required.
        </p>
        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          <Link
            href="/onboarding"
            className="rounded-md bg-indigo-600 px-8 py-3 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700"
          >
            Get started free →
          </Link>
          <Link
            href="/login"
            className="rounded-md border border-slate-300 px-8 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          >
            Sign in
          </Link>
        </div>
      </section>

      {/* Features */}
      <section className="border-t border-slate-100 bg-slate-50 px-6 py-16">
        <div className="mx-auto grid max-w-4xl gap-8 sm:grid-cols-3">
          <div className="text-center">
            <div className="mb-3 text-3xl">📄</div>
            <h3 className="mb-1 font-semibold text-slate-900">Upload any document</h3>
            <p className="text-sm text-slate-500">PDF, DOCX, TXT — drag-and-drop or URL ingestion. Processed and chunked automatically.</p>
          </div>
          <div className="text-center">
            <div className="mb-3 text-3xl">💬</div>
            <h3 className="mb-1 font-semibold text-slate-900">Query via chat</h3>
            <p className="text-sm text-slate-500">Ask questions in plain English. Every answer is grounded in your documents with source citations.</p>
          </div>
          <div className="text-center">
            <div className="mb-3 flex items-center justify-center gap-3">
              <Image src="/whatsapp.png" alt="WhatsApp" width={36} height={29} className="rounded" />
              <Image src="/slack.png" alt="Slack" width={84} height={36} className="rounded object-contain" />
            </div>
            <h3 className="mb-1 font-semibold text-slate-900">WhatsApp &amp; Slack</h3>
            <p className="text-sm text-slate-500">Connect your existing channels. Your team queries the knowledge base where they already work.</p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-100 px-6 py-6 text-center text-xs text-slate-400">
        © {new Date().getFullYear()} IISc RAG Platform
      </footer>
    </main>
  );
}
