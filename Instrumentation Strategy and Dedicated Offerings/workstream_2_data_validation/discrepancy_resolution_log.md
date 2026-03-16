# Discrepancy Resolution Log — Data Validation & Reconciliation

> **Version:** 1.0  
> **Last Updated:** 2026-03-16  
> **Owner:** Data Platform Team  
> **Location:** Updated weekly following each reconciliation run  

---

## Purpose

This log tracks every data discrepancy discovered during reconciliation between the raw event pipeline and the BI layer. Every 🟡 WARNING and 🔴 FAILURE from the reconciliation runbook must be logged here until resolved.

---

## Discrepancy Types

| Code | Type | Description |
|------|------|-------------|
| `ROW_COUNT` | Row Count Mismatch | Difference in event counts between raw and transformed layers |
| `MISSING_EVENT` | Missing Events | Events present in raw but absent from BI, or vice versa |
| `DUPLICATE` | Duplicate Events | Same `event_id` appearing multiple times in a layer |
| `NULL_FIELD` | Null/Missing Field | Required property is NULL or empty on critical events |
| `SCHEMA_DRIFT` | Schema Drift | Column added/removed/renamed without model update |
| `TIMEZONE` | Timezone Mismatch | Date boundary misalignment causing count shifts |
| `LATE_ARRIVAL` | Late-Arriving Data | Events ingested after the transformation window closed |
| `FILTER` | Filter Mismatch | Inconsistent `WHERE` clauses between raw pull and dbt model |

---

## Resolution Log

| # | Date Discovered | Event Name | Discrepancy Type | Severity | Raw Count | BI Count | Variance % | Root Cause | Resolution | Owner | Status | Date Resolved |
|---|----------------|------------|------------------|----------|-----------|----------|------------|------------|------------|-------|--------|---------------|
| 1 | 2026-03-03 | `dedicated_pipeline_executed` | `ROW_COUNT` | 🟡 WARN | 148,230 | 147,812 | 0.28% | Late-arriving events from `tenant_acme_prod`. Pipeline ran before all events landed. | Extended dbt schedule buffer from 2h to 4h. Added reprocessing step for T-1 data. | @data-eng-jane | ✅ Resolved | 2026-03-05 |
| 2 | 2026-03-03 | `dedicated_onboarding_step_completed` | `NULL_FIELD` | 🔴 FAIL | 12,405 | 12,405 | 0% | `step_name` property is NULL for 342 events from SDK v2.1.3. | SDK bug fixed in v2.1.4. Backfilled NULL `step_name` using `step_index` mapping. | @sdk-team-alex | ✅ Resolved | 2026-03-07 |
| 3 | 2026-03-10 | `dedicated_mr_created` | `MISSING_EVENT` | 🔴 FAIL | 8,921 | 0 | 100% | New event added to SDK but dbt model not updated. | Added `dedicated_mr_created` to `fct_dedicated_events` model. | @data-eng-priya | ✅ Resolved | 2026-03-11 |
| 4 | 2026-03-10 | `dedicated_nav_section_clicked` | `DUPLICATE` | 🟡 WARN | 45,100 | 52,340 | 16.05% | Client SDK double-firing on single-page-application route changes. | SDK fix deployed to debounce navigation events (200ms window). Dedup applied in dbt. | @sdk-team-alex | ✅ Resolved | 2026-03-14 |
| 5 | 2026-03-16 | `dedicated_security_scan_completed` | `LATE_ARRIVAL` | 🟡 WARN | 3,280 | 3,105 | 5.34% | Scans completing at end-of-day UTC arrive after T+0 transformation run. | Investigating: evaluating a T+1 reprocessing model for scan events. | @data-eng-jane | 🔄 In Progress | — |
| 6 | 2026-03-16 | `dedicated_user_invited` | `TIMEZONE` | 🟡 WARN | 1,450 | 1,423 | 1.86% | Raw events use `event_timestamp` (UTC); one dbt intermediate model casts to `America/New_York` before date extraction. | Under review: standardizing all dbt models to use UTC. | @data-eng-priya | 🔍 Investigating | — |

---

## Status Definitions

| Status | Meaning |
|--------|---------|
| 🔍 **Investigating** | Root cause is being analyzed |
| 🔄 **In Progress** | Fix is being implemented |
| ✅ **Resolved** | Fix deployed and verified in next reconciliation |
| 🚫 **Won't Fix** | Accepted variance — documented justification required |

---

## Escalation Rules

1. Any 🔴 FAIL that remains unresolved for **> 3 business days** must be escalated to the Data Platform Engineering Manager.
2. Any discrepancy affecting a **P0 event** must be escalated immediately, regardless of severity.
3. Recurring discrepancies (same event, same type, 3+ occurrences) trigger a **root cause review** meeting with the owning SDK and data engineering teams.

---

## Metrics & Trends

### Weekly Health Summary

| Week | Total Checks | 🟢 Pass | 🟡 Warn | 🔴 Fail | Overall Health |
|------|-------------|---------|---------|---------|----------------|
| 2026-W09 (Feb 24 – Mar 02) | 15 | 13 | 2 | 0 | 🟢 Healthy |
| 2026-W10 (Mar 03 – Mar 09) | 15 | 11 | 2 | 2 | 🟡 Degraded |
| 2026-W11 (Mar 10 – Mar 16) | 18 | 14 | 2 | 2 | 🟡 Degraded |

> **Target:** 100% 🟢 PASS rate within 90 days of instrumentation program launch.
