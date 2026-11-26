# Triage operations, data and privacy

## Source integrity and activation

The authoritative workbook's SHA-256 is `e7bd62fdcd50bfd08648a12df9c0a374771e4a1949823611d85b7e9e47b52f41`. Its 1,341 records and six protected reliability/verification fields were not rewritten. A cached in-memory repository loads the workbook plus additive JSON files; there is no new resource SQL import.

`audits/phase0/recon.json` contains original tag counts, the complete zero-tag inventory and five complete workbook records. `audits/phase1/resource_tag_proposals.json` preserves the original 1,362-row audit. `activation_review.json` records authorization to activate only its 637 unflagged records. The remaining 725 flags have not been cleared or represented as human-reviewed. `childcare_correction_review.json` subsequently removes two erroneous childcare tags from adult daycare resources 487 and 581. The November 8 review reviews another 30 records (26 tag/scope changes and four scope confirmations) in `nov08_service_corrections.json`. Historical proposal artifacts are preserved; the generator now includes the corrections by default, with `corrections=False` available only to reproduce the historical audit.

The active sidecar is `input_data/resource_tags.json`. Source hashes and evidence spans bind it to this exact workbook. Replacing the workbook requires a fresh audit; mismatches stop normal matching. Crisis contacts are read independently and remain available if the normal workbook/index fails.

`input_data/eligibility_facts.json` contains 10 explicit, narrowly scoped description and restriction facts reviewed during integration. Each includes the original snippet, resource hash, service need, constraint, decision and source URL. Examples: Medicaid acceptance for the described therapy programs; no-charge equipment loans for children; a weekly Saturday pantry; paid immigration consultations. This was a review of existing descriptions, **not a new provider call**. No inferred generalizations from free subprograms, office hours, organization names, or population labels are allowed. A matching `allows` fact means source-supported, not guaranteed eligibility or current availability. Explicit exclusions win; missing hard facts exclude a candidate. Optional preferences do not block matching.

New source-checked safety/navigation entries use IDs 900001–900004 in `input_data/safety_directory.json`. These are explicit directory records, never model-generated recommendations. They have provenance URLs/dates and no invented reliability score. TurnAround's hotline is a separate contact from organization office numbers in the workbook.

The three approved display typo corrections live in `lifeline_core/display.py`; original descriptions and evidence remain intact. MCP taxonomy counts come from the active workbook tags. Active tag inventories are visible through resource records.

## Migration and rollback

The CLI defaults to dry-run. It validates complete coverage, approval metadata, exact evidence and hashes, and writes only an independent JSON sidecar. No workbook save operation is used. Approval files contain source snapshots, not resident data.

```sh
.venv/bin/python scripts/tag_migration.py --review path/to/approved_review.json --dry-run
.venv/bin/python scripts/tag_migration.py --review path/to/approved_review.json --apply --backup path/to/new_rollback.json
.venv/bin/python scripts/tag_migration.py --rollback path/to/new_rollback.json --dry-run
.venv/bin/python scripts/tag_migration.py --rollback path/to/new_rollback.json --apply
```

The November transfer is reproducible with `scripts/transfer_november_tags.py`. It reads the archived September sidecars and both workbook snapshots. For the historical September activation, undo `audits/phase1/nov08_service_corrections_rollback.json` first (the prior bytes were reconstructed and checked against the earlier migration fingerprint), then undo the childcare correction with `audits/phase1/childcare_correction_rollback.json`, then the initial activation with `audits/phase1/activation_rollback.json`. Rollback guards bind the original absolute target and exact post-migration bytes. If the checkout moves, prepare a reviewed migration at the new path instead of defeating that guard. The CLI refuses stale/concurrent rollback. Removing the active sidecar disables normal triage; keep the map/questionnaire available during rollback.

Django migration `0003` adds two separate tables: private recommendation outcomes and source-tag review proposals. Existing community posts are not reused or republished. It was applied and tested locally, then the tracked SQLite file was restored byte-for-byte. The migrated preview/test database and backup are isolated under `.local/`. A normal local launch and production deployment must run the migration step.

## Curation

Generate a seven-day signed invitation without sending it:

```sh
.venv/bin/python manage.py create_review_link 87 --base-url https://www.baltimorelifeline.site
```

Anyone holding that link can propose a service tag with an exact source-description excerpt. No client/resident text belongs in this form. The signature protects resource selection and expiry; CSRF protects browser submissions. Identical proposals are deduplicated. Reviewers cannot edit reliability, source records or active tags. Staff moderate `ResourceTagReview` in Django admin. “Accepted for audit” is a queue decision, **not automatic activation**. A moderator must incorporate accepted evidence into a complete reviewed file and run the validated migration. Program eligibility requires the separate scoped-fact review. Use descriptions and provider calls to resolve unsupported, closed, branch-specific or referral-only records.

Keep reviewer incentives independent of positive ratings or acceptance. A fixed, funded review stipend or documented service hours could work; no payment or messaging system is enabled by this change. The moderation workflow is intentionally small and reviewable.

## Matching behavior

Normal retrieval includes only activated service tags with direct-description scope. Additional deterministic gates reject wrong contexts such as adult daycare for childcare, crime-victim legal services for eviction, clinic-only rides for job interviews, or cancer-only grief groups without cancer context. The initial source audit still has coarse tags; these runtime gates and the review queue matter.

Locations are not geocoded externally. An explicit ZIP/address match boosts ranking. A supported ZIP uses the midpoint of directory coordinates for an approximate origin; otherwise central Baltimore is clearly labeled. Normal candidates are capped at approximately 35 miles from central Baltimore using source coordinates, and known out-of-region service descriptions are excluded. Unknown neighborhood names trigger a Baltimore-area confirmation question; do not claim exact distance from the resident. Requested service area restrictions are hard constraints only with scoped facts. Availability today, appointment openings, and all eligibility conditions are not known.

Ranking checks service need coverage and preferences, then gives source reliability and proximity equal weight. Each contributes up to 0.5 points. Proximity declines linearly over 35 straight-line miles from the estimated origin. Multi-need coverage is reserved before filling up to ten slots, then the chosen set is sorted by descending score; fewer are returned if fewer fit. Reasons are short excerpts of original descriptions. No-score safety records are separate from normal ranking.

## Privacy and deployment

- Intake text exists only in request/browser memory. It is not written to SQL, sessions, files, local/session storage, analytics, URLs or application logs. Do not enable request-body logging or third-party replay/analytics on `/help/`, `/api/triage/`, or MCP tools.
- Text is sent to OpenAI only when configured and enabled, with Responses `store=False`. Provider-level retention may still apply; this is stated in the interface. Do not claim `store=False` is zero data retention.
- Browser SpeechRecognition may send audio to the browser vendor. Alternatively, `VOICE_USE_API=true` enables bounded MediaRecorder capture and `/api/transcribe/` with server-held credentials. Audio is handled in memory, sent to OpenAI when recording stops, and not persisted by this app. Provider retention policies apply. The interface discloses the active path. The microphone is optional, English/Spanish selectable, and never auto-submits. Unsupported browsers use typing.
- Feedback saves only resource ID, helpful boolean and timestamp. Free-text comments are discarded rather than applying unreliable name-redaction rules. Outcome feedback is never posted to the public community board or emailed.
- JSON endpoints use POST, CSRF, no-store responses, input limits, strict schemas and generic errors with no echoed exceptions. Rate limiting stores only minute-scoped HMAC keys. Crisis routing remains available after a rate limit. The default cache is process-local; configure a shared Django cache or edge rate limiter for multiple production workers.
- Browser text clears on explicit clear/pagehide. Leaving the page does not erase browser history, vendor speech history, or MCP client logs. The notice does not promise those protections.
- Do not attach error/session replay tools that capture request locals. The wrappers mark sensitive input and swallow raw SDK exceptions. Operator diagnostics may report error classes/codes only, without input or key values.
- MCP defaults to local stdio. Optional Streamable HTTP requires a dedicated bearer credential and exact host/origin validation. See `mcp_server/README.md`; interactive OAuth requires an identity gateway and public deployments require shared edge limits and HTTPS.

## Verification limits

See `evaluation/NOV08_REPORT.md` for current evidence and `docs/SETUP_AND_LIMITATIONS.md` for deployment steps. Offline tests are not clinical validation. Live AI quality is unverified. Actual Chromium rendering and synthetic microphone capture have been tested; human speech, mobile browsers and screen-reader operation still need manual checks. No production deployment or partner messages were sent.

References: [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk/tree/v1.x), [SpeechRecognition](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition), [211 Maryland](https://211md.org/about/), [TurnAround](https://www.turnaroundinc.org/), [National 911 Program](https://www.911.gov/calling-911/frequently-asked-questions/). The 988 contact was checked with the connected hotline directory tool.
