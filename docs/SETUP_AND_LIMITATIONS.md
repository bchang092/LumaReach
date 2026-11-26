# Setup and remaining limitations — November 8, 2026

## What now works

`/help/` offers the default questionnaire and MCP resource search. The search at `/help/mcp/` accepts service selections, editable text or voice, performs brief needs extraction on the server, then returns up to ten directory resources in descending match-score order. The model extracts needs and constraints only; it never creates provider names or contact details. The website API and both MCP transports use the same matching code.

Ranking first requires a supported service and any stated hard requirements. Supported need count carries the most weight, followed by blended lexical/semantic text relevance, location preference, supported optional preferences, original source reliability and recency. A selection step reserves coverage across multiple needs before sorting the selected set. Scores are relative ordering signals, not probabilities or a validated rating of care quality. Original scraped reliability scores remain unchanged.

The app runs without an API key using a basic local parser. With a key, structured extraction uses the Responses API with `store=False`, a 15-second timeout and no retries. Errors/refusals fall back to local matching with a visible notice. Raw intake text is not persisted by this app.

## Start the website

```sh
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -B manage.py migrate
.venv/bin/python -B manage.py runserver
```

Open `http://127.0.0.1:8000/help/`. For a new checkout, create `.venv` using Python 3.13 first. Install and run using the same Python environment. API keys go on the server, never in the browser.

Use `.env.example` as a configuration reference. The app does **not** automatically load `.env`; export variables in your shell or configure them through your host's secret manager.

1. Set `OPENAI_API_KEY` to an account with available API credits and access to the configured model.
2. Set `TRIAGE_USE_LLM=true`; optionally change `TRIAGE_MODEL` (default `gpt-4.1-mini`).
3. For server-backed voice, set `VOICE_USE_API=true`. `TRANSCRIPTION_MODEL` defaults to `gpt-transcribe`. Recordings are capped at 60 seconds in the UI and 2 MB at the API. Audio goes to OpenAI when recording stops, is handled in memory, and is not saved by Baltimore Lifeline. Review/edit the transcript before searching.
4. Without server voice, supported browsers use their own speech recognition service. Other browsers retain typing. Production microphone access requires HTTPS and user permission. Provider retention policies apply to both external speech and language-model processing.
5. For another application/API to use this directory, follow [MCP setup](../mcp_server/README.md). Local stdio needs no transport secret. HTTP requires a separate `MCP_API_KEY` and supports clients with preconfigured bearer headers. Interactive OAuth connection flows require an identity gateway.

## Where quality remains limited

- **Source coverage:** 1,154 of 1,341 workbook records have active service tags. The other 187 lack a supported service tag or have an operating-status flag. Some active tags are deliberately scoped to enrolled residents or specific programs and cannot qualify as general-access services.
- **Eligibility coverage:** only 10 program-scoped eligibility facts exist. An otherwise relevant provider can be withheld for a stated cost, insurance, age, document or schedule requirement that the directory cannot confirm. Returning fewer than ten is intentional. Missing information never means “eligible.”
- **Tag accuracy:** 30 additional records were reviewed: 26 had tag/scope changes and four had their existing scope confirmed. [Before/after audit](../audits/phase1/nov08_service_corrections.json) records exact changes and rationale. Runtime checks validate every activated tag's taxonomy membership, source hash, exact excerpt/offset, scope and review attribution. These checks prove source fidelity, not that the source itself is true or current. Implementation-agent review is not independent caseworker or provider verification.
- **Location:** matching currently covers geocoded sites within 35 approximate straight-line miles of central Baltimore. If a supplied ZIP has directory addresses, their coordinate midpoint provides a rough origin; otherwise the origin is central Baltimore, explicitly labeled. This is not GPS, travel time, transit accessibility, a real ZIP centroid, or confirmed service-area eligibility. Resources without usable coordinates are excluded; some remote/statewide services are therefore missed.
- **Understanding:** the offline parser handles common English/Spanish phrases and several negations but remains rule-based. Open-ended, ambiguous, multilingual and complex eligibility requests can be missed. The selected model must be evaluated with live API calls before claiming live-model accuracy.
- **Availability and quality:** the app does not know vacancies, whether a program is accepting clients today, current intake hours, or successful referral outcomes. Scraped reliability is not a validated measure of clinical/service quality. Providers must confirm.
- **Safety:** crisis routing precedes ranking and survives a missing main workbook and website rate limiting. Authored regression tests cannot establish that every crisis expression will be recognized. Qualified practitioners should review crisis wording and new held-out scenarios.
- **Voice:** actual Chromium microphone capture was tested with a synthetic device and mocked transcription. Human speech accuracy, accent/noise handling, mobile Safari/Android permissions and live transcription billing/model access are not verified.

## What you need before public launch

Configure a strong Django `SECRET_KEY`, HTTPS, `DEBUG=false`, production database, shared rate limiting and limits on API spending/concurrency. Keep request-body/audio capture disabled in proxies, logs, analytics and error reporting. The current Django rate limit is process-local; add a shared cache or edge enforcement for multiple workers. Run migrations and collectstatic. Deploy the MCP service separately if remote clients need it, with exact hosts, dedicated credentials and gateway protections described in its README. No deployment was performed here.

Run live evaluations after setting credentials:

```sh
.venv/bin/python -B scripts/evaluate_triage.py --live --output evaluation/live_results.json
.venv/bin/python -B scripts/evaluate_triage.py --live --cases evaluation/challenge_cases.json --output evaluation/live_challenge_results.json
```

A fallback is not a live-model pass: the evaluator exits with code 2 when a non-crisis request falls back. Examine route differences and wrong/missing needs; a zero exit code does not mean every authored route expectation passed. Review [current test results](../evaluation/NOV08_REPORT.md). Have caseworkers independently judge **all ten** results for new scenarios, then verify program facts with providers. Program-specific eligibility evidence can improve coverage for searches with strict requirements.

References: [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [file transcription](https://developers.openai.com/api/docs/guides/speech-to-text), [browser SpeechRecognition limitations](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition).
