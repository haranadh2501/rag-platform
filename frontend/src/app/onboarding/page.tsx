'use client';

import Image from 'next/image';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { checkSlugApi, registerTenantApi } from '../../lib/onboardingApi';
import { uploadDocumentApi } from '../../lib/documentApi';
import { setAuthToken } from '../../lib/apiClient';
import { useAuth } from '../../lib/authContext';
import type { UserOut } from '@admin-types';

// ── helpers ──────────────────────────────────────────────────────────────────

function slugify(value: string): string {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

// ── step sub-components ───────────────────────────────────────────────────────

interface StepIndicatorProps {
  current: number;
  total: number;
}

function StepIndicator({ current, total }: StepIndicatorProps) {
  return (
    <div className="mb-8 flex items-center justify-center gap-2">
      {Array.from({ length: total }, (_, i) => (
        <div key={i} className="flex items-center gap-2">
          <div
            className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold ${
              i + 1 < current
                ? 'bg-indigo-600 text-white'
                : i + 1 === current
                ? 'bg-indigo-600 text-white ring-4 ring-indigo-100'
                : 'bg-slate-200 text-slate-500'
            }`}
          >
            {i + 1 < current ? '✓' : i + 1}
          </div>
          {i < total - 1 && (
            <div className={`h-0.5 w-8 ${i + 1 < current ? 'bg-indigo-600' : 'bg-slate-200'}`} />
          )}
        </div>
      ))}
    </div>
  );
}

// ── main component ────────────────────────────────────────────────────────────

interface WizardData {
  companyName: string;
  companySlug: string;
  adminEmail: string;
  adminPassword: string;
  confirmPassword: string;
  plan: 'free' | 'pro';
}

type SlugStatus = 'idle' | 'checking' | 'available' | 'taken' | 'invalid';

export default function OnboardingPage() {
  const router = useRouter();
  const { login } = useAuth();

  const [step, setStep] = useState(1);
  const [data, setData] = useState<WizardData>({
    companyName: '',
    companySlug: '',
    adminEmail: '',
    adminPassword: '',
    confirmPassword: '',
    plan: 'free',
  });

  // step 1 state
  const [slugStatus, setSlugStatus] = useState<SlugStatus>('idle');
  const slugDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [step1Error, setStep1Error] = useState<string | null>(null);

  // step 2 state
  const [step2Error, setStep2Error] = useState<string | null>(null);
  const [registering, setRegistering] = useState(false);

  // step 3 state
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // stored after registration — needed for step 3 upload
  const [registeredToken, setRegisteredToken] = useState<string | null>(null);
  const [registeredUser, setRegisteredUser] = useState<UserOut | null>(null);

  // ── slug debounce ──────────────────────────────────────────────────────────

  const checkSlug = useCallback(async (slug: string) => {
    if (!slug || slug.length < 2) {
      setSlugStatus('idle');
      return;
    }
    setSlugStatus('checking');
    try {
      const res = await checkSlugApi(slug);
      setSlugStatus(res.available ? 'available' : 'taken');
    } catch {
      setSlugStatus('idle');
    }
  }, []);

  function handleSlugChange(raw: string) {
    const slug = slugify(raw);
    setData((d) => ({ ...d, companySlug: slug }));
    setSlugStatus('checking');
    if (slugDebounceRef.current) clearTimeout(slugDebounceRef.current);
    slugDebounceRef.current = setTimeout(() => checkSlug(slug), 500);
  }

  function handleCompanyNameChange(name: string) {
    setData((d) => ({ ...d, companyName: name }));
    // Auto-fill slug only if user hasn't manually edited it
    const autoSlug = slugify(name);
    handleSlugChange(autoSlug);
  }

  useEffect(() => {
    return () => {
      if (slugDebounceRef.current) clearTimeout(slugDebounceRef.current);
    };
  }, []);

  // ── step 1 submit ──────────────────────────────────────────────────────────

  function submitStep1() {
    setStep1Error(null);
    if (!data.companyName.trim()) { setStep1Error('Company name required.'); return; }
    if (!data.companySlug) { setStep1Error('Slug required.'); return; }
    if (slugStatus === 'taken') { setStep1Error('That slug is already taken.'); return; }
    if (slugStatus === 'checking') { setStep1Error('Checking slug availability…'); return; }
    if (slugStatus === 'idle' && data.companySlug.length < 2) { setStep1Error('Slug too short.'); return; }
    setStep(2);
  }

  // ── step 2 submit — calls register API ────────────────────────────────────

  async function submitStep2() {
    setStep2Error(null);
    if (!data.adminEmail.trim()) { setStep2Error('Email required.'); return; }
    if (data.adminPassword.length < 8) { setStep2Error('Password must be at least 8 characters.'); return; }
    if (data.adminPassword !== data.confirmPassword) { setStep2Error('Passwords do not match.'); return; }

    setRegistering(true);
    try {
      const res = await registerTenantApi({
        company_name: data.companyName,
        company_slug: data.companySlug,
        admin_email: data.adminEmail,
        admin_password: data.adminPassword,
        plan: data.plan,
      });

      // Store token for upload step; wire into auth context
      setRegisteredToken(res.access_token);
      setRegisteredUser(res.admin_user as UserOut);
      setAuthToken(res.access_token);
      login(res.access_token, res.admin_user as UserOut);

      setStep(3);
    } catch (err) {
      setStep2Error(err instanceof Error ? err.message : 'Registration failed.');
    } finally {
      setRegistering(false);
    }
  }

  // ── step 3 upload ──────────────────────────────────────────────────────────

  async function handleUpload() {
    if (!uploadFile) return;
    setUploading(true);
    setUploadError(null);
    try {
      await uploadDocumentApi({
        file: uploadFile,
        title: uploadFile.name,
        onProgress: setUploadProgress,
      });
      setStep(4);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed.');
    } finally {
      setUploading(false);
    }
  }

  function handleFileDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) setUploadFile(file);
  }

  // ── slug indicator ─────────────────────────────────────────────────────────

  function SlugIndicator() {
    if (!data.companySlug) return null;
    if (slugStatus === 'checking') return <span className="text-xs text-slate-400">Checking…</span>;
    if (slugStatus === 'available') return <span className="text-xs text-emerald-600">✓ Available</span>;
    if (slugStatus === 'taken') return <span className="text-xs text-red-600">✗ Already taken</span>;
    return null;
  }

  // ── render ─────────────────────────────────────────────────────────────────

  return (
    <main className="flex min-h-screen items-start justify-center bg-slate-50 px-4 py-16">
      <div className="w-full max-w-md">
        {/* Brand */}
        <div className="mb-6 text-center">
          <span className="text-sm font-semibold tracking-wide text-indigo-600">RAG Platform</span>
          <h1 className="mt-1 text-2xl font-bold text-slate-900">Get started</h1>
        </div>

        <StepIndicator current={step} total={4} />

        <div className="rounded-xl border border-slate-200 bg-white p-8 shadow-sm">

          {/* ── Step 1: Company Info ─────────────────────────────────────── */}
          {step === 1 && (
            <div>
              <h2 className="mb-5 text-lg font-semibold text-slate-900">Company information</h2>
              <div className="space-y-4">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700">Company name</label>
                  <input
                    type="text"
                    value={data.companyName}
                    onChange={(e) => handleCompanyNameChange(e.target.value)}
                    placeholder="Acme Corp"
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <div className="mb-1 flex items-center justify-between">
                    <label className="text-xs font-medium text-slate-700">Company slug</label>
                    <SlugIndicator />
                  </div>
                  <input
                    type="text"
                    value={data.companySlug}
                    onChange={(e) => handleSlugChange(e.target.value)}
                    placeholder="acme-corp"
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                  <p className="mt-1 text-xs text-slate-400">Lowercase letters, numbers, hyphens only.</p>
                </div>

                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700">Plan</label>
                  <select
                    value={data.plan}
                    onChange={(e) => setData((d) => ({ ...d, plan: e.target.value as 'free' | 'pro' }))}
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-800 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  >
                    <option value="free">Free</option>
                    <option value="pro">Pro</option>
                  </select>
                </div>
              </div>

              {step1Error && <p className="mt-3 text-xs text-red-600">{step1Error}</p>}

              <button
                onClick={submitStep1}
                className="mt-6 w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-40"
              >
                Next →
              </button>
            </div>
          )}

          {/* ── Step 2: Admin User ───────────────────────────────────────── */}
          {step === 2 && (
            <div>
              <h2 className="mb-5 text-lg font-semibold text-slate-900">Admin account</h2>
              <div className="space-y-4">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700">Email</label>
                  <input
                    type="email"
                    value={data.adminEmail}
                    onChange={(e) => setData((d) => ({ ...d, adminEmail: e.target.value }))}
                    placeholder="admin@acme.com"
                    disabled={registering}
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-60"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700">Password</label>
                  <input
                    type="password"
                    value={data.adminPassword}
                    onChange={(e) => setData((d) => ({ ...d, adminPassword: e.target.value }))}
                    placeholder="Min. 8 characters"
                    disabled={registering}
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-60"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-700">Confirm password</label>
                  <input
                    type="password"
                    value={data.confirmPassword}
                    onChange={(e) => setData((d) => ({ ...d, confirmPassword: e.target.value }))}
                    placeholder="••••••••"
                    disabled={registering}
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-60"
                  />
                </div>
              </div>

              {step2Error && <p className="mt-3 text-xs text-red-600">{step2Error}</p>}

              <div className="mt-6 flex gap-3">
                <button
                  onClick={() => setStep(1)}
                  disabled={registering}
                  className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 disabled:opacity-40"
                >
                  ← Back
                </button>
                <button
                  onClick={submitStep2}
                  disabled={registering}
                  className="flex-1 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {registering ? 'Creating account…' : 'Create account →'}
                </button>
              </div>
            </div>
          )}

          {/* ── Step 3: First Document (Optional) ───────────────────────── */}
          {step === 3 && (
            <div>
              <h2 className="mb-2 text-lg font-semibold text-slate-900">Upload your first document</h2>
              <p className="mb-5 text-sm text-slate-500">Optional — you can do this later from the admin panel.</p>

              <div
                onDrop={handleFileDrop}
                onDragOver={(e) => e.preventDefault()}
                onClick={() => fileInputRef.current?.click()}
                className="flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 p-8 text-center transition hover:border-indigo-400 hover:bg-indigo-50"
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx,.txt"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) setUploadFile(file);
                  }}
                />
                {uploadFile ? (
                  <p className="text-sm font-medium text-slate-800">{uploadFile.name}</p>
                ) : (
                  <>
                    <p className="text-sm text-slate-500">Drop a PDF, DOCX, or TXT here</p>
                    <p className="mt-1 text-xs text-slate-400">or click to browse</p>
                  </>
                )}
              </div>

              {uploading && (
                <div className="mt-3">
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
                    <div
                      className="h-full rounded-full bg-indigo-600 transition-all"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                  <p className="mt-1 text-center text-xs text-slate-500">{uploadProgress}%</p>
                </div>
              )}

              {uploadError && <p className="mt-3 text-xs text-red-600">{uploadError}</p>}

              <div className="mt-6 flex gap-3">
                <button
                  onClick={() => setStep(4)}
                  disabled={uploading}
                  className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 disabled:opacity-40"
                >
                  Skip for now
                </button>
                <button
                  onClick={handleUpload}
                  disabled={!uploadFile || uploading}
                  className="flex-1 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {uploading ? 'Uploading…' : 'Upload →'}
                </button>
              </div>
            </div>
          )}

          {/* ── Step 4: Done ────────────────────────────────────────────── */}
          {step === 4 && (
            <div className="text-center">
              <div className="mb-4 flex justify-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100 text-3xl">
                  🎉
                </div>
              </div>
              <h2 className="mb-2 text-lg font-semibold text-slate-900">You&apos;re all set!</h2>
              <p className="mb-6 text-sm text-slate-500">
                Your knowledge base is ready. Start querying your documents or upload more.
              </p>

              {/* Channel logos */}
              <div className="mb-6">
                <p className="mb-3 text-xs font-medium text-slate-500 uppercase tracking-wide">Also available on</p>
                <div className="flex items-center justify-center gap-6">
                  <div className="flex flex-col items-center gap-1">
                    <Image src="/whatsapp.png" alt="WhatsApp" width={40} height={40} className="rounded-lg" />
                    <span className="text-xs text-slate-500">WhatsApp</span>
                  </div>
                  <div className="flex flex-col items-center gap-1">
                    <Image src="/slack.png" alt="Slack" width={40} height={40} className="rounded-lg" />
                    <span className="text-xs text-slate-500">Slack</span>
                  </div>
                </div>
              </div>

              <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
                <button
                  onClick={() => router.push('/chat/new')}
                  className="rounded-md bg-indigo-600 px-6 py-2 text-sm font-medium text-white"
                >
                  Go to Chat
                </button>
                <button
                  onClick={() => router.push('/admin/documents')}
                  className="rounded-md border border-slate-300 px-6 py-2 text-sm font-medium text-slate-700"
                >
                  Upload More
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Already have an account */}
        {step < 4 && (
          <p className="mt-4 text-center text-xs text-slate-400">
            Already have an account?{' '}
            <a href="/login" className="text-indigo-600 hover:underline">Sign in</a>
          </p>
        )}
      </div>
    </main>
  );
}
