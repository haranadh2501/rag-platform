# Grounded Agentic RAG Platform

> Enterprise-grade multi-tenant AI knowledge platform that transforms organizational documents into a trustworthy, citation-backed assistant across Web, WhatsApp, and Slack.

[![Team](https://img.shields.io/badge/team-14%20members-6366f1?style=flat-square)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi&logoColor=white)]()
[![Next.js](https://img.shields.io/badge/Next.js-14-black?style=flat-square&logo=next.js)]()
[![n8n](https://img.shields.io/badge/n8n-RAG%20Engine-EA4B71?style=flat-square)]()
[![pgvector](https://img.shields.io/badge/pgvector-1024--dim%20HNSW-4169E1?style=flat-square&logo=postgresql&logoColor=white)]()
[![DeepSeek](https://img.shields.io/badge/DeepSeek-V4%20Flash-0066FF?style=flat-square)]()
[![Voyage](https://img.shields.io/badge/Voyage-embed%20%2B%20rerank-7C3AED?style=flat-square)]()
[![License](https://img.shields.io/badge/license-MIT-22c55e?style=flat-square)]()

## Overview
Organizations already possess vast amounts of knowledge in the form of manuals, SOPs, onboarding guides, troubleshooting documents, policies, FAQs, and internal documentation. However, finding the right information often requires human experts, resulting in slow support cycles and repetitive responses.

The Grounded Agentic RAG Platform enables organizations to upload their knowledge once and make it instantly accessible through AI-powered self-service channels. Every response is generated from retrieved evidence, accompanied by source citations, and validated through a self-checking pipeline to minimize hallucinations.

The platform is designed for:

Customer Support
Technical Troubleshooting
Employee Onboarding
IT Helpdesk
Product Documentation Search
Enterprise Knowledge Management

## Architecture

The platform follows a decoupled architecture where FastAPI acts as a lightweight gateway and n8n orchestrates all AI workflows.

```mermaid
flowchart LR
    subgraph Clients
        Web["Web UI<br/>Next.js 14"]
        WA["WhatsApp<br/>Twilio Sandbox"]
        MCP["MCP Clients<br/>Claude Desktop / Cursor"]
    end

    subgraph Edge["Gateway · Railway"]
        API["FastAPI<br/>(thin gateway)"]
        MCPSrv["/mcp/* JSON-RPC"]
    end

    subgraph RAG["n8n · RAG Engine"]
        Ingest["Ingestion WF<br/>parse + OCR + chunk + embed"]
        Retrieve["Agentic Retrieval WF<br/>plan → tools → self-check"]
        Ephemeral["Ephemeral Ingest WF<br/>1-hour TTL"]
    end

    subgraph Data["Neon Postgres + pgvector"]
        DocChunks[("document_chunks<br/>vector(1024)")]
        EphChunks[("ephemeral_chunks<br/>vector(1024) TTL=1h")]
        Meta[("tenants · users · documents<br/>conversations · messages")]
    end

    subgraph Providers["AI Providers"]
        Voyage["Voyage<br/>embed + rerank"]
        DSFlash["DeepSeek V4 Flash<br/>(primary gen)"]
        DSPro["DeepSeek V4 Pro<br/>(hard fallback)"]
        Gemini["Gemini 3.5 Flash<br/>(self-check)"]
        OAI["OpenAI gpt-4o-mini<br/>(vision OCR + insurance)"]
    end

    Web -->|JWT| API
    WA  -->|webhook| API
    MCP -->|JSON-RPC| MCPSrv
    MCPSrv --> API
    API   -->|POST /webhook/retrieve| Retrieve
    API   -->|POST /webhook/ingest| Ingest
    API   -->|POST /webhook/ingest-ephemeral| Ephemeral

    Ingest    --> Voyage
    Ingest    --> OAI
    Ingest    --> DocChunks
    Ephemeral --> Voyage
    Ephemeral --> EphChunks
    Retrieve  --> Voyage
    Retrieve  --> DocChunks
    Retrieve  --> EphChunks
    Retrieve  --> DSFlash
    Retrieve  --> Gemini
    Retrieve  --> DSPro
    API --> Meta
```



See [ARCHITECTURE.md](ARCHITECTURE.md) for full diagrams and data flows.

## Design Principle

> **FastAPI acts as a thin gateway.** The API layer never performs LLM operations directly. All AI functionality—including OCR, chunking, embedding generation, retrieval, reranking, grounded response generation, and answer verification—is orchestrated through dedicated n8n workflows. This separation of concerns improves modularity, maintainability, scalability, and operational reliability.

---

## Technology Stack

| Layer               | Technology               |
| ------------------- | ------------------------ |
| Frontend            | Next.js 14, Tailwind CSS |
| API Gateway         | FastAPI                  |
| Workflow Engine     | n8n                      |
| Database            | PostgreSQL               |
| Vector Search       | pgvector                 |
| Object Storage      | Cloudflare R2            |
| Embeddings          | Voyage AI                |
| Reranking           | Voyage AI                |
| Primary Generation  | DeepSeek V4 Flash        |
| Fallback Generation | DeepSeek V4 Pro          |
| Verification        | Gemini Flash             |
| OCR & Vision        | GPT-4o Mini              |

---

## Evaluation Results

The platform was evaluated using a **148-case multi-domain benchmark suite** spanning troubleshooting, onboarding, customer support, technical documentation, and operational knowledge workflows.

| Metric                     | Score         |
| -------------------------- | ------------- |
| Answer Relevancy           | **0.953**     |
| Context Precision          | **0.979**     |
| Context Recall             | **0.923**     |
| Citation Coverage          | **1.000**     |
| Successful Requests        | **148 / 148** |
| Unanswerable Query Refusal | **16 / 16**   |
| Faithfulness               | **0.830**     |

### Key Findings

* Strong retrieval quality across multiple application domains.
* High citation coverage with source-backed responses.
* Reliable refusal of unanswerable questions.
* Excellent context precision and recall.
* Future improvements focus on faithfulness optimization and latency reduction.

---

## Team
| Member                           | Role                                                                                       |
| -------------------------------- | ------------------------------------------------------------------------------------------ |
| **Shantha Suresh M**             | Tech Lead, System Architecture, Infrastructure, Platform Integration & Customer Onboarding |
| **Keshav Kumar**                 | Backend Foundations, Authentication & Core Services                                        |
| **Karthic V**                    | Document Management APIs, Admin APIs & Cloudflare R2 Integration                           |
| **Tushar Srivastava**            | Unified Messaging, Slack & WhatsApp Integration                                            |
| **Kumari Priyanka**              | n8n Ingestion Pipeline                                                                     |
| **Shreya Shrivastava**           | Agentic Retrieval, RAG & Generation Pipeline                                               |
| **Ritika Gupta**                 | Frontend Admin Portal & API Integration                                                    |
| **Joy Das**                      | Frontend Chat Portal, UI Integration, Documentation & Platform Integration                 |
| **Himanshu Arora**               | Evaluation, Testing & Microsoft Teams Integration                                          |
| **Yashas H M**                   | Evaluation, Reporting & Quality Assurance                                                  |
| **Harshit Agarwal**              | WhatsApp Bot Integration                                                                   |
| **Banda Venkata Bhava Haranadh** | Ephemeral Session RAG & Temporary Knowledge Store                                          |



## Documentation
- [CLAUDE.md](CLAUDE.md) — AI assistant instructions + project overview
- [PROJECT_SPEC.md](PROJECT_SPEC.md) — Goals, scope, success criteria
- [ARCHITECTURE.md](ARCHITECTURE.md) — System design, data flows, DB schema
- [SKILLS.md](SKILLS.md) — Platform capabilities reference
- [TEAM_WORKFLOW.md](TEAM_WORKFLOW.md) — PR rules, standup, branching
- [specs/openapi.yaml](specs/openapi.yaml) — Full API contract
- [specs/MODULE_SPEC_M*.md](specs/) — Per-member module specs
