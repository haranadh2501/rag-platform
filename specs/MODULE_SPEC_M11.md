# MODULE_SPEC_M11 — Documentation & Demo
Owner: Member 11 | Track: Docs | Branch: feat/docs

## Role
README, Sphinx documentation site (published to GitHub Pages), architecture diagrams, setup guides, demo dataset (3 tenant companies), demo script, presentation slides.

## Day-by-Day Deliverables
| Day | Deliverable | Done? |
|---|---|---|
| 1 | Start README with architecture diagram. Define 3 demo companies. | ☐ |
| 1 | Set up Sphinx skeleton (conf.py, MyST, Furo theme) — local build works | ☐ |
| 2 | API documentation supplement (beyond Swagger auto-gen) — via Sphinx autodoc | ☐ |
| 2 | Set up GitHub Pages auto-deploy (Actions workflow on push to main) | ☐ |
| 3 | n8n setup guide: import workflows + configure credentials | ☐ |
| 3 | Docker deployment guide: step-by-step from zero to running | ☐ |
| 4 | Demo dataset: 3 tenants with different document sets | ☐ |
| 5 | Seed script for demo: auto-create tenants + upload docs | ☐ |
| 5 | Record demo video OR prepare live demo script | ☐ |
| 6 | Architecture decision records (ADRs). Presentation slides. Final review. | ☐ |

## Files Owned
docs/
docs/conf.py
docs/requirements.txt (docs build deps)
.github/workflows/docs.yml
evaluation/sample-data/
README.md (with M1)

## Demo Companies
| Company | Industry | Document Types | Slug |
|---|---|---|---|
| Siemens Support | Consumer appliances | Dishwasher manuals, error codes | Siemens-support |
| TechDesk IT | Corporate IT helpdesk | SOPs, troubleshooting runbooks | techdesk-it |
| IndEquip Co | Industrial equipment | Maintenance guides, safety manuals | indequip-co |

## Demo Script (Day 6 rehearsal)
1. Open http://localhost:3000/onboarding
2. Register "Siemens Support" tenant (live, 30 seconds)
3. Upload 2 PDFs: dishwasher_manual.pdf + error_codes.pdf
4. Wait for status: completed (< 2 minutes)
5. Open Chat portal → ask: "How do I fix error E15?"
6. Show: grounded answer + citations panel + follow-up chips
7. Open WhatsApp on phone → send same question to Twilio sandbox
8. Show: WhatsApp reply received with answer
9. Demo tenant isolation: log in as Bosch → search for IT helpdesk content → "I don't have enough information"

## n8n Setup Guide Template
# n8n Workflow Setup

1. Open http://localhost:5678
2. Log in (admin / n8nadmin)
3. Go to Workflows → Import from file
4. Import: n8n-workflows/ingestion-pipeline.json
5. Import: n8n-workflows/retrieval-pipeline.json
6. Configure credentials:
   - OpenAI API: Settings → Credentials → New → OpenAI
   - Postgres: Settings → Credentials → New → PostgreSQL
     host: postgres, port: 5432, db: ragplatform
7. Activate both workflows (toggle to Active)
8. Test: send POST to http://localhost:5678/webhook/retrieve

## Sphinx + GitHub Pages Setup Template
# Sphinx docs → GitHub Pages

1. Install:
   pip install sphinx furo myst-parser sphinxcontrib-mermaid sphinx-copybutton
2. Scaffold:
   sphinx-quickstart docs   (accept defaults)
3. In docs/conf.py:
   extensions = ["myst_parser", "sphinx.ext.autodoc", "sphinx.ext.napoleon",
                 "sphinx.ext.autosummary", "sphinxcontrib.mermaid", "sphinx_copybutton"]
   html_theme = "furo"
   source_suffix = {".rst": "restructuredtext", ".md": "markdown"}
   # autodoc imports your code in CI — mock heavy deps so the build doesn't need them:
   autodoc_mock_imports = ["pinecone", "langgraph", "openai", "llama_parse", "slack_bolt"]
4. Build locally:
   sphinx-build -b html docs docs/_build/html
5. Add .github/workflows/docs.yml (below)
6. Repo → Settings → Pages → Source = GitHub Actions
7. Push to main → site live at https://<org>.github.io/<repo>/

# .github/workflows/docs.yml
name: Docs
on:
  push:
    branches: [main]
  workflow_dispatch:
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: false
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r docs/requirements.txt
      - run: sphinx-build -b html -W docs docs/_build/html
      - run: touch docs/_build/html/.nojekyll   # so _static/ assets load on Pages
      - uses: actions/upload-pages-artifact@v3
        with:
          path: docs/_build/html
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4

# GitHub-side setup (one-time)
The Sphinx build runs on the GitHub runner — no local install needed. Building locally (step 4 above) is only for preview.
Two things to set up in GitHub:
  1. Commit .github/workflows/docs.yml — GitHub auto-detects anything under .github/workflows/ (or: Actions tab → New workflow → set up a workflow yourself → paste → commit).
  2. Repo → Settings → Pages → Build and deployment → Source = "GitHub Actions" (NOT "Deploy from a branch").
Then push to main → watch the Actions tab → the deploy job prints the live URL (also shown at the top of Settings → Pages): https://<org>.github.io/<repo>/
Notes:
  - No token/secret to create — the permissions block (pages: write / id-token: write) authenticates via OIDC.
  - Source must be "GitHub Actions", not a gh-pages branch, or deploy-pages won't pick up the artifact.
  - Private repo: serving Pages may require a paid plan (Pro/Team); public repos are free.

## Acceptance Criteria
- [ ] README has working Quick Start (tested on clean machine)
- [ ] Sphinx docs build cleanly (sphinx-build -W) and render the API reference
- [ ] GitHub Pages site live; auto-deploys on push to main (.nojekyll present so assets load)
- [ ] n8n setup guide lets someone import workflows in < 10 minutes
- [ ] Docker guide: docker compose up works following the guide
- [ ] 3 demo companies with sample documents in evaluation/sample-data/
- [ ] Demo script rehearsed — runs in < 10 minutes
- [ ] Presentation slides exported as PDF in docs/

## Skills Required
Must-have: Technical writing, Markdown / MyST, Sphinx (conf.py, autodoc), GitHub Actions / Pages, screenshots, Excalidraw / Mermaid, presentation skills.
Nice-to-have: ScreenToGif / OBS for demo recording, Figma, video editing basics.

## Detailed Step-by-Step Plan
### Day 1 — README Polish
Pull repo. Read ARCHITECTURE.md, docs/DEPLOYMENT.md, docs/DEMO.md end-to-end.
Rewrite README.md top section with: hero blurb, 1-screenshot, badges (build/coverage/license + docs), 5-line quickstart.
Scaffold Sphinx in docs/ (conf.py: MyST + Furo + autodoc + mermaid); get sphinx-build to produce HTML locally.
Add .github/workflows/docs.yml; set Settings → Pages → Source = GitHub Actions; land first green deploy → site live at https://<org>.github.io/<repo>/.

### Day 2 — Sample Data
Define 3 demo tenant companies and pull their public PDFs:
Tenant A "MakeCo": 2-3 product manuals.
Tenant B "HelpDeskCo": IT SOPs.
Tenant C "MaintainCo": maintenance guides.
Store under evaluation/sample-data/<tenant>/.

### Day 3 — Diagrams
Refine 3 Excalidraw files in docs/diagrams/: open at https://excalidraw.com → File → Open → save back to .excalidraw. Export PNG to docs/diagrams/png/ for slides.
Mermaid diagrams render inline in the Sphinx site via sphinxcontrib-mermaid (and still render on GitHub).

### Day 4 — ADRs (Architecture Decision Records)
Create docs/adr/ with one MD file per decision (added to the Sphinx toctree so they're browsable on the site):
001-why-voyage-embeddings.md
002-deepseek-vs-openai.md
003-no-redis.md
004-ephemeral-uploads-pattern-A.md
005-mcp-server.md

### Day 5 — Demo Script + Slides
Build 10-slide deck (Google Slides / PPT): problem → solution → architecture → demo screenshots → cost → roadmap.
Walk through docs/DEMO.md 3 times; refine timing.

### Day 6 — Record
Record 3-min demo video (OBS, 1080p): Web UI chat → WhatsApp upload → Claude Desktop MCP → eval scores. Upload to YouTube unlisted, link in README.

## Learning Resources
ADR format: https://github.com/joelparkerhenderson/architecture-decision-record
Excalidraw: https://excalidraw.com
Mermaid live editor: https://mermaid.live
Sphinx: https://www.sphinx-doc.org
MyST parser: https://myst-parser.readthedocs.io
Furo theme: https://pradyunsg.me/furo/
GitHub Pages: https://docs.github.com/en/pages
