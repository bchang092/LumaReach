# Triage evaluation — 2026-10-24

Historical report. See [November 8 results](NOV08_REPORT.md) for the current ten-result implementation, HTTP MCP and browser testing.

Implementation is validated locally with conservative abstention. **Live LLM accuracy and real-browser/microphone behavior remain unverified.** The API account returned `429 / credit_balance_exhausted`; all non-crisis requests in the attempted live run used the fallback parser. No production deployment occurred.

## Results

| Check | Result |
| --- | --- |
| Authored inputs | 104 (64 initial + 40 challenge) |
| Exact category sets | 103/104 (99.0%) |
| Exact expected routes | 86/104 (82.7%) |
| Authored crisis cases | 40/40 routed to crisis contacts, zero normal matches |
| Perturbed inputs | 4,160 |
| Crisis perturbations | 1,600/1,600 routed safely |
| Directory grounding | 4,160/4,160; returned records equal directory records, reasons are description excerpts |
| Top-three service relevance review | 53/53 supported by descriptions; implementation-agent review |
| Automated top-three service-tag precision | 100% when results were returned; a tag-level proxy, not eligibility accuracy |
| Django tests | 51 passed, including all existing tests |
| Audit tests | 24 passed, including 2,000 rule perturbations |
| UI behavior tests | 10 passed in jsdom (9 intake + map subtype/reset/reliability) |
| MCP | Real official-SDK stdio client/server round trip; 4 tools; 6 core parity cases; private feedback |
| Migration | Dry-run no-write; apply; rollback/delete; byte restoration; stale rollback rejection |
| HTTP smoke | Real server, CSRF-protected POST, food and Medicaid matches, crisis response, no-store headers |

The matching runs returned 31 match responses, 21 no-match responses, 12 follow-ups and 40 crisis responses. This coverage tradeoff matters: precision is improved partly by refusing unsupported matches. Fewer than three resources are returned if only one or two qualify.

## Limits and failure analysis

These are development/regression inputs, not an independent clinical test set. Challenge failures were used to improve the code, so the final challenge score is not held-out accuracy. The 4,160 variants repeat the 104 authored meanings using case, spacing, punctuation, apostrophes and conversational prefixes; they are not 4,160 independent scenarios. The additional 2,000 audit-rule perturbations test tagging rules, not matching.

`service_relevance_review.json` records a reading of all final top-three descriptions from the initial set. It supports the narrower claim that the offered service is relevant to at least one requested need. It does not establish provider acceptance, a resident’s eligibility, same-day availability, successful outcomes, or complete coverage of every need. No caseworker adjudication has been performed.

Exact-route differences below are mostly conservative no-matches: the original expectations requested matches before eligibility facts were available. They are retained visibly rather than relabeling the tests as successes. The single category difference is the adversarial request for an invented free food bank: the fallback identifies a pantry, while the original expected generic food assistance. It returns no invented record.

| Case | Expected route | Actual route | Category set matches |
| --- | --- | --- | --- |
| food_04 | matches | no_match | yes |
| food_06 | matches | no_match | yes |
| housing_03 | matches | no_match | yes |
| housing_06 | matches | no_match | yes |
| medical_01 | matches | no_match | yes |
| medical_02 | matches | no_match | yes |
| medical_03 | matches | no_match | yes |
| mental_01 | matches | no_match | yes |
| mental_03 | matches | no_match | yes |
| mental_04 | matches | no_match | yes |
| mental_05 | matches | no_match | yes |
| mental_06 | matches | no_match | yes |
| support_05 | matches | no_match | yes |
| support_06 | matches | no_match | yes |
| spanish_03 | matches | no_match | yes |
| spanish_05 | matches | no_match | yes |
| adversarial_01 | follow_up | no_match | no |
| challenge_noncrisis_09 | matches | no_match | yes |

Remaining causes include unconfirmed no-ID access, fresh-food formats, Medicaid primary/dental care, prescription costs, evening therapy, outpatient-only treatment, harm-reduction access, affordable housing, general grief support, Suboxone-specific programs, diaper supplies, Spanish-speaking clinical care, free tax help, and out-of-region or vague descriptions. The 725 flagged source records remain outside normal matching. Human review could improve coverage without weakening eligibility checks.

## Fixes driven by testing

- Removed distant pantry matches from Baltimore ranking and added locality preference.
- Added service-specific gates for SNAP versus health insurance, eviction versus unrelated legal help, pet food versus animal control, clinic rides versus interview travel, cancer-specific grief groups, veteran-specific services, childcare versus adult daycare, and employment versus incidental mentions of work.
- Corrected two active false childcare tags on adult daycare records; the original audit and subsequent correction/rollback files remain reviewable.
- Extended safety detection for indirect English and Spanish expressions, overdose, threats, child danger and self-harm. Historical/negated language is handled separately; current danger cannot be overridden by the model.
- Fixed Django feedback writes from the asynchronous MCP runtime.
- Ensured crisis routing works without the normal workbook/index and after API rate limiting.
- Ensured voice never auto-submits, late voice results cannot repopulate cleared input, and resource text cannot inject HTML or unsafe links.

## Remaining release checks

1. Restore API credits and run both authored sets with `--live`. The evaluator exits with status 2 when any normal request falls back, preventing false live-model pass claims.
2. Have qualified caseworkers review acceptable resource IDs, eligibility, false positives, no-matches and crisis wording on new held-out inputs.
3. Test desktop/mobile visual layout, keyboard/screen-reader behavior, microphone permissions, speech quality and browser support in actual browsers. No browser connection was available during implementation.
4. Configure production secrets/shared rate limits, run migrations and collectstatic, then deploy through the existing process. No partner invitations or external messages were sent.

Machine-readable evidence: `final_summary.json`, `offline_results.json`, `challenge_results.json`, `robustness_results.json`, `challenge_robustness_results.json`, `service_relevance_review.json`, and the explicitly failed initial `live_results.json`.
