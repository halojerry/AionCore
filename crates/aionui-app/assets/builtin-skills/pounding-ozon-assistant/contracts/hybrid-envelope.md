# Hybrid Local-to-Cloud Envelope Contract

## Purpose

This document defines the envelope format for client (`pounding-ozon-hybrid`) to cloud backend (n8n pipeline) submission.

## Architecture

```
hybrid client → POST n8n /webhook/pipeline
```

The n8n pipeline receives the envelope, processes it through:
COS upload → mxou image generation → Ozon payload build → Ozon upload → Supabase result write.

The client uses `MXOU_TOKEN` for platform authentication.

## Auth

Client uses the **platform-issued user key** (`MXOU_TOKEN`).

Header:
- `Authorization: Bearer <MXOU_TOKEN>`

## Transport

| Backend | Method | URL |
|---------|--------|-----|
| n8n pipeline | POST | `{MXOU_API_BASE}/webhook/pipeline` |

Base URL configured via `MXOU_API_BASE` env var.

| Action | Method | Endpoint |
|--------|--------|----------|
| Submit task | POST | `/webhook/pipeline` |
| Poll status | — | Supabase direct query (client-side) |
| Property lookup | — | Supabase direct query (client-side) |
| Property confirm | — | Supabase direct write (client-side) |

## Request Envelope

```json
{
  "version": "v1",
  "project_id": "proj_abc123",
  "subproject_id": "item_001",
  "request_id": "req_001",
  "source": {
    "source_item_id": "1688_abc",
    "source_url": "https://detail.1688.com/offer/1.html",
    "query": "保温杯",
    "product_id": "",
    "offer_id": ""
  },
  "assets": {
    "image_urls": ["https://example.com/a.png"]
  },
  "draft": {
    "title": "",
    "source_category_ids": [],
    "attributes": {}
  },
  "resolved": {
    "category": {
      "description_category_id": "17038776",
      "type_id": "96114779",
      "confidence": 0.95
    },
    "attributes": [
      {"id": 31, "is_required": true, "values": [{"value": "BrandName"}]}
    ]
  },
  "extensions": {
    "ozon_client_id": "store-abc-ozon-client-id",
    "ozon_api_key": "store-abc-ozon-api-key",
    "mxou_token": "user-image-gen-token",
    "mxou_base_url": "https://api.mxou.cn",
    "ozon_currency": "RUB"
  }
}
```

### Fields

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `version` | string | yes | Always `"v1"` |
| `project_id` | string | yes | One user request — e.g. publishing 10 products |
| `subproject_id` | string | yes | One item under a project |
| `request_id` | string | yes | Idempotent request id |
| `source.source_item_id` | string | conditional | 1688 item id |
| `source.source_url` | string | conditional | 1688 product URL |
| `source.product_id` | string | conditional | Existing Ozon product_id (for refresh) |
| `source.offer_id` | string | conditional | Existing Ozon offer_id |
| `assets.image_urls` | string[] | no | Source image URLs |
| `draft` | object | no | Pre-assembled draft data |
| `resolved` | object | yes | Pre-resolved category + attributes (by local skill) |
| `extensions` | object | yes | Ozon credentials + mxou token |

### resolved

The `resolved` field contains category and attribute data that has been resolved **locally** by the skill before submission. This avoids redundant API calls in the cloud pipeline.

```json
{
  "resolved": {
    "category": {
      "description_category_id": "17038776",
      "type_id": "96114779",
      "confidence": 0.95
    },
    "attributes": [
      {"id": 31, "is_required": true, "values": [{"value": "BrandName"}]}
    ]
  }
}
```

### extensions

Per-store credentials for cloud-side Ozon API access and image generation:

```json
{
  "extensions": {
    "ozon_client_id": "store-abc-ozon-client-id",
    "ozon_api_key": "store-abc-ozon-api-key",
    "mxou_token": "user-image-gen-token",
    "mxou_base_url": "https://api.mxou.cn",
    "ozon_currency": "RUB"
  }
}
```

### Prohibited ad-hoc fields

- `source.draft_data` — use `draft` instead
- `assets.file` — use `assets.image_urls` or `draft` instead

## Response Envelope

```json
{
  "version": "v1",
  "project_id": "proj_abc123",
  "subproject_id": "item_001",
  "task_id": "task_001",
  "status": "accepted",
  "terminal": false,
  "error": null
}
```

### Status values

Non-terminal:
- `accepted` — received by n8n, queued for processing
- `in_progress` — n8n pipeline is running
- `retrying` — retrying after a recoverable failure

Terminal:
- `succeeded` — all stages completed, product uploaded to Ozon
- `partial_failed` — some stages failed but pipeline continued
- `blocked` — gate check blocked (missing attributes, low confidence, etc.)
- `failed` — unrecoverable failure
- `cancelled` — cancelled by operator

## Error Envelope

```json
{
  "version": "v1",
  "project_id": "proj_abc123",
  "subproject_id": "item_001",
  "task_id": "task_001",
  "status": "failed",
  "terminal": true,
  "error": {
    "code": "image_fetch_failed",
    "message": "remote image download failed",
    "retryable": true,
    "retry_count": 2
  }
}
```

## Batch Submission

For batch submissions, each `(project_id, subproject_id)` pair is submitted as a separate n8n webhook call under the same `project_id`.

```json
{
  "version": "v1",
  "project_id": "proj_abc123",
  "items": [
    {
      "subproject_id": "item_001",
      "request_id": "req_001",
      "source": { "source_url": "https://detail.1688.com/offer/1.html" },
      "assets": {},
      "draft": {}
    }
  ]
}
```

The hybrid client iterates `items` and submits each via `cloud_client.submit_task()`.
