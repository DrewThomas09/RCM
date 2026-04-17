"""Auto-generated OpenAPI 3.0 spec + /api/docs viewer (Prompt 39 enhancement).

Produces a machine-readable ``openapi.json`` describing every API
endpoint the server exposes. ``GET /api/docs`` serves a lightweight
Swagger UI page loaded from a CDN so partners' integration teams
can explore the API without reading source code.
"""
from __future__ import annotations

import json
from typing import Any, Dict

_SPEC: Dict[str, Any] = {
    "openapi": "3.0.3",
    "info": {
        "title": "RCM-MC API",
        "version": "1.0.0",
        "description": (
            "Healthcare PE diligence platform API. Covers deal management, "
            "analysis packets, Monte Carlo simulation, overrides, exports, "
            "portfolio operations, and webhooks."
        ),
    },
    "servers": [{"url": "/", "description": "This instance"}],
    "paths": {
        "/api/deals": {
            "get": {
                "summary": "List all deals",
                "tags": ["Deals"],
                "responses": {"200": {"description": "Array of deal snapshots"}},
            },
            "post": {
                "summary": "Create deal from hospital name/CCN (auto-populate)",
                "tags": ["Deals"],
                "requestBody": {
                    "content": {"application/json": {
                        "schema": {"type": "object", "properties": {
                            "name": {"type": "string"},
                            "deal_id": {"type": "string"},
                        }},
                    }},
                },
                "responses": {"200": {"description": "AutoPopulateResult"}},
            },
        },
        "/api/deals/{deal_id}/overrides": {
            "get": {
                "summary": "List overrides for a deal",
                "tags": ["Overrides"],
                "parameters": [{"name": "deal_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "Override map + audit trail"}},
            },
        },
        "/api/deals/{deal_id}/overrides/{key}": {
            "put": {
                "summary": "Set one override",
                "tags": ["Overrides"],
                "requestBody": {
                    "content": {"application/json": {
                        "schema": {"type": "object", "properties": {
                            "value": {}, "reason": {"type": "string"},
                        }},
                    }},
                },
                "responses": {"200": {"description": "Override applied"}},
            },
            "delete": {
                "summary": "Remove one override",
                "tags": ["Overrides"],
                "responses": {"200": {"description": "Override deleted"}},
            },
        },
        "/api/analysis/{deal_id}": {
            "get": {
                "summary": "Build or return cached analysis packet",
                "tags": ["Analysis"],
                "parameters": [{"name": "deal_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "Full DealAnalysisPacket JSON"}},
            },
        },
        "/api/analysis/{deal_id}/export": {
            "get": {
                "summary": "Export analysis in various formats",
                "tags": ["Exports"],
                "parameters": [
                    {"name": "deal_id", "in": "path", "required": True, "schema": {"type": "string"}},
                    {"name": "format", "in": "query", "schema": {
                        "type": "string",
                        "enum": ["html", "json", "csv", "xlsx", "pptx", "package", "questions"],
                    }},
                ],
                "responses": {"200": {"description": "Export file or inline HTML"}},
            },
        },
        "/api/analysis/{deal_id}/simulate/v2": {
            "post": {
                "summary": "Run v2 Monte Carlo simulation",
                "tags": ["Simulation"],
                "responses": {"200": {"description": "V2MonteCarloResult"}},
            },
        },
        "/api/analysis/{deal_id}/simulate/compare": {
            "post": {
                "summary": "Compare named MC scenarios",
                "tags": ["Simulation"],
                "responses": {"200": {"description": "ScenarioComparison"}},
            },
        },
        "/api/data/hospitals": {
            "get": {
                "summary": "Fuzzy hospital search (typeahead)",
                "tags": ["Data"],
                "parameters": [
                    {"name": "q", "in": "query", "schema": {"type": "string"}},
                    {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 5}},
                ],
                "responses": {"200": {"description": "Hospital match list"}},
            },
        },
        "/api/deals/{deal_id}/timeline": {
            "get": {
                "summary": "Activity timeline events for a deal",
                "tags": ["Activity"],
                "parameters": [
                    {"name": "deal_id", "in": "path", "required": True, "schema": {"type": "string"}},
                    {"name": "days", "in": "query", "schema": {"type": "integer", "default": 90}},
                ],
                "responses": {"200": {"description": "List of timeline events"}},
            },
        },
        "/api/portfolio/attribution": {
            "get": {
                "summary": "Fund-level performance attribution",
                "tags": ["Portfolio"],
                "responses": {"200": {"description": "FundAttribution"}},
            },
        },
        "/portfolio/monte-carlo": {
            "get": {
                "summary": "Correlated portfolio Monte Carlo",
                "tags": ["Portfolio"],
                "responses": {"200": {"description": "PortfolioMCResult"}},
            },
        },
        "/api/search": {
            "get": {
                "summary": "Cross-deal full-text search",
                "tags": ["Search"],
                "parameters": [
                    {"name": "q", "in": "query", "required": True, "schema": {"type": "string"}},
                    {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 20}},
                ],
                "responses": {"200": {"description": "Search results"}},
            },
        },
        "/api/deals/{deal_id}": {
            "delete": {
                "summary": "Delete a deal and all associated data (cascade)",
                "tags": ["Deals"],
                "parameters": [{"name": "deal_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {
                    "200": {"description": "Deal deleted"},
                    "404": {"description": "Deal not found"},
                },
            },
        },
        "/api/automations": {
            "get": {
                "summary": "List automation rules",
                "tags": ["Settings"],
                "responses": {"200": {"description": "Array of automation rules"}},
            },
        },
        "/api/metrics/custom": {
            "get": {
                "summary": "List custom metrics",
                "tags": ["Settings"],
                "responses": {"200": {"description": "Array of custom metrics"}},
            },
            "post": {
                "summary": "Register a custom metric",
                "tags": ["Settings"],
                "requestBody": {
                    "content": {"application/json": {
                        "schema": {"type": "object", "properties": {
                            "metric_key": {"type": "string"},
                            "display_name": {"type": "string"},
                            "unit": {"type": "string"},
                            "directionality": {"type": "string", "enum": ["higher_is_better", "lower_is_better"]},
                        }, "required": ["metric_key", "display_name"]},
                    }},
                },
                "responses": {"200": {"description": "Metric created"}},
            },
        },
        "/api/metrics/custom/{metric_key}": {
            "delete": {
                "summary": "Delete a custom metric",
                "tags": ["Settings"],
                "parameters": [{"name": "metric_key", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {
                    "200": {"description": "Metric deleted"},
                    "404": {"description": "Metric not found"},
                },
            },
        },
        "/api/webhooks": {
            "get": {
                "summary": "List registered webhooks",
                "tags": ["Settings"],
                "responses": {"200": {"description": "Array of webhooks"}},
            },
            "post": {
                "summary": "Register a webhook endpoint",
                "tags": ["Settings"],
                "requestBody": {
                    "content": {"application/json": {
                        "schema": {"type": "object", "properties": {
                            "url": {"type": "string", "format": "uri"},
                            "secret": {"type": "string"},
                            "events": {"type": "array", "items": {"type": "string"}},
                        }, "required": ["url"]},
                    }},
                },
                "responses": {
                    "200": {"description": "Webhook created"},
                    "400": {"description": "URL required"},
                },
            },
        },
        "/api/export/portfolio.csv": {
            "get": {
                "summary": "Download portfolio summary as CSV",
                "tags": ["Exports"],
                "responses": {"200": {"description": "CSV file download"}},
            },
        },
        "/health": {
            "get": {
                "summary": "Health check",
                "tags": ["Infrastructure"],
                "responses": {"200": {"description": "ok"}},
            },
        },
        "/ready": {
            "get": {
                "summary": "Readiness probe",
                "tags": ["Infrastructure"],
                "responses": {"200": {"description": "ready: true"}},
            },
        },
        "/api/deals/{deal_id}/summary": {
            "get": {
                "summary": "Lightweight deal summary (name, stage, health, archived)",
                "tags": ["Deals"],
                "parameters": [{"name": "deal_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {
                    "200": {"description": "Deal summary JSON"},
                    "404": {"description": "Deal not found"},
                },
            },
        },
        "/api/deals/{deal_id}/duplicate": {
            "post": {
                "summary": "Clone a deal with a new ID",
                "tags": ["Deals"],
                "parameters": [{"name": "deal_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "requestBody": {
                    "content": {"application/json": {
                        "schema": {"type": "object", "properties": {
                            "new_deal_id": {"type": "string"},
                            "new_name": {"type": "string"},
                        }},
                    }},
                },
                "responses": {
                    "200": {"description": "Deal cloned"},
                    "404": {"description": "Source deal not found"},
                },
            },
        },
        "/api/deals/bulk": {
            "post": {
                "summary": "Batch operations on multiple deals",
                "tags": ["Deals"],
                "requestBody": {
                    "content": {"application/json": {
                        "schema": {"type": "object", "properties": {
                            "action": {"type": "string", "enum": ["archive", "unarchive", "delete", "tag"]},
                            "deal_ids": {"type": "array", "items": {"type": "string"}},
                            "tag": {"type": "string", "description": "Required when action=tag"},
                        }, "required": ["action", "deal_ids"]},
                    }},
                },
                "responses": {
                    "200": {"description": "Batch results"},
                    "400": {"description": "Invalid action or empty deal_ids"},
                },
            },
        },
        "/api/deals/compare": {
            "get": {
                "summary": "Side-by-side deal comparison (JSON)",
                "tags": ["Deals"],
                "parameters": [
                    {"name": "ids", "in": "query", "required": True,
                     "schema": {"type": "string"},
                     "description": "Comma-separated deal IDs (2-10)"},
                ],
                "responses": {
                    "200": {"description": "Comparison data per deal"},
                    "400": {"description": "Fewer than 2 IDs"},
                },
            },
        },
        "/api/alerts/active-count": {
            "get": {
                "summary": "Count of active (un-acked) alerts",
                "tags": ["Infrastructure"],
                "responses": {"200": {"description": "{count: N}"}},
            },
        },
        "/api/metrics": {
            "get": {
                "summary": "Request observability metrics (p50/p95/p99 response times)",
                "tags": ["Infrastructure"],
                "responses": {"200": {"description": "Request count, error count, response time percentiles"}},
            },
        },
        "/api/backup": {
            "get": {
                "summary": "Download a full SQLite database backup",
                "tags": ["Infrastructure"],
                "responses": {"200": {"description": "SQLite file download"}},
            },
        },
        "/api/system/info": {
            "get": {
                "summary": "System information (version, DB stats, Python version)",
                "tags": ["Infrastructure"],
                "responses": {"200": {"description": "System info JSON"}},
            },
        },
        "/api/deals/import": {
            "post": {
                "summary": "Import deals from a JSON array",
                "tags": ["Deals"],
                "requestBody": {
                    "content": {"application/json": {
                        "schema": {"type": "array", "items": {
                            "type": "object", "properties": {
                                "deal_id": {"type": "string"},
                                "name": {"type": "string"},
                                "profile": {"type": "object"},
                            }, "required": ["deal_id"],
                        }},
                    }},
                },
                "responses": {
                    "200": {"description": "Import results with deal IDs"},
                    "400": {"description": "Empty or invalid input"},
                },
            },
        },
        "/api/deals/{deal_id}/audit": {
            "get": {
                "summary": "Audit trail for a specific deal",
                "tags": ["Deals"],
                "parameters": [
                    {"name": "deal_id", "in": "path", "required": True, "schema": {"type": "string"}},
                    {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 50}},
                ],
                "responses": {"200": {"description": "Filtered audit events"}},
            },
        },
        "/api/deals/{deal_id}/checklist": {
            "get": {
                "summary": "IC prep checklist with readiness assessment",
                "tags": ["Deals"],
                "parameters": [{"name": "deal_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "Checklist items with progress"}},
            },
        },
        "/api/deals/{deal_id}/validate": {
            "get": {
                "summary": "Validate deal data quality (profile completeness, field checks)",
                "tags": ["Deals"],
                "parameters": [{"name": "deal_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {
                    "200": {"description": "Validation result with issues and warnings"},
                    "404": {"description": "Deal not found"},
                },
            },
        },
        "/api/deals/{deal_id}/similar": {
            "get": {
                "summary": "Find deals with similar numeric profiles",
                "tags": ["Deals"],
                "parameters": [
                    {"name": "deal_id", "in": "path", "required": True, "schema": {"type": "string"}},
                    {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 5}},
                ],
                "responses": {"200": {"description": "Similar deals ranked by distance"}},
            },
        },
        "/api/deals/{deal_id}/pin": {
            "post": {
                "summary": "Pin a deal to the top of the dashboard",
                "tags": ["Deals"],
                "parameters": [{"name": "deal_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "Deal pinned"}},
            },
        },
        "/api/deals/stats": {
            "get": {
                "summary": "Aggregate deal counts by stage and archive status",
                "tags": ["Portfolio"],
                "responses": {"200": {"description": "Total, active, archived counts + stage distribution"}},
            },
        },
        "/api/deals/import-csv": {
            "post": {
                "summary": "Import deals from CSV text",
                "tags": ["Deals"],
                "requestBody": {"content": {"text/csv": {"schema": {"type": "string"}}}},
                "responses": {"200": {"description": "Import results with errors per row"}},
            },
        },
        "/api/portfolio/summary": {
            "get": {
                "summary": "Fund-level rollup with weighted MOIC/IRR, alerts, covenant status",
                "tags": ["Portfolio"],
                "responses": {"200": {"description": "Portfolio rollup JSON"}},
            },
        },
        "/api/portfolio/health": {
            "get": {
                "summary": "Health score band distribution across all active deals",
                "tags": ["Portfolio"],
                "responses": {"200": {"description": "Band counts and average score"}},
            },
        },
        "/api/deals/{deal_id}/package": {
            "get": {
                "summary": "Generate and download a full diligence package (zip)",
                "tags": ["Exports"],
                "parameters": [{"name": "deal_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "ZIP file download"}},
            },
        },
        "/api/deals/search": {
            "get": {
                "summary": "Search deals by name or ID",
                "tags": ["Deals"],
                "parameters": [
                    {"name": "q", "in": "query", "required": True, "schema": {"type": "string"}},
                    {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 20}},
                ],
                "responses": {"200": {"description": "Matching deals with name, ID, archived status"}},
            },
        },
        "/api/migrations": {
            "get": {
                "summary": "Schema migration status (applied, pending)",
                "tags": ["Infrastructure"],
                "responses": {"200": {"description": "Migration status"}},
            },
        },
        "/api": {
            "get": {
                "summary": "API route index — list all available endpoints",
                "tags": ["Infrastructure"],
                "responses": {"200": {"description": "Endpoint listing with methods, paths, summaries"}},
            },
        },
        "/api/deals/{deal_id}/counts": {
            "get": {
                "summary": "Badge counts for a deal (notes, tags, overrides, stage, health)",
                "tags": ["Deals"],
                "parameters": [{"name": "deal_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "Deal badge counts"}},
            },
        },
        "/api/deals/{deal_id}/notes": {
            "get": {
                "summary": "List notes for a deal with pagination",
                "tags": ["Deals"],
                "parameters": [
                    {"name": "deal_id", "in": "path", "required": True, "schema": {"type": "string"}},
                    {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 0}},
                    {"name": "offset", "in": "query", "schema": {"type": "integer", "default": 0}},
                ],
                "responses": {"200": {"description": "Paginated notes list"}},
            },
        },
        "/api/deals/{deal_id}/tags": {
            "get": {
                "summary": "List tags for a deal",
                "tags": ["Deals"],
                "parameters": [{"name": "deal_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "Array of tag strings"}},
            },
        },
        "/api/deals/{deal_id}/stage": {
            "get": {
                "summary": "Current stage and stage history",
                "tags": ["Deals"],
                "parameters": [{"name": "deal_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "Current stage + history array"}},
            },
        },
        "/api/deals/{deal_id}/health": {
            "get": {
                "summary": "Health score with component breakdown",
                "tags": ["Deals"],
                "parameters": [{"name": "deal_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "Score, band, components list"}},
            },
        },
        "/api/deals/{deal_id}/profile": {
            "patch": {
                "summary": "Merge individual fields into a deal's profile",
                "tags": ["Deals"],
                "parameters": [{"name": "deal_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "requestBody": {
                    "content": {"application/json": {
                        "schema": {"type": "object", "additionalProperties": True},
                    }},
                },
                "responses": {
                    "200": {"description": "Updated field list"},
                    "400": {"description": "Empty or invalid body"},
                },
            },
        },
        "/api/deals/{deal_id}/diffs": {
            "get": {
                "summary": "Field-level changes between consecutive snapshots",
                "tags": ["Deals"],
                "parameters": [{"name": "deal_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "Array of snapshot diffs with from/to values"}},
            },
        },
        "/api/deals/{deal_id}/completeness": {
            "get": {
                "summary": "Profile completeness vs 38-metric RCM registry",
                "tags": ["Deals"],
                "parameters": [{"name": "deal_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {
                    "200": {"description": "Grade, coverage %, present/missing keys"},
                    "404": {"description": "Deal not found"},
                },
            },
        },
        "/api/deals/{deal_id}/export-links": {
            "get": {
                "summary": "All available export URLs for a deal",
                "tags": ["Exports"],
                "parameters": [{"name": "deal_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "Map of export format to URL"}},
            },
        },
        "/api/portfolio/matrix": {
            "get": {
                "summary": "Cross-deal metric matrix (spreadsheet view)",
                "tags": ["Portfolio"],
                "parameters": [
                    {"name": "metrics", "in": "query",
                     "schema": {"type": "string"},
                     "description": "Comma-separated metric keys to include (all if omitted)"},
                ],
                "responses": {"200": {"description": "Deal rows with metric columns"}},
            },
        },
    },
    "tags": [
        {"name": "Deals", "description": "Deal CRUD, lifecycle, validation, completeness, search, PATCH"},
        {"name": "Analysis", "description": "Packet build + section access"},
        {"name": "Overrides", "description": "Analyst override management"},
        {"name": "Simulation", "description": "Monte Carlo + scenarios"},
        {"name": "Exports", "description": "HTML/XLSX/PPTX/CSV/Package"},
        {"name": "Data", "description": "Hospital search + data refresh"},
        {"name": "Portfolio", "description": "Fund-level views"},
        {"name": "Activity", "description": "Timeline + search"},
        {"name": "Search", "description": "Cross-deal search"},
        {"name": "Settings", "description": "Automations, custom metrics, webhooks"},
        {"name": "Infrastructure", "description": "Health, readiness, metrics, alerts"},
    ],
}


def get_openapi_spec() -> Dict[str, Any]:
    """Return the OpenAPI spec as a dict."""
    return _SPEC


def get_openapi_json() -> str:
    """Return the spec as a JSON string."""
    return json.dumps(_SPEC, indent=2)


def render_swagger_ui() -> str:
    """Return a self-contained HTML page that loads Swagger UI from CDN."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>RCM-MC API Docs</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    SwaggerUIBundle({
      url: '/api/openapi.json',
      dom_id: '#swagger-ui',
      deepLinking: true,
      presets: [SwaggerUIBundle.presets.apis],
    });
  </script>
</body>
</html>"""
