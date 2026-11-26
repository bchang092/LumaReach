# Tag audit review

**Historical Phase 1 instructions.** Activation and subsequent corrections have since been implemented. See [current operations](../../docs/TRIAGE_OPERATIONS.md) and [November 8 corrections](nov08_service_corrections.json). The statements below describe the original proposal checkpoint.

Phase 1 is a proposal. No SQL migration, workbook edit, active tag deployment, or reliability-score change has been performed.

- `resource_tag_proposals.json`: all 1,362 resources, old tags/category, proposed tags, exact source evidence spans and sentence context, scope, confidence, review flags, notes, approval fields, and the source snapshot.
- `taxonomy.json`: two layers, need categories with service subtypes and reported constraint/access tags. Only tags with supporting records are included.
- `old_to_new_tags.json`: category-to-proposed-need counts. There were no old resource tags. This is not a global replacement map.
- `summary.json`: current counts, confidence distribution, review reasons and tag frequencies.
- `display_corrections.json`: small display-only typo suggestions; the raw text remains unchanged.

The full source descriptions were inspected individually. Conservative rules produce reproducible proposals, with explicit record-specific decisions for vague, closed, misleading or scoped descriptions. This is not an independent verification of the underlying scraped claims. Confidence describes the tag assignment, not service quality or the existing reliability metric.

`new_tags` contains `need:<category>.<subtype>` for services and named constraint tags such as `access.walk_in_reported`. Every tag has a verbatim snippet and full context. `source.protected_metadata` retains the original reliability score, classification, confidence, reliability description and date. Neither names nor legacy categories supply evidence for new services.

Constraints come from descriptions, restrictions and service hours, as authorized in the October 24 clarification. Population served is not exclusive eligibility. Site opening hours are not program intake hours. All `hard_filter_eligible` values remain false: these are discovery/review facts, not unscoped exclusion rules. Program-level eligibility must be confirmed before the future matcher uses it as a hard filter.

## Review procedure

Review a copy of `resource_tag_proposals.json`. Preserve its source snapshot and resource IDs. Correct `new_tags` and the corresponding `evidence` together; evidence must point into `description`, `restrictions`, or `hours`, and need tags must have description evidence. Resolve every reason on a flagged record, document the resolution in notes, then set `review_flag` to false and clear `review_reasons`. Set `approved` to true, `reviewer` to the reviewer's identity, and `reviewed_at` to an ISO timestamp with timezone. Pending records remain unapproved and are not applied. Do not bulk-clear flags without checking them.

Do not treat “no supported need” as a deletion request. Those source rows remain intact and require better program information or an explicit determination that they are outside this directory's matching scope. No additional tag should be invented to hide a gap.

The proposal builder is bound to the audited workbook SHA-256. If the source changes, re-audit before regenerating ID-specific decisions. Do not rerun the builder over a human-reviewed copy: keep the review copy separate.

## Prepared migration commands — not executed

The migration writes `input_data/resource_tags.json`, an additive sidecar, using only approved records. It does not modify the master workbook, reliability calculations, Django tables, or website behavior. The future matching repository will consume this sidecar after approval.

Dry-run after review:

```sh
python3 -B scripts/tag_migration.py --review path/to/approved_review.json --dry-run
```

Apply only after approval:

```sh
python3 -B scripts/tag_migration.py --review path/to/approved_review.json --apply --backup path/to/new_tag_backup.json
```

Rollback preview, then rollback if approved:

```sh
python3 -B scripts/tag_migration.py --rollback path/to/new_tag_backup.json --dry-run
python3 -B scripts/tag_migration.py --rollback path/to/new_tag_backup.json --apply
```

Dry-run is the default and writes nothing. Application requires an exclusive new backup, uses an atomic sidecar replacement, and locks concurrent migration attempts. Review validation rejects stale source hashes, altered source snapshots, duplicate/missing IDs, invented tags, invalid evidence, unapproved/no-op batches and unresolved flags. Rollback refuses to overwrite a sidecar changed since the migration and restores the prior bytes (or removes a newly created sidecar). Back up the repository normally as well; the sidecar backup does not constitute a database backup.

The CLI's write/rollback paths have not been executed, including in dry-run. Pure validation and rollback-planning functions were exercised in memory by `scripts/test_tag_audit.py`. Atomic filesystem writes still require an isolated integration test before any real application.

## Checks

```sh
python3 -B scripts/test_tag_audit.py
```

This checks full source coverage, source/evidence preservation, conservative food/clinical/access distinctions, closure flags, unmodified reliability metadata, approval validation, and rollback preconditions. The 2,000 generated negation/case/punctuation variants are rule assertions, not 2,000 independently authored matching prompts or live MCP tests.

See `docs/TRIAGE_DESIGN.md` for the shared core, MCP interfaces, website layout, voice tradeoffs, crowdsourced review workflow, privacy and evaluation plan.
