# Reconciliation Runbook — Data Validation & Event Pipeline Integrity

> **Version:** 1.0  
> **Last Updated:** 2026-03-16  
> **Owner:** Data Platform Team  
> **Cadence:** Weekly (every Monday) + ad-hoc after pipeline deployments  

---

## 1. Purpose

This runbook ensures 100% alignment between raw event logs captured from GitLab Dedicated tenants and the aggregated metrics displayed in the BI layer. It defines a repeatable process for detecting, quantifying, and resolving data discrepancies.

---

## 2. Architecture Overview

```
┌──────────────────┐     ┌───────────────────┐     ┌──────────────────┐     ┌────────────────┐
│  Client/Server   │────▶│ Raw Event Logs     │────▶│ Transformation   │────▶│ BI Dashboards  │
│  SDK (Snowplow)  │     │ (Snowflake RAW)    │     │ Layer (dbt)      │     │ (Looker/Tableau)│
└──────────────────┘     └───────────────────┘     └──────────────────┘     └────────────────┘
       Source              raw.dedicated_events      analytics.fct_events     Dashboard KPIs
```

---

## 3. Step-by-Step Reconciliation Process

### Step 1: Pull Raw Event Counts from the Source

Connect to the Snowflake RAW schema and retrieve total event counts for the reconciliation window.

```sql
-- Raw event counts by event_name for a given date range
-- Schema: raw.dedicated_events
SELECT
    event_name,
    DATE(event_timestamp)                     AS event_date,
    COUNT(*)                                  AS raw_event_count,
    COUNT(DISTINCT event_id)                  AS raw_distinct_event_count,
    COUNT(DISTINCT tenant_id)                 AS tenants_reporting
FROM raw.dedicated_events
WHERE event_timestamp >= '{{ start_date }}'
  AND event_timestamp <  '{{ end_date }}'
GROUP BY event_name, DATE(event_timestamp)
ORDER BY event_date, event_name;
```

**Parameters:**
- `{{ start_date }}`: Beginning of the reconciliation window (inclusive), e.g., `2026-03-10`
- `{{ end_date }}`: End of the reconciliation window (exclusive), e.g., `2026-03-17`

### Step 2: Pull Aggregated Counts from the BI Layer

Query the transformed dbt model that feeds the BI dashboards.

```sql
-- Transformed event counts from the analytics layer
-- Schema: analytics.fct_dedicated_events
SELECT
    event_name,
    event_date,
    COUNT(*)                                  AS bi_event_count,
    COUNT(DISTINCT event_id)                  AS bi_distinct_event_count,
    COUNT(DISTINCT tenant_id)                 AS tenants_in_model
FROM analytics.fct_dedicated_events
WHERE event_date >= '{{ start_date }}'
  AND event_date <  '{{ end_date }}'
GROUP BY event_name, event_date
ORDER BY event_date, event_name;
```

### Step 3: Diff / Comparison

Join the raw and BI datasets to surface discrepancies.

```sql
-- Reconciliation comparison: raw vs. BI layer
WITH raw_counts AS (
    SELECT
        event_name,
        DATE(event_timestamp)                 AS event_date,
        COUNT(DISTINCT event_id)              AS raw_count
    FROM raw.dedicated_events
    WHERE event_timestamp >= '{{ start_date }}'
      AND event_timestamp <  '{{ end_date }}'
    GROUP BY event_name, DATE(event_timestamp)
),
bi_counts AS (
    SELECT
        event_name,
        event_date,
        COUNT(DISTINCT event_id)              AS bi_count
    FROM analytics.fct_dedicated_events
    WHERE event_date >= '{{ start_date }}'
      AND event_date <  '{{ end_date }}'
    GROUP BY event_name, event_date
)
SELECT
    COALESCE(r.event_name, b.event_name)      AS event_name,
    COALESCE(r.event_date, b.event_date)      AS event_date,
    COALESCE(r.raw_count, 0)                  AS raw_count,
    COALESCE(b.bi_count, 0)                   AS bi_count,
    COALESCE(r.raw_count, 0) - COALESCE(b.bi_count, 0) AS count_diff,
    CASE
        WHEN COALESCE(r.raw_count, 0) = 0 THEN NULL
        ELSE ROUND(
            ABS(COALESCE(r.raw_count, 0) - COALESCE(b.bi_count, 0))
            * 100.0 / r.raw_count, 4
        )
    END                                       AS variance_pct,
    CASE
        WHEN COALESCE(r.raw_count, 0) = 0 AND COALESCE(b.bi_count, 0) > 0
            THEN '🔴 ORPHAN IN BI'
        WHEN COALESCE(b.bi_count, 0) = 0 AND COALESCE(r.raw_count, 0) > 0
            THEN '🔴 MISSING FROM BI'
        WHEN ABS(COALESCE(r.raw_count, 0) - COALESCE(b.bi_count, 0))
             * 100.0 / NULLIF(r.raw_count, 0) > 0.1
            THEN '🟡 VARIANCE EXCEEDS THRESHOLD'
        ELSE '🟢 PASS'
    END                                       AS reconciliation_status
FROM raw_counts r
FULL OUTER JOIN bi_counts b
    ON r.event_name = b.event_name
   AND r.event_date = b.event_date
ORDER BY reconciliation_status DESC, event_date, event_name;
```

### Step 4: Evaluate Results

Review the output using the threshold definitions below.

---

## 4. Threshold Definitions

| Status | Condition | Action Required |
|--------|-----------|-----------------|
| 🟢 **PASS** | Variance ≤ 0.1% between raw and BI counts | No action. Log result in weekly report. |
| 🟡 **WARNING** | Variance between 0.1% and 1.0% | Investigate within 2 business days. File a ticket if root cause is unclear. |
| 🔴 **FAILURE** | Variance > 1.0%, or events entirely missing from one layer | Escalate immediately. Page on-call data engineer. Block dashboard refresh if necessary. |

### Severity Escalation

1. **Self-resolving:** If a WARNING resolves in the next run (e.g., caused by a pipeline delay), close with a note.
2. **Persistent:** If a WARNING persists for 3+ consecutive runs, escalate to FAILURE.
3. **Critical:** Any FAILURE affecting a P0 event or a P0 dashboard metric triggers an incident per the Data Incident Response process.

---

## 5. Post-Reconciliation Checklist

- [ ] All 🟢 PASS — no action needed
- [ ] All 🟡 WARNINGs have been investigated and tickets filed
- [ ] All 🔴 FAILUREs have been escalated and assigned
- [ ] Results logged in the [Reconciliation Results Log](./discrepancy_resolution_log.md)
- [ ] Weekly summary sent to `#data-platform` Slack channel

---

## 6. Common Root Causes

| Root Cause | Symptoms | Resolution |
|-----------|----------|------------|
| **Late-arriving events** | BI count is lower than raw for recent dates; resolves next day | Increase transformation schedule buffer; add reprocessing window |
| **Duplicate events** | Raw count is higher than BI count | Check deduplication logic in dbt; verify `event_id` uniqueness at source |
| **Schema drift** | New event name present in raw but missing from BI | Update dbt model to include new event; add to taxonomy |
| **Filter mismatch** | Counts diverge for specific tenants | Compare `WHERE` clauses in raw pull vs. dbt model |
| **Timezone mismatch** | Counts are off by ~1 day's worth of events at boundaries | Ensure both raw and BI use UTC consistently |
| **Pipeline failure** | Entire date range is missing from BI | Check dbt run logs; re-trigger failed models |
