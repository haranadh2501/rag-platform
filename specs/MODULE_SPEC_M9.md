# MODULE_SPEC_M9 — Frontend: Chat Portal

**Owner**: Member 9 | **Track**: Frontend | **Branch**: `feat/chat-ui`

## Role
Next.js ChatGPT-style interface for querying the knowledge base with grounded answers and citations.

## Day-by-Day Deliverables
| Day | Deliverable | Done? |
|---|---|---|
| 1 | Wireframe chat layout. Study M3's mock response shape. | ☐ |
| 2 | Chat layout: sidebar (conversation list) + main chat area | ☐ |
| 2 | Message input component: textarea, send button, keyboard shortcuts | ☐ |
| 2 | Message display: user/assistant bubbles + Markdown rendering | ☐ |
| 3 | Source citations: collapsible panel with chunk text + page numbers + scores | ☐ |
| 3 | Follow-up question chips (clickable → auto-fills input) | ☐ |
| 3 | Conversation management: new chat, auto-title, load history | ☐ |
| 4 | Wire to real `POST /chat/query` endpoint | ☐ |
| 5 | Typing indicator (skeleton while waiting for n8n) | ☐ |
| 5 | Dark mode + mobile responsive | ☐ |
| 6 | Polish, search across conversations | ☐ |

## Files Owned
- `frontend/src/app/chat/`
- `frontend/src/components/chat/`

## Support Files (read/extend, not exclusively owned)
- `frontend/src/lib/chat/` — Chat Portal API client (`chatApi.ts`)
- `frontend/chat/types/` — canonical Chat Portal type contract (`chat.ts`); source of truth derived from `specs/openapi.yaml`

## Key Pages
```
/chat                  → redirects to /chat/new
/chat/new              → blank conversation
/chat/[conversation_id] → loaded conversation
```

## Component Structure
```
src/components/chat/
  ChatLayout.tsx        → sidebar + main area wrapper
  ConversationList.tsx  → list of past conversations
  MessageList.tsx       → scrollable message history
  MessageBubble.tsx     → single user/assistant bubble
  CitationsPanel.tsx    → collapsible citations accordion
  FollowUpChips.tsx     → clickable follow-up suggestions
  MessageInput.tsx      → textarea + send button
  TypingIndicator.tsx   → animated dots while waiting
```

## Mock Data Shape (from M3)
```typescript
interface ChatQueryResponse {
  answer: string
  sources: Array<{
    document_id: string
    title: string
    chunk_text: string
    page_number: number | null
    score: number
  }>
  follow_up_questions: string[]
  conversation_id: string
  faithfulness: number
  requires_clarification: boolean
  metadata: { model: string; retrieval_time_ms: number; chunks_retrieved: number }
}
```

## Citations Panel Design
```
[📄 Source 1] Product Manual — p.12 (score: 0.94)    ▼
  "...the relevant excerpt from the document showing the
   context that was used to generate this answer..."

[📄 Source 2] Quick Start Guide — p.3 (score: 0.87)  ▼
  "...second relevant excerpt..."
```

## Acceptance Criteria
- [x] Message sent → answer displayed with Markdown formatting
- [x] Citations panel shows document title + page + excerpt (collapsible), rendered per assistant message
- [x] Follow-up chips appear below the latest answer (driven by `ChatQueryResponse.follow_up_questions`, which has no per-message equivalent); clicking one sends the query
- [x] New conversation created on first message if no conversation_id
- [x] Conversation history loads on sidebar
- [x] Typing indicator shown while waiting for response
- [x] Works on mobile (responsive at 375px width)
- [ ] Dark mode toggle working — **shared-shell gap, not fully M9-owned**: `tailwind.config.ts` declares `darkMode: 'class'` but no `ThemeProvider`/toggle exists anywhere in the app (Admin UI included); requires app-shell-level work outside `frontend/src/app/chat/` and `frontend/src/components/chat/`.


---
<!-- AUTO-APPENDED:SKILLS-V1 -->
## Skills Required
- **Must-have:** Next.js 14, TypeScript, TailwindCSS, React state mgmt, Markdown rendering (`react-markdown`), streaming/SSE basics.
- **Nice-to-have:** `@uiw/react-md-editor`, syntax highlighting (`rehype-highlight`), zustand state, mobile-first design.

## Detailed Step-by-Step Plan
### Day 1 — Wireframe
1. Branch `feat/chat-ui`. Sketch layout: left sidebar (conversation list + "New chat" button) / center chat area / right collapsible "Sources" drawer.
2. Install `react-markdown` `rehype-highlight` `rehype-raw`.

### Day 2 — Message Components
3. `components/chat/Message.tsx`: user bubble (right, blue) vs assistant bubble (left, surface). Render markdown with code-block syntax highlighting.
4. `components/chat/CitationCard.tsx`: shows document title, page number, snippet, score. Click → opens Sources drawer.
5. `components/chat/FaithfulnessBadge.tsx`: green (≥0.85) / amber (0.7-0.85) / red (<0.7); tooltip explains "self-check score".

### Day 3 — Chat Page
6. `app/chat/[conversationId]/page.tsx`: load history via GET /chat/conversations/{id} (response embeds `messages[]` directly — there is no separate `/messages` sub-route), render message list, autoscroll bottom.
7. Input box at bottom: textarea + Send button (Cmd+Enter). On submit → POST /chat/query with conversation_id → append both messages.
8. Show typing indicator (3 bouncing dots) while waiting.

### Day 4 — Follow-ups + Clarifications
9. Render `follow_up_questions` as 3 clickable chips below assistant message; click sends as next query.
10. If `requires_clarification=true`, render a warning banner above the answer and highlight the badge red.

### Day 5 — Sidebar + Polish
11. `components/chat/Sidebar.tsx`: list conversations (GET /chat/conversations), highlight active, "New chat" → navigate to `/chat/new`, where the first message creates the conversation via POST /chat/query with conversation_id: null (there is no POST /chat/conversations endpoint).
12. Conversation title auto-generated from first user message (truncate 40 chars).
13. Dark mode default; light theme toggle.

### Day 6 — Mobile + Demo Prep
14. Test on iPhone-width (375 px). Drawer becomes full-screen on mobile.
15. Pre-seed 3 demo conversations for screenshots.

## Learning Resources
- react-markdown: https://github.com/remarkjs/react-markdown
- TailwindCSS chat UI patterns: https://tailwindui.com/components/application-ui/messaging
- Zustand: https://zustand-demo.pmnd.rs/
