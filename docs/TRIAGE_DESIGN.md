# Baltimore Lifeline triage design

**Historical design proposal — October 24, 2026.** This document describes the original plan, not current implementation status. See [current setup and limitations](SETUP_AND_LIMITATIONS.md) and [operations](TRIAGE_OPERATIONS.md).

Original status: Phase 1 proposal, October 24, 2026. The MCP server and website changes have not been implemented. The raw workbook, scraped reliability scores, classifications, confidence values, and verification dates remain unchanged.

## What residents should experience

Keep familiar point-and-click navigation alongside a single editable text box. A resident should be able to describe a situation, tap a suggested need, or use the existing questionnaire. None of these routes should require an account.

Desktop layout:

| Main column | Side panel |
|---|---|
| “What do you need help with?” | “You can mention…” |
| Large text box and microphone button | Food today, somewhere to sleep, bills, medical care, another need |
| Editable voice transcript in the same box | Optional neighborhood/ZIP, travel limits, timing, language |
| “Find help” button | “Browse resources” and “Use the questionnaire” links |
| At most two relevant follow-up questions | Brief privacy notice |

On phones the suggestions appear below the input. The microphone has visible start, stop, permission-denied, unsupported-browser, and transcription-error states. Never auto-submit speech. Keep typed text when speech fails. No continuously listening microphone. Keyboard input, screen-reader labels, clear focus states, large controls, and plain English/Spanish copy are acceptance requirements.

For food, suggest useful distinctions: **meal ready to eat**, **groceries to cook**, **delivery**, **food for a medical diet**, and **help applying for food benefits**. Ask about cooking/refrigeration only when it changes which services fit. A pantry distribution is not necessarily ready-to-eat food. Frozen prepared meals may still require storage and reheating. Food-bank offices are not necessarily public pickup locations. Meals bundled with a care program are not public meal assistance.

Results show 3–5 concrete options, grouped by need when multiple needs are present. Each card has a service-specific reason supported by source text, next action, phone/address from the source, service hours if known, and missing eligibility details. A narrow card sidebar contains **the original reliability score**, its classification, and the last verification date. Retain source precision internally; presentation rounding must not change the score. Do not relabel tag-confidence as reliability.

Keep a visible filter rail for people who prefer browsing. Show counts after each filter and allow removing a filter without restarting. Examples: meal vs groceries, delivery vs pickup, cost, language, and access method. Display “not documented” rather than silently treating an unknown as a confirmed match. Do not display hundreds of broadly related resources as a personalized recommendation.

## One engine, two adapters

The website sends POST requests to Django. MCP clients call the same Python matching service through an MCP adapter. Both invoke one shared function and one resource repository. Replacing the website questionnaire does not require putting an MCP client in a resident's browser.

Proposed modules:

| Module | Responsibility |
|---|---|
| `resources/repository.py` | Load the workbook plus approved tag sidecar; preserve raw reliability metadata; index records by ID |
| `matching/schemas.py` | Typed extraction, constraints, follow-ups, result and evidence schemas |
| `matching/safety.py` | Safety routing before ordinary retrieval; no dependence on review-score thresholds |
| `matching/extraction.py` | LLM adapter for structured needs; provider timeout/error handling |
| `matching/eligibility.py` | Explicit, scoped hard constraints with supported/conflicting/unknown states |
| `matching/ranking.py` | Need fit, description similarity, verification recency and unchanged source reliability |
| `matching/service.py` | Orchestrate the pipeline and construct results from existing record IDs |
| `mcp_server/server.py` | Official Python MCP SDK adapter |
| `map/api.py` | Django POST adapter, request limits, CSRF/origin controls, safe error handling |
| `feedback/service.py` | Private recommendation outcomes, separate from public community posts |

The official Python SDK is the implementation dependency, not a custom protocol implementation. Start with local stdio transport for development. If a remote endpoint is required, use the SDK's supported HTTP transport with scoped authorization and origin protections; do not expose a local unauthenticated development server publicly. Confirm and pin the supported stable SDK release during implementation. Sources: [official Python SDK](https://github.com/modelcontextprotocol/python-sdk), [MCP security guidance](https://modelcontextprotocol.io/docs/2025-11-25/tutorials/security/security_best_practices).

## Matching pipeline

1. **Check safety first.** Fast deterministic rules cover explicit immediate danger, self-harm, medical emergencies, violence and child danger in supported languages. Ambiguous cases receive a structured safety classification before ordinary matching. Distinguish current danger from negated or historical language and document both missed-danger and false-alarm rates. If danger is detected, return approved crisis records immediately and skip normal ranking. Classifier uncertainty/outage must not silently route concerning input to ordinary results.
2. **Extract needs.** The LLM returns schema-validated JSON with multiple need categories/subtypes, urgency, optional neighborhood/ZIP, constraints, uncertainty and short follow-ups. Require evidence spans from user input. The model cannot supply resource names, addresses or phone numbers. Unknown values remain null. Invalid JSON, hallucinated enum values, conflicting facts and excessive questions are rejected or handled through a bounded repair/fallback path.
3. **Ask only useful questions.** Return one or two short questions if missing facts materially affect eligibility or service type. For “food today, no stove,” prioritize ready-to-eat options; do not force the user through unrelated questions. Avoid requesting names, DOB, exact home addresses or documentation numbers.
4. **Retrieve and filter deterministically.** Query approved tags first. Expand only within compatible services, never from food assistance to food regulation or from shelter to unrelated apartment rentals. Distinguish direct provision, partner/referral navigation, resident-only benefits and uncertain branch availability. Apply known hard exclusions only to reviewed, program-scoped eligibility facts. Unknown insurance is not accepted insurance; unknown documents are not “no ID required.” If a strict constraint cannot be confirmed, ask or report the gap rather than promise a match.
5. **Rank relevant candidates.** Use exact service/subtype coverage plus semantic similarity to the service description. Prevent generic parent/subtype double-counting. Prefer verified/recently checked records and use the existing reliability score as a bounded secondary signal, without recalculating it. A highly rated unrelated service must never outrank a directly relevant one. Do not exclude a crisis provider solely because of its public-review score. Diversity rules avoid five branches of one organization crowding out independent options and cover multiple needs.
6. **Construct grounded answers.** Select existing resource IDs, then hydrate contact details from the repository. Reasons are short description-supported statements, with evidence references. An optional rewriting model can simplify wording but cannot introduce new factual claims. Validate every returned ID and contact field against the source snapshot.
7. **Abstain when appropriate.** Return a clear no-match or partial-match state. Show a reviewed caseworker/resource-navigation or 211 record already in the repository. Do not force a weak match to fill five slots.

Emergency national contacts and the 211 fallback must have explicit approved directory entries before the database-only safety/fallback acceptance tests can pass. A generic organization office phone must not be substituted for its crisis line. The Phase 1 `crisis.intervention` tag is discovery evidence, not an approved crisis-routing registry. Verify the appropriate access channel separately.

The Phase 1 constraint tags intentionally describe **reported facts**. They are not yet complete machine-executable eligibility rules. Before hard filtering, reviewers must resolve program scope, age OR-conditions, service area, accepted plan details, and any contradiction. A 62+ OR disability housing rule cannot become “exclude everyone under 62.” Site hours cannot become pantry pickup hours.

## MCP and website contracts

| Interface | Behavior |
|---|---|
| `find_resources(need_text, location?, constraints?)` | Calls the core; returns `crisis`, `follow_up`, `matches`, `partial_match`, `no_match`, or `unavailable` |
| `get_resource(resource_id)` | Returns the full source record and separately labeled approved tag metadata; unknown ID is an error |
| `list_tags()` | Returns the versioned approved taxonomy, labels and available counts |
| `submit_feedback(resource_id, helpful, comment?)` | Validates ID and boolean; rate-limits; stores a private outcome with an optional redacted comment |
| `POST /api/triage/` | Same request/response schema and core as `find_resources` |

A match includes resource ID, source snapshot version, name, actual contact fields, matched service tags, reason/evidence, raw reliability score/classification, verification date, and eligibility uncertainties. Return stable machine codes separately from localized wording. The caller never sets source verification, reliability, approval or eligibility truth. Add an idempotency key to outcome submission and keep it out of the public community-feedback model.

## Voice and privacy

Use browser speech recognition initially as an optional enhancement. It avoids building an audio-upload/storage path and lets users edit a transcript before submission. The tradeoff is uneven browser support and provider-dependent processing: browser recognition can send audio to a remote recognition service. It must not be described as guaranteed local/offline. Source: [MDN SpeechRecognition](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition).

Offer typing and point-and-click fallbacks everywhere. If consistent speech support later requires a transcription endpoint, use bounded in-memory streaming, an explicit processor/retention decision, and no audio files, request-body logs or analytics payloads. That processor decision must precede deployment.

Proposed input notice, to verify against the eventual provider configuration: “Tell us what help you need. You do not need to include your name or exact address. Baltimore Lifeline does not save your message or recording. Voice recognition may use your browser’s provider. Check the text before sending.”

Process intake text transiently and do not persist it by default. Store only aggregate outcomes and nonidentifying operational metrics. If a user explicitly submits a feedback comment, redact names, phone numbers, addresses and DOBs before storage; if redaction is uncertain, discard the text and keep only the helpful/not-helpful outcome. Never promise regex alone can remove all names. Keep raw intake out of query strings, browser storage, access logs, exception reports, traces, caches and analytics. Do not retain raw audio. Document third-party LLM/transcription processing honestly; application nonretention is not a promise about a vendor's practices.

Protect exact location as sensitive. Ask for neighborhood/ZIP when sufficient and do not automatically request GPS. Convert any volunteered identifying details to the minimum needed location representation before persistence (prefer no persistence). Source descriptions and client input are untrusted data, never system instructions. The extraction model has no tools, browsing, database-write permissions or secret access.

## Crowdsourced curation

Use small assigned review tasks, not an unrestricted public database editor. A task link identifies a resource and requested field, never a resident or intake transcript. Let volunteers verify one question such as “Are groceries available for pickup?” or “Which documents does this program require?”

The form shows the existing claim, source excerpt, website, and last verification date; reviewers choose confirmed, corrected, unavailable, or could not verify. Require an evidence URL or dated call-verification note. Collect program/location scope separately from the organization. Make “I could not verify this” a useful completion, not a failure.

LLMs propose tags and detect inconsistent wording. Deterministic routines validate IDs, allowed tags, evidence spans, stale source versions, dates, duplicates, contradictions and approval permissions. Qualified partner reviewers approve eligibility/crisis changes. Conflicting submissions enter a moderator queue; two independent confirmations can raise review priority without automatically changing scraped reliability scores.

Maintain an append-only proposal/review history with who changed what, source evidence, timestamps, previous values and rollback references. Feedback about recommendation helpfulness is a distinct signal and does not overwrite the web-scraped reliability score. No volunteer can approve their own privileged changes. Use expiring signed links, authentication for approval, rate limits and clear “already reviewed” states.

Reward completed, evidence-supported reviews rather than positive ratings or raw volume. Options include partner-recognized service hours, acknowledgment, or a fixed small stipend under an explicitly funded program. Never tie incentives to referrals, patient information, favorable ratings or approval outcomes. No invitations, reward commitments, messages or external writes have been sent in Phase 1.

## Evaluation and release gates

The initial hand-authored cases are in `evaluation/triage_cases.json`. They are expectations, not completed MCP evaluations. Include messy language, Spanish, multiple needs, missing information, no-cook food, delivery eligibility, insurance uncertainty, crisis and non-crisis contrasts, and prompt injection.

After the core exists:

1. Expand to at least 200 independently authored cases with approved expected categories and acceptable resource IDs. Keep a held-out split, especially for crisis and eligibility cases.
2. Run at least 2,000 reproducible variants (typos, reordered constraints, code-switching and distracting text) and report them separately from independent cases. Do not use model agreement as correctness ground truth.
3. Measure category precision/recall, multi-need coverage, precision@3, recall of acceptable resources@5, hard-constraint violations, justified abstentions, crisis sensitivity and false alarms, grounding violations, latency and cost. Report denominators, confidence intervals where useful, and each failure by case ID.
4. Require every labeled crisis case to reach the crisis route with approved crisis records, zero ordinary resources, and zero fabricated contact information. This is a test-suite requirement, not a claim of perfect real-world detection.
5. Require zero invented resource IDs/contact details and zero known hard-constraint violations. Report coverage lost to unknown eligibility rather than hiding it.
6. Exercise live MCP protocol calls, all four tools, invalid schemas, cancellation, timeouts, duplicate feedback, denied writes, wrong IDs, concurrent requests and provider outages. Run the same cases through the website API and confirm identical core results.
7. Check English/Spanish text flows, microphone permission and failure states, transcript editing, mobile layout, keyboard/screen-reader behavior, and preserved questionnaire fallback. Inspect logs and analytics for sensitive text leakage with synthetic PII fixtures.
8. Pilot with residents and partner caseworkers on adjudicated cases. Keep the old flow available and roll back through a feature flag if precision or safety regressions appear.

Phase 1 tests validate the audit and migration planner only. They do not establish retrieval accuracy, successful live MCP operation, voice behavior, or clinical safety performance.
