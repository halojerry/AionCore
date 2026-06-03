# Hybrid Line Responsibility Boundary

## Topology

```
pounding-ozon/          → Legacy local-only skill (reference, unchanged)
pounding-ozon-hybrid/   → Hybrid local thin-client (THIS, active)
pounding-ozon-cloud/    → Cloud worker/backend (Python packages)
deploy/n8n/             → n8n pipeline workflows (cloud execution)
```

## Local Responsibilities (pounding-ozon-hybrid)

| Responsibility | Rationale |
| --- | --- |
| 1688 AK handling | Local credential; cloud should not hold it |
| Browser/session-bound acquisition | Requires local browser state |
| Local selection and draft capture | User-machine dependent |
| 1688 search (text/image/link) | Local API calls |
| Category matching (Supabase → Ozon API) | Local cache + API enrichment |
| Attribute resolution | Local attribute matching engine |
| Envelope assembly | Client formats its own envelopes |
| Config management | Local config store |
| Receiving results from cloud | Response processing |
| COS credential management | COS secret keys stay local |

## Cloud Responsibilities (n8n @ worker.mxou.cn)

| Responsibility | Rationale |
| --- | --- |
| COS image upload & mirror | Cloud has COS access via community node |
| mxou image generation | GPU/API access on cloud side |
| Ozon payload build | Centralized logic in n8n Code nodes |
| Ozon product upload | n8n HTTP Request to Ozon API |
| Supabase task status update | n8n writes results |
| Error capture → Sentry | Centralized observability |
| Storage lifecycle (cleanup >30d) | n8n cron workflow |

## Contract-Only

| Item | Contract Location |
| --- | --- |
| Envelope format (v1) | `contracts/hybrid-envelope.md` |
| Auth: Bearer MXOU_TOKEN | `contracts/hybrid-envelope.md` |
| Status values | `contracts/hybrid-envelope.md` |
| Structured error envelope | `contracts/hybrid-envelope.md` |

## Cloud Transport (n8n)

```
hybrid client → POST https://worker.mxou.cn/webhook/pipeline
  Body: {"task_id": "...", "envelope": {...}}

Pipeline stages:
  Build → DL Image → COS Upload → Image Gen (stage-image-gen) → Rebuild → Ozon → Result → Supabase
```

**Hard rules:**
- Client never holds cloud credentials (COS keys, Supabase service role)
- n8n pipeline validates envelope structure before processing

## Communication Flow

```
User → pounding-ozon-hybrid
         │
         ├── Local: search 1688, match category, resolve attributes, build envelope
         │
         └── Cloud (n8n pipeline):
               ├─ POST https://worker.mxou.cn/webhook/pipeline
               │   Body: {"task_id": "...", "envelope": {...}}
               ├─ n8n runs: COS → Image Gen → Payload → Ozon → Supabase
               └─ Poll: client queries Supabase gateway_tasks directly
```

## Non-Goals

- pounding-ozon is NOT being rewritten (reference only)
- pounding-ozon-hybrid does NOT import pounding-ozon runtime code
- pounding-ozon-cloud does NOT depend on pounding-ozon-hybrid
