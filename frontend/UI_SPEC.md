# UI_SPEC.md — IISc Grounded Agentic RAG Platform

> Frontend specification for Next.js 14 · TypeScript · TailwindCSS.
> Covers all three UI surfaces: Onboarding Wizard (M13), Admin Portal (M8), Chat Portal (M9).
> The central design concern is **trust**: every answer must visibly prove it came from a source document.

---

## 1. Guiding Principles

| Principle | Implication |
|---|---|
| Grounded answers only | Every assistant message must render citations. Uncited answers are a UX bug. |
| Faithfulness is first-class | The self-check score is not metadata — it is a badge on every response. |
| Inline evidence | Users should never have to click away to verify an answer; chunk text is shown inline. |
| Multi-tenant isolation | No cross-tenant data can leak visually — tenant context is always in scope. |
| Speed perception | Upload → queryable is < 2 min. Show live progress so the user knows something is happening. |
| Zero hallucination signal | When `requires_clarification` is true, the UI makes that unmistakable with a warning state. |

---

## 2. Design System

### 2.1 Color Tokens

| Token | Hex / Tailwind | Usage |
|---|---|---|
| `brand-primary` | `indigo-600` | Primary buttons, active nav, links |
| `brand-surface` | `slate-50` | Page backgrounds |
| `brand-card` | `white` | Card / panel backgrounds |
| `text-base` | `slate-900` | Body text |
| `text-muted` | `slate-500` | Labels, timestamps, metadata |
| `faithfulness-high` | `emerald-500` | Score ≥ 0.85 |
| `faithfulness-mid` | `amber-400` | 0.70 ≤ score < 0.85 |
| `faithfulness-low` | `red-500` | Score < 0.70 |
| `status-pending` | `slate-400` | Document ingestion pending |
| `status-processing` | `blue-500` | Document ingestion in progress |
| `status-completed` | `emerald-500` | Document ingestion done |
| `status-failed` | `red-500` | Document ingestion failed |
| `clarification-bg` | `amber-50` | Clarification-required banner background |
| `clarification-border` | `amber-400` | Clarification-required banner border |

Dark mode uses the same semantic tokens with `dark:` Tailwind variants. Default to dark mode; provide a toggle.

### 2.2 Typography

- Font family: system-ui stack (no custom font load — keep it fast).
- Scale: Tailwind default. `text-sm` for table cells and metadata; `text-base` for body; `text-lg/xl` for headings.
- Markdown inside assistant messages: rendered via `react-markdown` + `rehype-highlight`. Code blocks use `bg-slate-800 text-slate-100`.

### 2.3 Spacing & Layout

- Sidebar width: 240 px (collapsible on < 768 px screens).
- Max content width: 900 px centered for chat messages; full-width for admin tables.
- Card padding: `p-6`. Section gap: `gap-6`.

### 2.4 Iconography

Use Heroicons (already compatible with Tailwind). No icon fonts.

---

## 3. Route Map

```
/                            → Landing page (M13)
/onboarding                  → Onboarding wizard — 4 steps (M13)

/login                       → Shared login page

/admin                       → Redirects to /admin/documents
/admin/documents             → Document list + upload (M8)
/admin/documents/[id]        → Document detail (M8)
/admin/users                 → User list + invite (M8)
/admin/tenants               → Tenant list — super_admin only (M8 + M13)
/admin/settings              → Tenant settings (M8)

/chat                        → Redirects to /chat/new
/chat/new                    → Blank conversation (M9)
/chat/[conversation_id]      → Loaded conversation (M9)
```

Route guards: any `/admin/*` or `/chat/*` route requires a valid JWT. Redirect to `/login` with a `?next=` parameter on auth failure.

---

## 4. Landing Page (`/`)

Purpose: marketing entry point for businesses evaluating the platform.

### Layout

```
┌────────────────────────────────────────────────────┐
│  Logo                         [Log In]  [Get Started]│
├────────────────────────────────────────────────────┤
│                                                    │
│   Hero headline (2 lines, text-4xl bold)           │
│   "Upload your docs. Answer customer questions.    │
│    Every answer cites its source."                 │
│                                                    │
│   [Get Started — Free →]                           │
│                                                    │
├────────────────────────────────────────────────────┤
│  3-column feature strip:                           │
│  [📄 Any Document] [🔎 Grounded Answers] [🏢 Multi-tenant]│
├────────────────────────────────────────────────────┤
│  "How it works" — 3-step diagram                   │
│  Upload → Ask → Cited Answer                       │
├────────────────────────────────────────────────────┤
│  Footer: IISc branding · GitHub link               │
└────────────────────────────────────────────────────┘
```

- Static HTML — no API calls.
- "Get Started" → `/onboarding`.
- "Log In" → `/login`.

---

## 5. Onboarding Wizard (`/onboarding`)

Self-service flow to register a new tenant, create its first admin user, and optionally upload the first document. Calls `POST /onboarding/register` and `GET /onboarding/check-slug`.

### 5.1 Stepper Shell

```
┌──────────────────────────────────────────────────────┐
│  Logo                                                │
│                                                      │
│  ●───────●───────●───────○                           │
│  Company  Admin   Upload  Done                       │
│                                                      │
│  ┌────────────────────────────────────┐              │
│  │  [Step content renders here]       │              │
│  └────────────────────────────────────┘              │
│                            [Back] [Next →]           │
└──────────────────────────────────────────────────────┘
```

- Progress indicator: filled dots = completed steps, outlined = future.
- Validation runs on each step before `[Next]` is enabled.
- Error messages appear inline beneath the field, never in a toast.

### 5.2 Step 1 — Company Information

Fields:
- **Company Name** — free text, required, max 255 chars.
- **Company Slug** — lowercase alphanumeric + hyphens. Auto-generated from Company Name (debounce 400 ms), editable. Live availability check via `GET /onboarding/check-slug?slug=`. Show ✓ green / ✗ red inline beside the field. Blocked slugs: `admin`, `api`, `www`, `app`.
- **Plan** — dropdown: Free / Pro (default: Free).

### 5.3 Step 2 — Admin User

Fields:
- **Email** — format-validated.
- **Password** — min 8 chars. Show a 4-bar strength meter (weak / fair / good / strong) based on entropy.
- **Confirm Password** — must match; validated on blur.
- **Terms checkbox** — required to proceed.

On clicking "Next" on this step: fire `POST /onboarding/register` with all collected data. Show a full-width loading state ("Creating your workspace…") while the request is in flight. On success, store the returned `access_token` in an httpOnly cookie via a Next.js API route. On failure, show the error inline.

### 5.4 Step 3 — Upload First Document (Optional)

```
┌───────────────────────────────────────────┐
│  📂  Drop a PDF here, or click to browse  │
│      (max 25 MB · PDF, DOCX, TXT)         │
│                                           │
│  [ Skip for now ]    [ Upload → ]         │
└───────────────────────────────────────────┘
```

- Drag-and-drop zone.
- On file drop: validate MIME client-side (PDF/DOCX/TXT only), reject > 25 MB with a friendly message before upload.
- On upload: `POST /admin/documents/upload` (multipart). Show inline progress bar with file name.
- After upload completes: show "Document received — it will be queryable in about 2 minutes" banner. Do not wait for `completed` status here — move to Step 4 automatically.
- "Skip for now" advances immediately to Step 4 without upload.

### 5.5 Step 4 — Done

```
┌───────────────────────────────────────────┐
│  Your knowledge base is ready!            │
│                                           │
│  Tenant: acme-corp                        │
│  Admin:  admin@acme-corp.com              │
│                                           │
│  [ Go to Chat ]    [ Upload More Docs ]   │
└───────────────────────────────────────────┘
```

- "Go to Chat" → `/chat/new`.
- "Upload More Docs" → `/admin/documents`.
- If a document was uploaded in Step 3, show a subtle progress indicator: "Ingesting document… (usually < 2 min)". Poll `GET /admin/documents` every 5 s; swap the indicator to "Ready to query!" when status becomes `completed`.

---

## 6. Shared Login Page (`/login`)

```
┌────────────────────────────────┐
│  Logo                          │
│                                │
│  Email    [________________]   │
│  Password [________________]   │
│                                │
│  [Log In]                      │
│                                │
│  New here? → /onboarding       │
└────────────────────────────────┘
```

- Calls `POST /auth/login`. Stores JWT in httpOnly cookie.
- On 401: show "Invalid email or password" inline under the password field.
- On success: redirect to `?next` parameter or `/admin/documents` (admin role) / `/chat` (user role).
- No "forgot password" in MVP.

---

## 7. Admin Portal

Shared layout: sidebar + top header + content area.

### 7.1 Admin Layout

```
┌──────────┬────────────────────────────────────────┐
│          │ Header: tenant name   [User ▾] [Logout] │
│ Sidebar  ├────────────────────────────────────────┤
│          │                                        │
│ Documents│  [Page content]                        │
│ Users    │                                        │
│ Tenants* │                                        │
│ Settings │                                        │
│          │                                        │
│ [Chat →] │                                        │
└──────────┴────────────────────────────────────────┘
```

- "Tenants" nav item is only rendered for `super_admin` role.
- "[Chat →]" link at the bottom of the sidebar navigates to `/chat`.
- On mobile (< 768 px): sidebar collapses to a hamburger menu.

### 7.2 Documents Page (`/admin/documents`)

This is the primary admin workflow page.

**Upload area (top of page)**

Two tabs: "Upload File" and "Add by URL".

Upload File tab:
```
┌──────────────────────────────────────────────────────┐
│  📁  Drag & drop PDF, DOCX, or TXT here              │
│      or  [Browse files]                              │
│      Max 25 MB per file · 20 uploads/hour             │
└──────────────────────────────────────────────────────┘
```

Add by URL tab:
```
  URL:   [https://example.com/manual.pdf_________] [Ingest]
  Title: [Optional title______________________]
```

Both call the appropriate endpoint. On submission, a new row immediately appears at the top of the document table with `status: pending`. Rows with `pending` or `processing` status are polled every 5 s.

**Document table**

| # | Title | Type | Status | Chunks | Uploaded | Actions |
|---|---|---|---|---|---|---|
| 1 | Product Manual | PDF | ● Completed | 142 | 2 min ago | Detail · Delete |
| 2 | IT SOP Guide | DOCX | ⟳ Processing | — | 30 s ago | — |
| 3 | Quick Start | URL | ● Pending | — | just now | — |
| 4 | Old Policy | TXT | ✕ Failed | — | 1 day ago | Retry · Delete |

Status badge rendering:
- `pending` — slate dot, "Pending"
- `processing` — blue spinning circle, "Processing…"
- `completed` — emerald filled dot, "Completed"
- `failed` — red X, "Failed" with a tooltip showing `error_message`

Filter bar above the table: filter by status (all / pending / processing / completed / failed). Pagination: 20 rows per page with `< Prev   1 of 5   Next >` controls.

**Storage quota bar**

Below the table header:
```
Storage used: ████████░░░░░░░░░  420 MB of 1 GB
```

Fetched from tenant metadata. Turns amber at 80 %, red at 95 %.

### 7.3 Document Detail Page (`/admin/documents/[id]`)

```
┌────────────────────────────────────────────────┐
│ ← Back to Documents                            │
│                                                │
│ Product Manual                                 │
│ Type: PDF   Status: ● Completed   Chunks: 142  │
│ Uploaded: 2026-06-01 10:30                     │
│                                                │
│ Source: /uploads/product-manual.pdf            │
│                                                │
│                        [Delete Document]       │
└────────────────────────────────────────────────┘
```

Delete is a destructive action: show a confirmation dialog ("Are you sure? This will remove all 142 chunks from the knowledge base.") before calling `DELETE /admin/documents/{id}`.

### 7.4 Users Page (`/admin/users`)

**User table**

| Email | Role | Active | Joined | Actions |
|---|---|---|---|---|
| admin@acme.com | Admin | ✓ | 2026-06-01 | — |
| user@acme.com | User | ✓ | 2026-06-01 | Deactivate |

Role pills: `super_admin` = indigo, `admin` = blue, `user` = slate.

**Invite User panel** (shown in a slide-over drawer or modal):

```
  Email:    [______________]
  Role:     [User ▾]
  [Send Invite]
```

Calls `POST /admin/users/invite`. On success: new row appears in the table.

### 7.5 Tenants Page (`/admin/tenants`) — super_admin only

| Tenant | Slug | Plan | Active | Created | Actions |
|---|---|---|---|---|---|
| Acme Corp | acme-corp | Free | ✓ | 2026-06-01 | Edit |
| Beta Co | beta-co | Pro | ✓ | 2026-05-30 | Edit · Deactivate |

Create New Tenant button opens a modal with Company Name, Slug, Plan fields. Calls `POST /admin/tenants`.

Edit opens a modal that calls `PATCH /admin/tenants/{id}`. Deactivate sets `is_active: false`; show confirmation dialog first.

### 7.6 Settings Page (`/admin/settings`)

- **Tenant info**: name, slug (read-only), plan badge.
- **Channel status**: icons for Web, WhatsApp, Slack — green if configured in backend, grey if not.
- **Rate limits**: "20 uploads / hour" displayed as informational text.

---

## 8. Chat Portal

The primary end-user interface. Users ask questions and receive grounded, cited answers.

### 8.1 Chat Layout

```
┌──────────────┬──────────────────────────────────────────┐
│              │ Header: Knowledge Base Name        [Admin]│
│ Sidebar      ├──────────────────────────────────────────┤
│              │                                          │
│ [+ New Chat] │  Message list (scrollable)               │
│              │                                          │
│ Past chats:  │  [User bubble]                           │
│ · IT helpdesk│  [Assistant bubble + Citations]          │
│ · Device FAQ │  [User bubble]                           │
│ · Setup guide│  [Assistant bubble + Citations]          │
│              │                                          │
│              │ ──────────────────────────────────────── │
│              │  [Message input                    Send] │
└──────────────┴──────────────────────────────────────────┘
```

- Sidebar lists conversations from `GET /chat/conversations`. Clicking one navigates to `/chat/[conversation_id]`.
- "+ New Chat" creates a new blank conversation (client-side; no API call until first message is sent).
- On mobile: sidebar is a full-screen drawer triggered by a menu button.

### 8.2 Message Bubbles

**User bubble** (right-aligned, `indigo-100` background):
```
                               How do I reset the device? │
                                               10:32 AM ▪ │
```

**Assistant bubble** (left-aligned, `white`/`slate-800` dark background):
```
│ To reset the device, press and hold the power button for │
│ 5 seconds until the LED blinks red. Release, then press  │
│ once to restart. [Manual, p.12]                          │
│                                                          │
│ Faithfulness  ████████░░  0.92  ●                        │
│ 1100 ms · 5 chunks · deepseek-v4-flash                   │
│                                                          │
│ ▼ Sources (2)                                            │
│ ▼ Suggested follow-ups                                   │
│                                              10:32 AM ▪  │
```

Markdown is rendered inside assistant bubbles (headers, bold, code blocks, lists).

### 8.3 Faithfulness Badge

This is the most critical RAG quality indicator. It must appear on every assistant message.

```
Faithfulness  ████████░░  0.92  ●
```

- Numeric score (0.00–1.00), two decimal places.
- Filled bar proportional to score.
- Dot color: emerald ≥ 0.85 · amber 0.70–0.84 · red < 0.70.
- Tooltip on hover: "Self-check score from Gemini 3.5 Flash. Measures how well the answer is supported by retrieved source chunks. Scores below 0.70 trigger an automatic retry with a stronger model."

**Low faithfulness state** (score < 0.70):
- Badge is visually prominent (red, pulsing border).
- Add a subtle disclaimer below the answer: "This answer has a low grounding score — verify against the source documents before acting on it."

### 8.4 Clarification-Required State

When `requires_clarification: true` is returned:

```
┌──────────────────────────────────────────────────────┐
│ ⚠  The assistant needs more context to answer this.  │
│    Please clarify your question.                     │
└──────────────────────────────────────────────────────┘
[Answer text from the assistant, if any]
```

- Banner uses `amber-50` background, `amber-400` left border.
- Faithfulness badge is hidden (not applicable when clarification is requested).

### 8.5 Citations Panel

Collapsible accordion below each assistant message. Closed by default on desktop; open by default on first message.

```
▼ Sources (2)

  📄 Product Manual · p.12 · score 0.94
  ┌──────────────────────────────────────────────────────┐
  │ "…press and hold the power button for 5 seconds      │
  │  until the LED blinks red. Release, then press once  │
  │  to restart the device…"                             │
  └──────────────────────────────────────────────────────┘

  📄 Quick Start Guide · p.3 · score 0.87
  ┌──────────────────────────────────────────────────────┐
  │ "…the factory reset procedure is documented in       │
  │  Section 4 of the Product Manual…"                   │
  └──────────────────────────────────────────────────────┘
```

Each source shows:
- Document title (links to `/admin/documents/[id]` if the user has admin role).
- Page number if available (`p.12`) — omit if `null`.
- Similarity score rounded to 2 decimal places.
- The full `chunk_text` in a monospace-bordered block.

Scores are color-coded: `> 0.90` emerald text, `0.75–0.90` amber, `< 0.75` slate muted.

**Context Precision signal**: the score beside each chunk is the Voyage reranker score. High scores on the top-ranked chunks indicate high context precision. The UI does not compute this — it displays the raw scores returned by the backend. A future enhancement can aggregate and label it, but for MVP the per-chunk scores are sufficient evidence.

**Context Recall signal**: the `chunks_retrieved` field in `metadata` indicates how many chunks were used. The metadata line below the faithfulness badge shows this:

```
1100 ms · 5 chunks · deepseek-v4-flash
```

If `chunks_retrieved` is 0 and the answer was generated, show a warning: "No matching source chunks were retrieved. This answer may not be grounded."

### 8.6 Follow-Up Question Chips

Rendered below the citations panel as clickable chips:

```
  Suggested follow-ups:
  [How do I factory reset?]  [What's the LED indicator meaning?]  [Where is the power button?]
```

- Clicking a chip inserts the text into the message input and immediately submits it.
- Chips are only rendered if `follow_up_questions` is non-empty.
- Max 3 chips per message.

### 8.7 Message Input

```
┌────────────────────────────────────────────────────────┐
│  Ask a question about your documents...                │
│                                                        │
│                                         [Send ↵ Cmd+↵] │
└────────────────────────────────────────────────────────┘
```

- `textarea` that grows with content (max 8 lines before scrolling).
- Submit on `Cmd+Enter` (Mac) / `Ctrl+Enter` (Windows). `Enter` alone adds a newline.
- Disabled (with a spinner) while a request is in flight.
- Max 2000 characters; show character count when > 1800.

### 8.8 Typing Indicator

Shown while `POST /chat/query` is awaiting a response:

```
│ ● ● ●  ← three dots animating left-to-right
```

Appears as an assistant bubble with no text content. Replaced by the real message when the response arrives.

### 8.9 Conversation Management

- Conversations are auto-titled from the first user message (truncated to 40 characters) on the client side — no extra API call needed.
- Conversation history loads via `GET /chat/conversations/{id}` on route navigation.
- "Delete conversation" option (three-dot menu on each sidebar item): calls `DELETE /chat/conversations/{id}`, removes from sidebar, redirects to `/chat/new`.

---

## 9. RAG Quality Indicators — Reference Table

This table maps each RAG quality concept to its UI representation.

| Concept | Data Source | UI Location | Visual Treatment |
|---|---|---|---|
| **Faithfulness** | `ChatQueryResponse.faithfulness` | Below every assistant message | Colour-coded score badge + filled bar |
| **Grounding / Citation Coverage** | `ChatQueryResponse.sources` | Collapsible citations panel | One block per source chunk; absent = warning |
| **Context Precision** | `SourceChunk.score` (per chunk) | Per-chunk score label in citations panel | Emerald > 0.90, amber 0.75–0.90, slate < 0.75 |
| **Context Recall** | `ChatQueryResponse.metadata.chunks_retrieved` | Metadata line below badge | "N chunks" — 0 chunks triggers warning |
| **Answer Relevance** | `requires_clarification` | Warning banner + hidden badge | Amber banner when true |
| **Model Fallback** | `metadata.model` | Metadata line below badge | `deepseek-v4-pro` displayed in amber to signal retry was triggered |
| **Retrieval Speed** | `metadata.retrieval_time_ms` | Metadata line below badge | Displayed in ms; no colour coding in MVP |

---

## 10. Component Inventory

The following components are required across the three surfaces. File paths match module ownership.

### Shared (`frontend/src/components/`)

| Component | Purpose |
|---|---|
| `AuthGuard` | Wraps protected routes; redirects to /login |
| `ToastProvider` | Global toast notifications (success / error) |
| `ConfirmDialog` | Reusable confirmation modal for destructive actions |
| `StatusBadge` | Renders `pending / processing / completed / failed` pills |
| `Spinner` | Inline loading spinner |
| `DragDropZone` | Reusable file drop target |

### Admin (`frontend/src/components/admin/`)

| Component | Purpose |
|---|---|
| `AdminLayout` | Sidebar + header shell |
| `DocumentTable` | Paginated, polled document list |
| `DocumentUploadPanel` | Tabbed upload / URL ingest form |
| `StorageQuotaBar` | Storage usage progress bar |
| `UserTable` | User list with role pills |
| `InviteUserDrawer` | Slide-over for inviting a user |
| `TenantTable` | Tenant list (super_admin only) |
| `TenantModal` | Create / edit tenant |

### Chat (`frontend/src/components/chat/`)

| Component | Purpose |
|---|---|
| `ChatLayout` | Sidebar + chat area shell |
| `ConversationList` | Sidebar conversation links |
| `MessageList` | Scrollable message history |
| `MessageBubble` | Single user or assistant message |
| `FaithfulnessBadge` | Score + bar + colour + tooltip |
| `CitationsPanel` | Collapsible accordion of source chunks |
| `FollowUpChips` | Clickable suggestion chips |
| `MessageInput` | Textarea + send button |
| `TypingIndicator` | Animated placeholder bubble |
| `ClarificationBanner` | Amber warning for `requires_clarification` |

### Onboarding (`frontend/src/app/onboarding/`)

| Component | Purpose |
|---|---|
| `OnboardingWizard` | Step shell with progress indicator |
| `StepCompanyInfo` | Company name + slug + plan |
| `StepAdminUser` | Email + password + strength meter |
| `StepDocumentUpload` | Optional first document upload |
| `StepDone` | Success state with CTA buttons |
| `SlugAvailabilityInput` | Debounced slug field with live check |
| `PasswordStrengthMeter` | 4-bar entropy meter |

---

## 11. State Management

No global state library required for MVP. Use React context for:

- **`AuthContext`** — current user, JWT presence, `login()`, `logout()` methods.
- **`ToastContext`** — queue of toast messages.

Chat message state is local to `MessageList` / the conversation page.

Polling for document status (in Admin document table and Onboarding Step 4) is handled with `useEffect` + `setInterval`. Clear the interval when the component unmounts or when all relevant rows reach a terminal state (`completed` or `failed`).

SWR or TanStack Query may be introduced in a follow-up sprint to handle caching and revalidation, but are not required for the initial implementation.

---

## 12. API Integration Notes

- All authenticated calls attach `Authorization: Bearer <token>` from the cookie-stored JWT.
- 401 responses from any endpoint trigger an automatic logout + redirect to `/login?next=<current-path>`.
- 429 responses (rate limit) show a toast: "You've reached the upload limit (20/hour). Please wait and try again."
- Multipart uploads (`/admin/documents/upload`) should stream progress using the `XMLHttpRequest.upload.onprogress` event — not `fetch`, which does not expose upload progress natively.
- The `MOCK_N8N=true` backend mode returns a canned `ChatQueryResponse`. During frontend development, the citations panel, faithfulness badge, and follow-up chips should all render correctly with mock data. The mock response must be treated as spec-compliant — do not special-case the mock.

---

## 13. Accessibility & Responsive Requirements

- All interactive elements are keyboard-navigable with visible focus rings (`focus-visible:ring-2 ring-indigo-500`).
- All images and icon-only buttons have `aria-label`.
- Status badges use both colour and text (not colour alone) to convey meaning.
- The citations panel is an HTML `<details>`/`<summary>` element or equivalent ARIA accordion.
- Faithfulness badge tooltip is accessible via keyboard (`role="tooltip"`, linked by `aria-describedby`).
- Minimum touch target: 44 × 44 px for all buttons on mobile.
- Chat layout tested at 375 px (iPhone SE), 768 px (tablet), 1280 px (desktop).
- On mobile (< 768 px): sidebar becomes a full-screen drawer; citations panel expands to full-width below the message.

---

## 14. Error & Empty States

| Scenario | Component | Treatment |
|---|---|---|
| No documents uploaded yet | Document table | Illustration + "Upload your first document" CTA |
| No conversations yet | Conversation sidebar | "Ask your first question →" hint |
| Document ingestion failed | Status badge | Red badge + tooltip with `error_message` + "Retry" action |
| `sources` array is empty on an answer | Citations panel | Warning: "No source chunks — this answer may not be grounded" |
| `faithfulness` < 0.70 | Faithfulness badge | Red badge + disclaimer text beneath answer |
| `requires_clarification` is true | ClarificationBanner | Amber banner replaces badge |
| Network error on chat query | MessageBubble | Error state bubble: "Could not reach the server. Try again." with retry button |
| 0 chunks retrieved | Metadata line | "0 chunks" displayed in red; warning message appended |

---

## 15. Out of Scope (v1)

The following are explicitly not required in this sprint:

- Real-time streaming of assistant tokens (SSE / WebSocket). The UI shows a typing indicator until the full response arrives.
- Search across conversation history.
- Markdown export of conversations.
- In-UI RAGAS dashboard (evaluation results are in `evaluation/` — not surfaced in the UI).
- Custom branding per tenant.
- Stripe / payment UI.
- Voice interface.
- Notifications (email, push) on document ingestion completion.
