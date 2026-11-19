# Spotnxt Ad Metrics MCP Server

A working **Model Context Protocol (MCP)** server for mock advertising analytics, built with **Python, FastAPI, and the official MCP Python SDK**.

Claude can discover four tools, read mock campaign data, calculate advertising metrics, and produce a campaign performance summary. The same logic is also exposed through a small FastAPI REST API for easy manual testing.

---

## Table of contents

- [What is implemented](#what-is-implemented)
- [Tools exposed to Claude](#tools-exposed-to-claude)
- [Architecture](#architecture)
- [Quick start](#quick-start)
- [Connect to Claude Desktop](#connect-to-claude-desktop)
- [Connect to Claude Code (alternative)](#connect-to-claude-code-alternative)
- [Run over HTTP](#run-over-http)
- [Demo](#demo)
- [Metric definitions and validation](#metric-definitions-and-validation)
- [Tests](#tests)
- [Project structure](#project-structure)

---

## What is implemented

| Assignment requirement | Where it lives |
| --- | --- |
| Python + FastAPI + official MCP SDK | `app/main.py`, `app/mcp_server.py` |
| Read Ad Data tool | `read_ad_data` in `app/mcp_server.py` |
| Calculate Ad Metrics tool | `calculate_ad_metrics` in `app/mcp_server.py` |
| Campaign Summary tool | `campaign_summary` in `app/mcp_server.py` |
| Claude integration | MCP stdio transport + `README` configuration |
| Mock advertising data | `app/data.py` |
| Input validation / error handling | Pydantic models, `ToolError`, FastAPI 4xx responses |
| Working MCP server | Verified over stdio and Streamable HTTP; 41 automated tests pass |

The MCP server is the primary deliverable. FastAPI is used as the HTTP host and also provides REST endpoints and OpenAPI docs; the REST routes are not a replacement for MCP.

---

## Tools exposed to Claude

| Tool | Inputs | Returns |
| --- | --- | --- |
| `read_ad_data` | `campaign_id` | Campaign metadata plus spend, impressions, clicks, and conversions |
| `calculate_ad_metrics` | `spend`, `impressions`, `clicks`, `conversions` | `ctr`, `cpc`, `cpa`, `cpm` |
| `campaign_summary` | `campaign_id` | Campaign data, calculated metrics, performance rating, summary text, insights |
| `list_campaigns` | none | Available campaign IDs and basic campaign details |

`list_campaigns` is a small convenience tool so Claude can discover a valid ID before calling the three required tools.

Example prompts once connected:

- "List the campaigns available in Spotnxt."
- "Read the ad data for campaign `cmp_1001`."
- "Calculate CTR, CPC, CPA, and CPM for $2,400 spend, 400,000 impressions, 8,000 clicks, and 320 conversions."
- "How is campaign `cmp_1002` performing? Give me the summary and key insights."

All campaign data is fictional. No Meta Ads or other real advertising API is called.

---

## Architecture

```text
Claude Desktop / Claude Code / MCP client
                  │
                  │ MCP protocol (JSON-RPC)
                  ▼
        ┌─────────────────────┐
        │   MCP server        │
        │ app/mcp_server.py   │
        │ 4 tools             │
        └─────────┬───────────┘
                  │
                  ▼
        ┌─────────────────────┐
        │ Analytics layer     │
        │ app/data.py         │
        │ app/metrics.py      │
        └─────────┬───────────┘
                  │
                  ▼
        ┌─────────────────────┐
        │ FastAPI host        │
        │ app/main.py         │
        │ /mcp + REST + docs  │
        └─────────────────────┘
```

Two transports are supported:

- **stdio** — recommended for Claude Desktop; Claude launches `app/mcp_server.py` as a child process.
- **Streamable HTTP** — served by FastAPI at `POST/GET http://localhost:8000/mcp`.

---

## Quick start

Requires **Python 3.10+** (tested with Python 3.11 and the current official `mcp` 2.3 SDK).

### Windows (PowerShell or CMD)

```bat
cd spotnxt-mcp-server
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

### macOS / Linux

```bash
cd spotnxt-mcp-server
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

### Verify the MCP server without Claude

The demo client launches the server over stdio, performs MCP tool discovery, calls every tool, and demonstrates an expected error:

```bash
python scripts/demo_client.py
```

You should see the four tool schemas followed by the results for `list_campaigns`, `read_ad_data`, `calculate_ad_metrics`, `campaign_summary`, and an unknown-campaign error.

---

## Connect to Claude Desktop

> **No paid subscription needed.** Anthropic supports local MCP servers in
> **Claude Desktop on the Free plan**. A free Claude account is enough for this
> assignment. Claude Code (the `claude` CLI) requires a paid plan, so use the
> Desktop app instead — no Pro/Max purchase is required.

### 1. Find the Claude Desktop config file

| OS | Path |
| --- | --- |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

Create the file if it does not exist.

### 2. Add the server

Use the **absolute path** to the virtual environment's Python and to `app/mcp_server.py`.

Windows example (replace `C:\path\to` with the real repository location):

```json
{
  "mcpServers": {
    "spotnxt-ads": {
      "command": "C:\\path\\to\\spotnxt-mcp-server\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\path\\to\\spotnxt-mcp-server\\app\\mcp_server.py"
      ]
    }
  }
}
```

macOS / Linux example:

```json
{
  "mcpServers": {
    "spotnxt-ads": {
      "command": "/absolute/path/to/spotnxt-mcp-server/.venv/bin/python",
      "args": [
        "/absolute/path/to/spotnxt-mcp-server/app/mcp_server.py"
      ]
    }
  }
}
```

If the file already contains other MCP servers, add the `"spotnxt-ads"` entry inside the existing `"mcpServers"` object.

> **Windows MSIX installs:** some Claude Desktop builds read a virtualized copy
> of the config. If the server does not appear, add the same `"spotnxt-ads"`
> entry here as well:
> `%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude_desktop_config.json`

### 3. Restart Claude Desktop

Quit Claude Desktop completely (on Windows, use **File → Exit**; closing the window is not enough) and reopen it.

The server should appear in the tools/connectors menu as **spotnxt-ads**, with four tools:

```text
read_ad_data
calculate_ad_metrics
campaign_summary
list_campaigns
```

### 4. Ask Claude to use it

```text
Use the Spotnxt tools to list the available campaigns, then summarize cmp_1001.
```

```text
Using Spotnxt, how is cmp_1002 performing? Include CTR, CPC, CPA, and CPM.
```

Claude should first discover the tools, then invoke `list_campaigns`, `read_ad_data`/`campaign_summary`, and reply with the returned data.

### Troubleshooting

- **No tools appear:** verify both absolute paths, then run the same command manually:
  - Windows: `C:\path\to\spotnxt-mcp-server\.venv\Scripts\python.exe C:\path\to\spotnxt-mcp-server\app\mcp_server.py`
  - It is correct for the process to wait silently for JSON-RPC input. Press `Ctrl+C` to stop.
- **Server starts but Claude reports an error:** confirm `pip install -r requirements.txt` was run in the same `.venv`.
- **Claude Desktop logs:** check the app's MCP logs (Windows: `%APPDATA%\Claude\logs`) for the `spotnxt-ads` server entry.
- **HTTP connector alternative:** if your Claude plan/version supports custom connectors, run the HTTP server (below) and use `http://localhost:8000/mcp` as the connector URL. stdio is the most portable setup.

---

## Optional: Claude Code (paid plans only)

> **Skip this section if you are using the free plan.** Claude Code requires a
> paid Claude subscription or API billing. Claude Desktop Free is sufficient.

Claude Code can load a project-scoped `.mcp.json` from the repository root:

```json
{
  "mcpServers": {
    "spotnxt-ads": {
      "command": "C:\\path\\to\\spotnxt-mcp-server\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\path\\to\\spotnxt-mcp-server\\app\\mcp_server.py"
      ]
    }
  }
}
```

Then start Claude Code in this repository, approve the project MCP server, and ask:

```text
Use the spotnxt-ads MCP server to summarize campaign cmp_1002.
```

Alternatively:

```bash
claude mcp add spotnxt-ads -- /absolute/path/to/python /absolute/path/to/app/mcp_server.py
```

---

## Run over HTTP

From the repository root, with the virtual environment active:

```bash
uvicorn app.main:app --reload
```

| URL | Purpose |
| --- | --- |
| `http://127.0.0.1:8000/mcp` | MCP Streamable HTTP endpoint |
| `http://127.0.0.1:8000/docs` | Interactive FastAPI docs |
| `http://127.0.0.1:8000/healthz` | Health check |
| `http://127.0.0.1:8000/api/campaigns` | List campaigns (REST convenience) |

Demonstrate MCP over HTTP in a second terminal:

```bash
python scripts/demo_client.py --transport http --url http://127.0.0.1:8000/mcp
```

### REST examples

```bash
curl http://127.0.0.1:8000/api/campaigns/cmp_1001
curl http://127.0.0.1:8000/api/campaigns/cmp_1002/summary
curl -X POST http://127.0.0.1:8000/api/metrics/calculate \
  -H "Content-Type: application/json" \
  -d '{"spend":1000,"impressions":100000,"clicks":2000,"conversions":40}'
```

Expected calculation result:

```json
{
  "ctr": 2.0,
  "cpc": 0.5,
  "cpa": 25.0,
  "cpm": 10.0
}
```

---

## Demo

### Recorded MCP protocol demo

The output below was produced by `python scripts/demo_client.py` using the official MCP client and the stdio transport. This is the same discovery/invocation flow Claude uses: `tools/list`, then `tools/call`.

```text
=== MCP tools discovered ===
[
  {"name": "read_ad_data", ...},
  {"name": "calculate_ad_metrics", ...},
  {"name": "campaign_summary", ...},
  {"name": "list_campaigns", ...}
]

=== calculate_ad_metrics(1000, 100000, 2000, 40) ===
{
  "ctr": 2.0,
  "cpc": 0.5,
  "cpa": 25.0,
  "cpm": 10.0
}

=== campaign_summary(cmp_1002) ===
{
  "campaign_id": "cmp_1002",
  "name": "Cart Abandoner Retargeting",
  "status": "ACTIVE",
  "metrics": {
    "ctr": 3.0,
    "cpc": 0.5,
    "cpa": 6.25,
    "cpm": 15.0
  },
  "performance": "Strong",
  "insights": [
    "CTR of 3.00% is above the 2.00% benchmark.",
    "CPC of $0.50 is below the $1.50 target.",
    "CPA of $6.25 is within the $15.00 target.",
    "CPM of $15.00 is within the $12.00-$25.00 range."
  ]
}

=== read_ad_data error handling(cmp_9999) ===
{
  "is_error": true,
  "message": "Error executing tool read_ad_data: Campaign 'cmp_9999' was not found. Available campaign IDs: cmp_1001, cmp_1002, cmp_1003, cmp_1004, cmp_1005."
}
```

### Claude Desktop demonstration (free plan works)

After following [Connect to Claude Desktop](#connect-to-claude-desktop), ask:

```text
Use the Spotnxt MCP tools to answer:

1. Which campaigns are available?
2. How is cmp_1002 performing? Show CTR, CPC, CPA, CPM, and the summary.
3. Calculate the metrics for $1,000 spend, 100,000 impressions, 2,000 clicks,
   and 40 conversions.
```

Claude will show tool calls such as `list_campaigns`, `campaign_summary`, and `calculate_ad_metrics` in its activity/tool log. Add a screenshot or copied transcript of that session to the repository when submitting if the evaluator requires visual proof of the Claude connection. The protocol-level demo above can be reproduced at any time without Claude.

---

## Metric definitions and validation

| Metric | Formula | Output |
| --- | --- | --- |
| CTR | `clicks / impressions * 100` | Percentage (e.g. `2.0` means 2.00%) |
| CPC | `spend / clicks` | Currency amount |
| CPA | `spend / conversions` | Currency amount |
| CPM | `spend / impressions * 1000` | Currency amount |

- Calculations use `Decimal` arithmetic and round to **4 decimal places**.
- A metric whose denominator is zero is returned as `null` instead of raising a divide-by-zero error or reporting a misleading zero.
- CTR is 0 when there are impressions but no clicks; CPC is null when there are no clicks; CPA is null when there are no conversions.

### Input validation

- `campaign_id` must be 1–32 characters, start with a letter/digit, and contain only letters, digits, `_`, or `-`. Lookup is case-insensitive and trims whitespace.
- Unknown IDs produce an MCP tool error listing valid campaign IDs (and HTTP 404 for REST).
- `spend`, `impressions`, `clicks`, and `conversions` must be non-negative and finite.
- `clicks` cannot exceed `impressions`.
- Values have generous upper bounds to keep calculations safe.

### Performance benchmarks

The summary uses simple, documented benchmarks so the output is explainable rather than magic:

| Metric | Good | Okay | Poor |
| --- | --- | --- | --- |
| CTR | ≥ 2.00% | 1.00–2.00% | < 1.00% |
| CPC | ≤ $1.50 | $1.50–$3.00 | > $3.00 |
| CPA | ≤ $15.00 | $15.00–$30.00 | > $30.00 |
| CPM | ≤ $12.00 | $12.00–$25.00 | > $25.00 |

These are internal demo thresholds, not claims about real-world benchmarks. They can be changed in `app/metrics.py`.

### Mock campaigns

| ID | Name | Platform | Status | Spend | Impressions | Clicks | Conversions |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| `cmp_1001` | Summer Sale - Prospecting | Meta | ACTIVE | $12,500 | 1,250,000 | 18,750 | 1,125 |
| `cmp_1002` | Cart Abandoner Retargeting | Instagram | ACTIVE | $4,800 | 320,000 | 9,600 | 768 |
| `cmp_1003` | Q3 Brand Awareness | Meta | COMPLETED | $8,000 | 2,000,000 | 6,000 | 240 |
| `cmp_1004` | B2B Demo Requests | Meta | PAUSED | $6,200 | 155,000 | 3,410 | 186 |
| `cmp_1005` | Holiday Video Teaser | Instagram | ACTIVE | $3,500 | 875,000 | 2,625 | 105 |

---

## Tests

```bash
python -m pytest -q
```

The suite covers:

- Metric formulas and rounding
- Zero-denominator behavior
- Invalid / non-finite inputs and inconsistent clicks vs. impressions
- Campaign lookup and malformed IDs
- MCP tool discovery, schemas, successful calls, and tool errors
- FastAPI REST endpoints, validation responses, and OpenAPI generation

Expected: `41 passed`.

---

## Project structure

```text
spotnxt-mcp-server/
│
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI host, REST endpoints, /mcp mount
│   ├── mcp_server.py    # Official MCP SDK server + four tools
│   ├── data.py          # Mock campaigns and lookup/validation
│   └── metrics.py       # CTR/CPC/CPA/CPM + summary logic
│
├── tests/
│   ├── test_metrics.py
│   ├── test_mcp_server.py
│   └── test_api.py
│
├── scripts/
│   └── demo_client.py   # Reproducible MCP discovery/invocation demo
│
├── requirements.txt
├── requirements-dev.txt
├── README.md
└── .gitignore
```

### Main dependencies

- `mcp>=2.3,<3.0` — official MCP Python SDK; provides `MCPServer` and the client used by the demo/tests.
- `fastapi>=0.115,<1.0` — FastAPI host, REST endpoints, OpenAPI.
- `uvicorn>=0.31,<1.0` — ASGI server.
- `pytest`, `httpx` — development/test only.
#   S p o t n x t _ B a c k e n d _ D e v e l o p e r _ I n t e r n _ A s s i g n m e n t  
 