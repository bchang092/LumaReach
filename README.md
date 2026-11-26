# Baltimore Lifeline

Guided Help at **`/help/`** offers two paths. The default questionnaire builds a priority-based help plan. MCP resource search accepts service selections, typed text, or voice and returns up to ten ranked directory resources. The website calls the registered MCP tool through the SDK’s in-process transport. Standalone clients can use stdio or authenticated HTTP.

The website and MCP share one engine: safety check → structured needs extraction → evidence and eligibility gates → ranked directory results. It runs with basic local matching without an API key. An OpenAI key enables richer interpretation and optional server-backed transcription. The model cannot create provider records or contact information.

## Start locally

Use Python 3.13. Create a virtual environment if needed, then install and run with that same Python:

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -B manage.py migrate
.venv/bin/python -B manage.py runserver
```

Open http://127.0.0.1:8000/help/.

For AI extraction, set `OPENAI_API_KEY` and `TRIAGE_USE_LLM=true` in the server environment. For optional audio transcription, also set `VOICE_USE_API=true`. `.env.example` lists settings; `.env` files are **not automatically loaded**. Never put API keys in browser code.

See **[setup, shortcomings and launch steps](docs/SETUP_AND_LIMITATIONS.md)** for model configuration, voice behavior, data limitations and deployment requirements.

## MCP connections

```sh
.venv/bin/python -B -m mcp_server.server
```

This starts local stdio MCP. For API clients, an authenticated Streamable HTTP transport is also available. See **[MCP configuration and client example](mcp_server/README.md)**. HTTP requires a separate transport key; clients expecting interactive OAuth need an authorization gateway.

## Data and quality

- The map, questionnaire and MCP use `input_data/11242026_ReverificationMASTER_SHEET.xlsx` (Sheet1). 1,154 of 1,341 workbook records have active service tags, including 585 tagged automatically from November descriptions. [Transfer details](audits/november_transfer.json).
- Every active tag is validated against exact source evidence, source hash, taxonomy, scope and review attribution at load time.
- Review of thirty further records corrected tags/scopes on 26 and confirmed four existing scopes, preventing mistakes such as treating patient lodging as medical care or peer support as clinical treatment. [Audited changes](audits/phase1/nov08_service_corrections.json) are reversible.
- Ranking combines service fit, text relevance, approximate location, supported preferences, original reliability and recency. Cards explain the order; relative match scores do not establish eligibility or service quality.
- Only 10 program-scoped eligibility facts exist. Unknown hard requirements can produce fewer than ten results or no match. The app never pads results with unconfirmed eligibility.
- API/live speech quality, independent caseworker assessment and production deployment remain outstanding. [Current test report](evaluation/NOV08_REPORT.md) separates measured results from these limitations.

## Tests

```sh
.venv/bin/python -B manage.py test map --noinput
.venv/bin/python -B scripts/test_tag_audit.py
.venv/bin/python -B scripts/test_tag_migration_io.py
.venv/bin/python -B scripts/test_mcp_protocol.py
.venv/bin/python -B scripts/test_mcp_http.py
.venv/bin/python -B scripts/evaluate_triage.py --variants --output evaluation/nov08_robustness_results.json
.venv/bin/python -B scripts/evaluate_triage.py --variants --cases evaluation/challenge_cases.json --output evaluation/nov08_challenge_robustness_results.json
```

UI behavior and actual browser checks:

```sh
npm install --prefix .local/ui-tests --no-audit --no-fund jsdom
node --test scripts/test_intake_ui.cjs scripts/test_map_filters.cjs
npm install --prefix .local/browser-tests --no-audit --no-fund playwright axe-core
.local/browser-tests/node_modules/.bin/playwright install chromium
node scripts/test_browser.cjs
```

The Chromium test uses a synthetic microphone and mocked transcription, not a live speech-quality evaluation. Protocol/browser tests use temporary databases. See [operations and privacy](docs/TRIAGE_OPERATIONS.md) for maintenance and rollback.

## Page activity and feedback

After running migrations, sign in to Django admin and open **Map → Page activity** at `/admin/map/pageactivity/`. Staff need the **Can view page activity** permission. The report shows every page, including pages with zero activity, for today, 7 days, or 30 days in Baltimore time.

A small “Was this page helpful?” control appears at the foot of each page and inside the map filters. Feedback is one tap per page load. The report counts page loads, clicks, and Yes/No responses in daily buckets. Automatic counting honors Do Not Track and Global Privacy Control. Clicks are batched and best-effort. Totals measure interactions, not unique people. The activity table stores no answers, coordinates, IPs, URLs, review tokens, or visitor IDs.

Guided Help supports eight selectable services with optional typed or spoken details. The longer questionnaire can also run a local search from an optional written note. [November 20 provider tag review](audits/phase1/provider-review-2026-11-20.md) documents the five records checked and the applied corrections.
