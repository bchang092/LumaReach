# Ranked voice search validation — November 8, 2026

The implementation now supports up to ten scored results, validated active tag evidence, stdio and authenticated HTTP MCP, and optional server audio transcription. **No live OpenAI extraction or transcription quality was established in this pass. No production deployment occurred.**

## Measured checks

| Check | Result |
| --- | --- |
| Django backend suite | 73 passed |
| Tag audit suite | 25 passed, including 2,000 rule perturbations |
| UI DOM behavior suite | 16 passed |
| MCP stdio | Real official-client initialization, four tools, six core-parity cases, lookup/taxonomy/feedback |
| MCP HTTP | Real TCP/official-client initialization; authentication, startup guards, host/origin/body limits, tool schemas, four parity cases, result limits, scoped constraints, feedback |
| Migration IO | Dry-run, apply, rollback/delete, exact byte restoration and stale rollback rejection passed |
| Correction rollback | Dry-run accepted; reconstructed prior bytes matched the historical backup fingerprint |
| Chromium | Ten ranked cards, doctor regression, 390px layout without horizontal overflow, zero page errors |
| Accessibility | No serious/critical axe findings in the tested main content; not a full accessibility certification |
| Voice capture | Actual Chromium MediaRecorder with a synthetic microphone; nonempty audio upload, editable mocked transcript, no automatic search |
| Authored scenarios | 104; exact need sets 103/104 (99.0%), exact expected routes 86/104 (82.7%) |
| Authored crisis scenarios | 40/40 routed to crisis support with no normal matches |
| Perturbed inputs | 4,160; 4,160/4,160 grounding and rank/bound checks passed |
| Crisis perturbations | 1,600/1,600 routed as expected |
| Top-ten tag relevance proxy | 100% when matches returned; **not** independently adjudicated eligibility or actual service quality |

The 104 authored cases returned 31 match responses and 21 no-match responses; the rest were follow-ups or crisis routes. Exact-route mismatches are retained in the machine-readable reports rather than relabeled to inflate success. Most reflect insufficient source evidence for hard requirements such as insurance, cost, documents or hours. The category mismatch is the pre-existing adversarial “invent a free food bank” case; no invented provider was returned.

The 4,160 variants repeat 104 meanings with case, spacing, punctuation and introductory phrases. They are not independent scenarios or held-out accuracy measurements. The development cases informed fixes. New independently authored cases, provider verification and caseworker review remain necessary.

## Fixes that the tests exercise

- Ten-result bounds, stable descending scores, evidence grounding, duplicate handling, coverage of multiple needs, scoped preference scoring and approximate ZIP origins.
- Thirty records reviewed: ten unsupported service tags removed, sixteen service scopes corrected and four existing scopes confirmed. Patient lodging, non-medical home care, peer-led support and emergency-only programs no longer masquerade as general medical/clinical services.
- Requests for a doctor now work; incidental doctor context in medical diets does not create a new medical need. Declined groceries, negated insurance and adult-versus-child ages have regressions.
- General searches exclude unsupported pediatric, veteran-specific and domestic-violence-specific contexts. These conservative gates can miss suitable programs too; they do not prove exclusive eligibility.
- Every active tag is checked against the taxonomy, source hash, exact span/context, scope and reviewer metadata on load. Corrupted evidence fails closed.
- Small/empty semantic indexes, nonfinite/missing coordinates and future verification dates are handled conservatively.
- Audio tests cover disabled/missing credentials, CSRF, request method, size/type, language, empty/oversized transcript, API failure, rate limit and no database persistence.
- UI tests cover denied microphone permission, cancellation while permission is pending, discarded recordings, late transcription/search responses after clearing, safe text/link rendering and feedback.
- Both transports share the same Baltimore-local date for freshness, avoiding score differences between server and client processes with different time zones.

The migration test also exposed an assumption that pre- and post-migration JSON bytes were identical. It now restores the actual applied bytes before testing rollback, so formatting changes cannot accidentally bypass or falsely fail stale-content protection.

## Outstanding checks

Live structured interpretation, model access, API billing and human speech transcription remain untested. Chromium synthetic input does not establish accent/noise recognition, mobile Safari/Android operation or real microphone permission behavior. The automated accessibility scan does not replace keyboard and screen-reader testing.

The catalog still has 725 records awaiting review and only 12 scoped eligibility facts. Provider availability, intake schedules, geographic service areas and the meaning of scraped reliability scores need independent verification. The public HTTP deployment needs HTTPS, shared edge limits and secrets; OAuth-only clients need an identity gateway. See [setup and limitations](../docs/SETUP_AND_LIMITATIONS.md).

Evidence: [summary](nov08_summary.json), [authored results](nov08_offline_results.json), [challenge results](nov08_challenge_results.json), [variants](nov08_robustness_results.json), [challenge variants](nov08_challenge_robustness_results.json), [service corrections](../audits/phase1/nov08_service_corrections.json). Local browser screenshots are in `.local/browser-results/` and can be regenerated with `node scripts/test_browser.cjs`.
